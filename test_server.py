#!/usr/bin/env python3
"""
Unit tests за HTTP сървъра.
Използва pytest framework.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock


# Import на функциите от server.py
import sys
sys.path.insert(0, '.')
from server import (
    log, read_headers, handle_client, 
    send_ok, send_error, MAX_LINE, MAX_HEADERS, MAX_BODY
)


class TestLogFunction:
    """Тестове за log функцията"""
    
    def test_log_creates_entry(self, tmp_path, monkeypatch):
        """Тест че log създава запис във файла"""
        log_file = tmp_path / "test.log"
        monkeypatch.setattr('server.LOG_FILE', str(log_file))
        
        log("test message")
        
        assert log_file.exists()
        content = log_file.read_text()
        assert "test message" in content
        assert "[" in content  # timestamp brackets
    
    def test_log_with_empty_message(self, tmp_path, monkeypatch):
        """Тест че log работи с празно съобщение"""
        log_file = tmp_path / "test.log"
        monkeypatch.setattr('server.LOG_FILE', str(log_file))
        
        log("")
        
        assert log_file.exists()
    
    def test_log_with_special_characters(self, tmp_path, monkeypatch):
        """Тест че log работи със специални символи"""
        log_file = tmp_path / "test.log"
        monkeypatch.setattr('server.LOG_FILE', str(log_file))
        
        log("test\nmultiline\nmessage")
        
        content = log_file.read_text()
        assert "multiline" in content


class TestReadHeaders:
    """Тестове за read_headers функцията"""
    
    @pytest.mark.asyncio
    async def test_read_headers_normal(self):
        """Тест за нормално четене на headers"""
        mock_sock = Mock()
        mock_loop = Mock()
        
        # Симулираме получаване на headers с double CRLF
        test_data = b"GET / HTTP/1.1\r\nHost: test\r\n\r\n"
        mock_loop.sock_recv = AsyncMock(side_effect=[test_data, b""])
        
        result = await read_headers(mock_sock, mock_loop, MAX_HEADERS)
        
        assert result == test_data
        assert b"GET / HTTP/1.1" in result
    
    @pytest.mark.asyncio
    async def test_read_headers_with_double_lf(self):
        """Тест за headers с двойна LF вместо CRLF"""
        mock_sock = Mock()
        mock_loop = Mock()
        
        test_data = b"GET / HTTP/1.1\nHost: test\n\n"
        mock_loop.sock_recv = AsyncMock(side_effect=[test_data, b""])
        
        result = await read_headers(mock_sock, mock_loop, MAX_HEADERS)
        
        assert result == test_data
    
    @pytest.mark.asyncio
    async def test_read_headers_exceeds_limit(self):
        """Тест че хвърля грешка при надвишаване на лимита"""
        mock_sock = Mock()
        mock_loop = Mock()
        
        # Симулираме много данни без double CRLF
        big_chunk = b"A" * 1000
        mock_loop.sock_recv = AsyncMock(return_value=big_chunk)
        
        with pytest.raises(ValueError, match="headers too long"):
            await read_headers(mock_sock, mock_loop, 500)
    
    @pytest.mark.asyncio
    async def test_read_headers_empty_connection(self):
        """Тест за празна връзка"""
        mock_sock = Mock()
        mock_loop = Mock()
        
        mock_loop.sock_recv = AsyncMock(return_value=b"")
        
        result = await read_headers(mock_sock, mock_loop, MAX_HEADERS)
        
        assert result == b""
    
    @pytest.mark.asyncio
    async def test_read_headers_multiple_chunks(self):
        """Тест за получаване на headers на части"""
        mock_sock = Mock()
        mock_loop = Mock()
        
        chunks = [
            b"GET / HTTP/1.1\r\n",
            b"Host: test\r\n",
            b"Content-Length: 10\r\n\r\n"
        ]
        mock_loop.sock_recv = AsyncMock(side_effect=chunks)
        
        result = await read_headers(mock_sock, mock_loop, MAX_HEADERS)
        
        assert b"GET / HTTP/1.1" in result
        assert b"Host: test" in result


class TestSendFunctions:
    """Тестове за send_ok и send_error"""
    
    @pytest.mark.asyncio
    async def test_send_ok(self):
        """Тест за send_ok функцията"""
        mock_sock = Mock()
        mock_loop = AsyncMock()
        
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            await send_ok(mock_sock)
        
        # Проверяваме че е извикан sock_sendall
        mock_loop.sock_sendall.assert_called_once()
        sent_data = mock_loop.sock_sendall.call_args[0][1]
        
        assert b"200 OK" in sent_data
        assert b"OK" in sent_data
    
    @pytest.mark.asyncio
    async def test_send_error(self):
        """Тест за send_error функцията"""
        mock_sock = Mock()
        mock_loop = AsyncMock()
        
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            await send_error(mock_sock)
        
        mock_loop.sock_sendall.assert_called_once()
        sent_data = mock_loop.sock_sendall.call_args[0][1]
        
        assert b"500" in sent_data
        assert b"ERROR" in sent_data
    
    @pytest.mark.asyncio
    async def test_send_error_handles_exception(self):
        """Тест че send_error обработва exceptions"""
        mock_sock = Mock()
        mock_loop = AsyncMock()
        mock_loop.sock_sendall.side_effect = Exception("Network error")
        
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            # Не трябва да хвърля exception
            await send_error(mock_sock)


class TestHandleClient:
    """Тестове за handle_client функцията"""
    
    @pytest.mark.asyncio
    async def test_handle_client_get_request(self, tmp_path, monkeypatch):
        """Тест за обработка на GET request"""
        log_file = tmp_path / "test.log"
        monkeypatch.setattr('server.LOG_FILE', str(log_file))
        
        mock_sock = MagicMock()
        mock_sock.setblocking = Mock()
        mock_sock.close = Mock()
        
        mock_loop = AsyncMock()
        
        # Симулираме GET request
        request_data = b"GET /test HTTP/1.1\r\nHost: localhost\r\n\r\n"
        mock_loop.sock_recv = AsyncMock(return_value=request_data)
        mock_loop.sock_sendall = AsyncMock()
        
        addr = ("127.0.0.1", 12345)
        
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            await handle_client(mock_sock, addr, mock_loop)
        
        # Проверяваме че е изпратен OK response
        assert mock_loop.sock_sendall.called
        
        # Проверяваме че е логнато
        log_content = log_file.read_text()
        assert "GET" in log_content
        assert "127.0.0.1" in log_content
    
    @pytest.mark.asyncio
    async def test_handle_client_post_request(self, tmp_path, monkeypatch):
        """Тест за обработка на POST request с body"""
        log_file = tmp_path / "test.log"
        monkeypatch.setattr('server.LOG_FILE', str(log_file))
        
        mock_sock = MagicMock()
        mock_sock.setblocking = Mock()
        mock_sock.close = Mock()
        
        mock_loop = AsyncMock()
        
        body = b"test=data"
        request_data = (
            b"POST /submit HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n"
        )
        
        # Първо headers, после body
        mock_loop.sock_recv = AsyncMock(side_effect=[request_data, body, b""])
        mock_loop.sock_sendall = AsyncMock()
        
        addr = ("127.0.0.1", 12346)
        
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            await handle_client(mock_sock, addr, mock_loop)
        
        log_content = log_file.read_text()
        assert "POST" in log_content
        assert "test=data" in log_content
    
    @pytest.mark.asyncio
    async def test_handle_client_empty_request(self, tmp_path, monkeypatch):
        """Тест за празен request"""
        log_file = tmp_path / "test.log"
        monkeypatch.setattr('server.LOG_FILE', str(log_file))
        
        mock_sock = MagicMock()
        mock_sock.setblocking = Mock()
        mock_sock.close = Mock()
        
        mock_loop = AsyncMock()
        # Първо извикване връща празно (EOF веднага)
        mock_loop.sock_recv = AsyncMock(return_value=b"")
        mock_loop.sock_sendall = AsyncMock()
        
        addr = ("127.0.0.1", 12347)
        
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            await handle_client(mock_sock, addr, mock_loop)
        
        # Трябва да е изпратен ERROR
        log_content = log_file.read_text()
        assert "EMPTY_REQUEST" in log_content
    
    @pytest.mark.asyncio
    async def test_handle_client_invalid_first_line(self, tmp_path, monkeypatch):
        """Тест за невалиден първи ред"""
        log_file = tmp_path / "test.log"
        monkeypatch.setattr('server.LOG_FILE', str(log_file))
        
        mock_sock = MagicMock()
        mock_sock.setblocking = Mock()
        mock_sock.close = Mock()
        
        mock_loop = AsyncMock()
        
        # Request без line break - трябва да има поне един chunk който се връща
        # и след това празен за да завърши четенето
        mock_loop.sock_recv = AsyncMock(side_effect=[
            b"INVALID REQUEST DATA WITHOUT NEWLINE",
            b""  # EOF
        ])
        mock_loop.sock_sendall = AsyncMock()
        
        addr = ("127.0.0.1", 12348)
        
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            await handle_client(mock_sock, addr, mock_loop)
        
        log_content = log_file.read_text()
        assert "INVALID_FIRST_LINE" in log_content
    
    @pytest.mark.asyncio
    async def test_handle_client_first_line_too_long(self, tmp_path, monkeypatch):
        """Тест за твърде дълъг първи ред"""
        log_file = tmp_path / "test.log"
        monkeypatch.setattr('server.LOG_FILE', str(log_file))
        
        mock_sock = MagicMock()
        mock_sock.setblocking = Mock()
        mock_sock.close = Mock()
        
        mock_loop = AsyncMock()
        
        # Много дълъг първи ред
        long_line = b"GET /" + b"A" * (MAX_LINE + 100) + b" HTTP/1.1\r\n\r\n"
        mock_loop.sock_recv = AsyncMock(return_value=long_line)
        mock_loop.sock_sendall = AsyncMock()
        
        addr = ("127.0.0.1", 12349)
        
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            await handle_client(mock_sock, addr, mock_loop)
        
        log_content = log_file.read_text()
        assert "FIRST_LINE_TOO_LONG" in log_content
    
    @pytest.mark.asyncio
    async def test_handle_client_body_too_large(self, tmp_path, monkeypatch):
        """Тест за твърде голям body"""
        log_file = tmp_path / "test.log"
        monkeypatch.setattr('server.LOG_FILE', str(log_file))
        
        mock_sock = MagicMock()
        mock_sock.setblocking = Mock()
        mock_sock.close = Mock()
        
        mock_loop = AsyncMock()
        
        # Request с Content-Length > MAX_BODY
        request_data = (
            b"POST /big HTTP/1.1\r\n"
            b"Content-Length: " + str(MAX_BODY + 1000).encode() + b"\r\n\r\n"
        )
        
        # Симулираме получаване на данни
        mock_loop.sock_recv = AsyncMock(side_effect=[
            request_data,
            b"A" * 4096,  # част от body
            b"B" * 4096,
            b""
        ])
        mock_loop.sock_sendall = AsyncMock()
        
        addr = ("127.0.0.1", 12350)
        
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
                await handle_client(mock_sock, addr, mock_loop)
        
        log_content = log_file.read_text()
        assert "BODY_TOO_LARGE" in log_content
    
    @pytest.mark.asyncio
    async def test_handle_client_exception_handling(self, tmp_path, monkeypatch):
        """Тест за обработка на exceptions"""
        log_file = tmp_path / "test.log"
        monkeypatch.setattr('server.LOG_FILE', str(log_file))
        
        mock_sock = MagicMock()
        mock_sock.setblocking = Mock(side_effect=Exception("Socket error"))
        mock_sock.close = Mock()
        
        mock_loop = AsyncMock()
        addr = ("127.0.0.1", 12351)
        
        # Не трябва да хвърля exception нагоре
        await handle_client(mock_sock, addr, mock_loop)
        
        log_content = log_file.read_text()
        assert "EXCEPTION" in log_content


class TestEdgeCases:
    """Тестове за гранични случаи"""
    
    @pytest.mark.asyncio
    async def test_handle_random_bytes(self, tmp_path, monkeypatch):
        """Тест за напълно случайни байтове"""
        log_file = tmp_path / "test.log"
        monkeypatch.setattr('server.LOG_FILE', str(log_file))
        
        mock_sock = MagicMock()
        mock_sock.setblocking = Mock()
        mock_sock.close = Mock()
        
        mock_loop = AsyncMock()
        
        # Случайни байтове (невалиден HTTP) - трябва да завърши с EOF
        random_data = bytes([i % 256 for i in range(100)])
        mock_loop.sock_recv = AsyncMock(side_effect=[random_data, b""])
        mock_loop.sock_sendall = AsyncMock()
        
        addr = ("127.0.0.1", 12352)
        
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            await handle_client(mock_sock, addr, mock_loop)
        
        # Трябва да е обработено без crash
        assert log_file.exists()
    
    def test_log_with_none_message(self, tmp_path, monkeypatch):
        """Тест за None като съобщение"""
        log_file = tmp_path / "test.log"
        monkeypatch.setattr('server.LOG_FILE', str(log_file))
        
        # Не трябва да хвърля exception
        try:
            log(None)
        except Exception:
            pytest.fail("log() should handle None gracefully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=server", "--cov-report=term-missing"])