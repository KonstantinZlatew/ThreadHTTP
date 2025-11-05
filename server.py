#!/usr/bin/env python3
"""
Async/epoll минимален HTTP сървър.
Използва ниско-ниво socket + asyncio (epoll под Linux).
Логва request-ите в server.log и връща "OK" при успех, "ERROR" при грешка.
"""

import asyncio
import socket
import datetime
import pathlib

LOG_FILE = "server.log"
HOST = "0.0.0.0"
PORT = 9090

MAX_LINE = 10 * 1024 * 1024      # 10 MB за първи ред или header line
MAX_HEADERS = 10 * 1024 * 1024   # 10 MB общи headers
MAX_BODY = 10 * 1024 * 1024      # 10 MB за body

def log(msg: str):
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    line = f"[{ts}] {msg}\n"
    print(line, end="")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)

async def read_line(sock: socket.socket, loop: asyncio.AbstractEventLoop, max_len: int):
    buf = bytearray()
    while True:
        chunk = await loop.sock_recv(sock, 1024)
        if not chunk:
            if not buf:
                return None
            break
        buf.extend(chunk)
        if b'\n' in buf:
            break
        if len(buf) > max_len:
            raise ValueError("line too long")
    # отделяме първата линия, оставаме с останалите в internal buffer
    # за простота - връщаме линия и поставяме останалото обратно в socket с памет:
    # Но тъй като не можем да "push back" в сокет, ще работим на по-високо ниво:
    # Вместо това, при четене за headers четем по-безопасно с read_until_double_crlf()
    # Тази функция се използва главно за единични редове, но в нашия flow ще използваме
    # read_until_double_crlf за headers. Тук връщаме първата линия откъм буфера.
    # Разделяме на първа линия и оставяме останалото в local buffer to be returned too.
    idx = buf.find(b'\n')
    line = bytes(buf[:idx+1])
    remainder = bytes(buf[idx+1:])
    return line, remainder

# Чете headers до двойна CRLF, с лимит
async def read_headers(sock: socket.socket, loop: asyncio.AbstractEventLoop, max_total: int):
    buf = bytearray()
    while True:
        chunk = await loop.sock_recv(sock, 4096)
        if not chunk:
            break
        buf.extend(chunk)
        if b'\r\n\r\n' in buf or b'\n\n' in buf:
            break
        if len(buf) > max_total:
            raise ValueError("headers too long")
    return bytes(buf)

# Основен обработчик на клиент
async def handle_client(client_sock: socket.socket, addr, loop):
    peer = f"{addr[0]}:{addr[1]}"
    try:
        client_sock.setblocking(False)
        # Четем първи ред (request-line): можем да прочетем chunk и да го парснем
        # Прочитаме headers първо (включва и първия ред)
        raw_headers = await read_headers(client_sock, loop, MAX_HEADERS)
        if not raw_headers:
            log(f"{peer} EMPTY_REQUEST")
            await send_error(client_sock)
            return

        # Ограничение за първи ред: вземаме първия ред от raw_headers
        first_line_end = raw_headers.find(b'\r\n')
        if first_line_end == -1:
            first_line_end = raw_headers.find(b'\n')
        if first_line_end == -1:
            # нямаме валиден първи ред
            log(f"{peer} INVALID_FIRST_LINE")
            await send_error(client_sock)
            return

        if first_line_end > MAX_LINE:
            log(f"{peer} FIRST_LINE_TOO_LONG len={first_line_end}")
            await send_error(client_sock)
            return

        first_line = raw_headers[:first_line_end].decode('latin-1', errors='replace').strip()
        headers_part = raw_headers[first_line_end+2:] if raw_headers[first_line_end:first_line_end+2]==b'\r\n' else raw_headers[first_line_end+1:]
        headers_text = headers_part.decode('latin-1', errors='replace')

        # Парсване на headers: разделяме по редове, до празен ред
        header_lines = headers_text.splitlines()
        headers = {}
        for line in header_lines:
            if not line.strip():
                break
            if ':' in line:
                k, v = line.split(':', 1)
                headers[k.strip().lower()] = v.strip()
            else:
                # Нередов header - записваме като raw
                headers.setdefault('__invalid__', []).append(line)

        method = first_line.split()[0] if first_line.split() else "UNKNOWN"

        # Ако има Content-Length -> прочети body (но с лимит)
        body = b""
        content_length = None
        if 'content-length' in headers:
            try:
                content_length = int(headers['content-length'])
            except Exception:
                content_length = None

        if content_length is not None:
            if content_length > MAX_BODY:
                # не четем целия body (за да не засядаме) - прочитаме до MAX_BODY байта и игнорираме останалото
                to_read = MAX_BODY
                read_so_far = 0
                while read_so_far < to_read:
                    chunk = await loop.sock_recv(client_sock, min(65536, to_read - read_so_far))
                    if not chunk:
                        break
                    body += chunk
                    read_so_far += len(chunk)
                log(f"{peer} BODY_TRUNCATED content_length={content_length} read={read_so_far}")
                # drain rest non-blocking (consume but ignore) up to a small window to avoid blocking:
                remaining = content_length - read_so_far
                # try to consume without blocking but with timeout:
                try:
                    client_sock.setblocking(False)
                    # attempt to read a few times quickly
                    for _ in range(5):
                        chunk = await asyncio.wait_for(loop.sock_recv(client_sock, 4096), timeout=0.05)
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        if remaining <= 0:
                            break
                except Exception:
                    pass
                # mark error because client sent too large body
                log(f"{peer} BODY_TOO_LARGE total={content_length}")
                await send_error(client_sock)
                return
            else:
                # нормално четене на body
                need = content_length
                read = 0
                while read < need:
                    chunk = await loop.sock_recv(client_sock, min(65536, need - read))
                    if not chunk:
                        break
                    body += chunk
                    read += len(chunk)

        # Форматираме лог съобщението
        now = datetime.datetime.utcnow().isoformat() + "Z"
        log_msg = f"REQUEST from {peer} at {now}\nREQUEST-LINE: {first_line}\nMETHOD: {method}\nHEADERS:\n"
        for k, v in headers.items():
            log_msg += f"  {k}: {v}\n"
        # ограничаваме логнатото тяло до 1MB за четливост в примера
        display_body = body
        if len(display_body) > 1024*1024:
            display_body = display_body[:1024*1024] + b"...[truncated]\n"
        try:
            body_text = display_body.decode('utf-8', errors='replace')
        except Exception:
            body_text = str(display_body)
        log_msg += f"BODY ({len(body)} bytes):\n{body_text}\n----END----"
        log(log_msg)

        # Отговаряме 200 OK
        await send_ok(client_sock)
    except ValueError as ve:
        log(f"{peer} PARSE_ERROR: {ve}")
        await send_error(client_sock)
    except Exception as e:
        log(f"{peer} EXCEPTION: {e}")
        try:
            await send_error(client_sock)
        except Exception:
            pass
    finally:
        try:
            client_sock.close()
        except Exception:
            pass

async def send_ok(sock: socket.socket):
    resp_body = b"OK"
    resp = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(resp_body)).encode() + b"\r\nConnection: close\r\n\r\n" + resp_body
    await asyncio.get_event_loop().sock_sendall(sock, resp)

async def send_error(sock: socket.socket):
    resp_body = b"ERROR"
    resp = b"HTTP/1.1 500 Internal Server Error\r\nContent-Length: " + str(len(resp_body)).encode() + b"\r\nConnection: close\r\n\r\n" + resp_body
    try:
        await asyncio.get_event_loop().sock_sendall(sock, resp)
    except Exception:
        pass

async def accept_loop(server_sock: socket.socket, loop: asyncio.AbstractEventLoop):
    server_sock.setblocking(False)
    while True:
        try:
            client_sock, addr = await loop.sock_accept(server_sock)
            log(f"ACCEPT {addr}")
            # стартираме task за обработка
            asyncio.create_task(handle_client(client_sock, addr, loop))
        except Exception as e:
            log(f"ACCEPT_EXCEPTION: {e}")
            await asyncio.sleep(0.1)

def run(host=HOST, port=PORT):
    loop = asyncio.get_event_loop()
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(100)
    log(f"Server starting on {host}:{port}")
    try:
        loop.run_until_complete(accept_loop(server_sock, loop))
    except KeyboardInterrupt:
        log("Server shutting down (KeyboardInterrupt)")
    finally:
        server_sock.close()

if __name__ == "__main__":
    # create/clear log file
    p = pathlib.Path(LOG_FILE)
    if p.exists():
        p.unlink()
    run()
