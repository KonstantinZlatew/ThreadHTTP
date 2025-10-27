#!/usr/bin/env python3
"""
Тестов скрипт за сървъра.
Изпълнява:
 - нормален GET
 - нормален POST (Content-Length)
 - изпраща напълно случайни байтове
 - изпраща твърде дълъг header (>10MB)
 - изпраща твърде голям body (>10MB)
"""

import socket
import time
import os

HOST = "127.0.0.1"
PORT = 8080

def simple_get():
    s = socket.create_connection((HOST, PORT), timeout=5)
    req = b"GET / HTTP/1.1\r\nHost: test\r\nConnection: close\r\n\r\n"
    s.sendall(req)
    resp = s.recv(4096)
    print("GET response:", resp)
    s.close()

def simple_post():
    s = socket.create_connection((HOST, PORT), timeout=5)
    body = b"hello=world"
    req = b"POST /submit HTTP/1.1\r\nHost: test\r\nContent-Length: " + str(len(body)).encode() + b"\r\nConnection: close\r\n\r\n" + body
    s.sendall(req)
    resp = s.recv(4096)
    print("POST response:", resp)
    s.close()

def random_bytes():
    s = socket.create_connection((HOST, PORT), timeout=5)
    payload = os.urandom(128)
    s.sendall(payload)
    time.sleep(0.1)
    try:
        resp = s.recv(4096)
        print("RANDOM response:", resp)
    except Exception as e:
        print("RANDOM recv error:", e)
    s.close()

def long_header():
    s = socket.create_connection((HOST, PORT), timeout=10)
    big = b"A" * (11 * 1024 * 1024)  # 11 MB
    req = b"GET / HTTP/1.1\r\nHost: test\r\nX-Big: " + big + b"\r\nConnection: close\r\n\r\n"
    # Внимание: може да заеме време и да използва памет
    print("sending very long header (11MB)...")
    s.sendall(req[:1024*1024])  # изпращаме частично първо - за да демонстрираме не-забиване
    time.sleep(0.2)
    # опитваме да прочетем отговор (сървърът трябва да не блокира)
    try:
        resp = s.recv(4096)
        print("LONG-HEADER response (partial):", resp)
    except Exception as e:
        print("LONG-HEADER recv error:", e)
    s.close()

def big_body():
    s = socket.create_connection((HOST, PORT), timeout=20)
    body = b"B" * (11 * 1024 * 1024)  # 11 MB
    header = b"POST /big HTTP/1.1\r\nHost: test\r\nContent-Length: " + str(len(body)).encode() + b"\r\nConnection: close\r\n\r\n"
    print("sending large body header then body (11MB)...")
    s.sendall(header)
    # изпращаме body на части (да не изчерпваме памет)
    chunk = 1024*64
    sent = 0
    try:
        while sent < len(body):
            s.sendall(body[sent:sent+chunk])
            sent += chunk
            time.sleep(0.001)
            if sent % (1024*1024) == 0:
                print(f" sent {sent//1024//1024} MB")
    except Exception as e:
        print("send error:", e)
    try:
        resp = s.recv(4096)
        print("BIG-BODY response:", resp)
    except Exception as e:
        print("BIG-BODY recv error:", e)
    s.close()

if __name__ == "__main__":
    print("=== simple GET ===")
    simple_get()
    time.sleep(0.2)
    print("\n=== simple POST ===")
    simple_post()
    time.sleep(0.2)
    print("\n=== random bytes ===")
    random_bytes()
    time.sleep(0.2)
    print("\n=== long header test (partial) ===")
    long_header()
    time.sleep(0.2)
    print("\n=== big body test ===")
    big_body()
