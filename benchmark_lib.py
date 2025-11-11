#!/usr/bin/env python3
"""
Библиотека за benchmark тестове с wrk.
Съдържа функции за изпълнение на wrk команди и парсване на резултатите.
"""

import subprocess
import json
import re
import time
from typing import Dict, List, Optional
from pathlib import Path


class WrkBenchmark:
    """Wrapper клас за wrk benchmark инструмент"""
    
    def __init__(self, url: str = "http://127.0.0.1:9090", wrk_path: str = "wrk"):
        self.url = url
        self.wrk_path = wrk_path
        self.scripts_dir = Path("wrk_scripts")
        self.scripts_dir.mkdir(exist_ok=True)
        
    def check_wrk_installed(self) -> bool:
        """Проверява дали wrk е инсталиран"""
        try:
            result = subprocess.run([self.wrk_path, "--version"], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def create_payload_script(self, size: int) -> Path:
        """
        Създава Lua script за wrk с POST request с определен payload размер.
        
        Args:
            size: Размер на payload в bytes
            
        Returns:
            Path към създадения script файл
        """
        script_path = self.scripts_dir / f"payload_{size}.lua"
        
        # Оптимизация: за големи payloads генерираме chunked
        if size > 1024 * 1024:  # > 1MB
            # Генерираме string по-ефективно
            lua_script = f'''
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/octet-stream"

local body_size = {size}
local chunk_size = 8192
local chunk = string.rep("A", chunk_size)
local full_chunks = math.floor(body_size / chunk_size)
local remainder = body_size % chunk_size

request = function()
    local body_parts = {{}}
    for i = 1, full_chunks do
        table.insert(body_parts, chunk)
    end
    if remainder > 0 then
        table.insert(body_parts, string.rep("A", remainder))
    end
    local body = table.concat(body_parts)
    
    return wrk.format("POST", "/", 
        {{["Content-Length"] = tostring(#body)}}, 
        body)
end
'''
        else:
            # За малки payloads - директно
            lua_script = f'''
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/octet-stream"

local body = string.rep("A", {size})

request = function()
    return wrk.format("POST", "/", 
        {{["Content-Length"] = tostring(#body)}}, 
        body)
end
'''
        
        script_path.write_text(lua_script)
        return script_path
    
    def run_benchmark(self, 
                     connections: int, 
                     duration: int = 30,
                     threads: int = 4,
                     script: Optional[Path] = None,
                     timeout: int = 120) -> Dict:
        """
        Изпълнява wrk benchmark.
        
        Args:
            connections: Брой паралелни връзки
            duration: Продължителност в секунди
            threads: Брой threads (обикновено 4)
            script: Path към Lua script (за POST с payload)
            timeout: Timeout за цялата команда
            
        Returns:
            Dict с резултатите от теста
        """
        cmd = [
            self.wrk_path,
            "-t", str(threads),
            "-c", str(connections),
            "-d", f"{duration}s",
            "--latency",  # За percentile данни
        ]
        
        if script:
            cmd.extend(["-s", str(script)])
        
        cmd.append(self.url)
        
        print(f"  Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                print(f"  WARNING: wrk returned non-zero: {result.returncode}")
                print(f"  stderr: {result.stderr}")
            
            return self._parse_wrk_output(result.stdout, result.stderr, connections)
            
        except subprocess.TimeoutExpired:
            print(f"  ERROR: Benchmark timeout after {timeout}s")
            return {
                "connections": connections,
                "duration": duration,
                "error": "timeout",
                "requests_per_sec": 0,
                "failed_requests": -1
            }
        except Exception as e:
            print(f"  ERROR: {e}")
            return {
                "connections": connections,
                "duration": duration,
                "error": str(e),
                "requests_per_sec": 0,
                "failed_requests": -1
            }
    
    def _parse_wrk_output(self, stdout: str, stderr: str, connections: int) -> Dict:
        """
        Парсва output от wrk.
        
        wrk output format:
        Running 30s test @ http://127.0.0.1:9090
          4 threads and 10 connections
          Thread Stats   Avg      Stdev     Max   +/- Stdev
            Latency     1.23ms    2.34ms   50.00ms   95.00%
            Req/Sec     2.50k   500.00     3.00k    80.00%
          Latency Distribution
             50%    1.00ms
             75%    1.50ms
             90%    2.00ms
             99%    5.00ms
          150000 requests in 30.00s, 10.00MB read
          Socket errors: connect 0, read 0, write 0, timeout 0
        Requests/sec:   5000.00
        Transfer/sec:    333.33KB
        """
        
        result = {
            "connections": connections,
            "raw_output": stdout,
            "stderr": stderr
        }
        
        # Requests per second
        match = re.search(r'Requests/sec:\s+([\d.]+)', stdout)
        if match:
            result["requests_per_sec"] = float(match.group(1))
        else:
            result["requests_per_sec"] = 0
        
        # Transfer/sec (throughput)
        match = re.search(r'Transfer/sec:\s+([\d.]+)(KB|MB|GB)', stdout)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            # Конвертираме всичко в MB/s
            if unit == "KB":
                value /= 1024
            elif unit == "GB":
                value *= 1024
            result["throughput_mbps"] = value
        else:
            result["throughput_mbps"] = 0
        
        # Total requests
        match = re.search(r'(\d+) requests in', stdout)
        if match:
            result["total_requests"] = int(match.group(1))
        else:
            result["total_requests"] = 0
        
        # Total data transferred
        match = re.search(r'requests in [\d.]+s, ([\d.]+)(KB|MB|GB)', stdout)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            if unit == "KB":
                value /= 1024
            elif unit == "GB":
                value *= 1024
            result["total_data_mb"] = value
        else:
            result["total_data_mb"] = 0
        
        # Latency stats
        match = re.search(r'Latency\s+([\d.]+)(us|ms|s)', stdout)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            # Конвертираме всичко в ms
            if unit == "us":
                value /= 1000
            elif unit == "s":
                value *= 1000
            result["latency_avg_ms"] = value
        else:
            result["latency_avg_ms"] = 0
        
        # Latency percentiles
        percentiles = {}
        for pct in ["50", "75", "90", "99"]:
            match = re.search(rf'{pct}%\s+([\d.]+)(us|ms|s)', stdout)
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                if unit == "us":
                    value /= 1000
                elif unit == "s":
                    value *= 1000
                percentiles[f"p{pct}"] = value
        result["latency_percentiles"] = percentiles
        
        # Socket errors (failed requests)
        match = re.search(r'Socket errors: connect (\d+), read (\d+), write (\d+), timeout (\d+)', stdout)
        if match:
            connect_err = int(match.group(1))
            read_err = int(match.group(2))
            write_err = int(match.group(3))
            timeout_err = int(match.group(4))
            result["failed_requests"] = connect_err + read_err + write_err + timeout_err
            result["socket_errors"] = {
                "connect": connect_err,
                "read": read_err,
                "write": write_err,
                "timeout": timeout_err
            }
        else:
            result["failed_requests"] = 0
            result["socket_errors"] = {
                "connect": 0,
                "read": 0,
                "write": 0,
                "timeout": 0
            }
        
        # Non-2xx responses (също са failed)
        match = re.search(r'Non-2xx or 3xx responses: (\d+)', stdout)
        if match:
            non_2xx = int(match.group(1))
            result["failed_requests"] += non_2xx
            result["non_2xx_responses"] = non_2xx
        else:
            result["non_2xx_responses"] = 0
        
        return result
    
    def run_concurrency_test(self, 
                            concurrency_levels: List[int],
                            duration: int = 30) -> List[Dict]:
        """
        Изпълнява серия от тестове с различни нива на паралелност.
        
        Args:
            concurrency_levels: Списък с брой паралелни връзки
            duration: Продължителност на всеки тест
            
        Returns:
            Списък с резултати от всички тестове
        """
        results = []
        
        print(f"\n=== Concurrency Test (Duration: {duration}s) ===")
        for i, conc in enumerate(concurrency_levels, 1):
            print(f"\n[{i}/{len(concurrency_levels)}] Testing with {conc} connections...")
            
            result = self.run_benchmark(
                connections=conc,
                duration=duration,
                threads=min(4, conc)  # Не повече от 4 threads
            )
            
            results.append(result)
            
            # Кратка почивка между тестовете
            if i < len(concurrency_levels):
                print("  Cooling down for 2 seconds...")
                time.sleep(2)
        
        return results
    
    def run_throughput_test(self,
                           payload_sizes: List[int],
                           connections: int = 10,
                           duration: int = 30) -> List[Dict]:
        """
        Изпълнява серия от тестове с различни payload размери.
        
        Args:
            payload_sizes: Списък с размери на payload в bytes
            connections: Брой паралелни връзки (константен)
            duration: Продължителност на всеки тест
            
        Returns:
            Списък с резултати от всички тестове
        """
        results = []
        
        print(f"\n=== Throughput Test (Duration: {duration}s, Connections: {connections}) ===")
        for i, size in enumerate(payload_sizes, 1):
            print(f"\n[{i}/{len(payload_sizes)}] Testing with {self._format_size(size)} payload...")
            
            # Създаваме Lua script за този размер
            script = self.create_payload_script(size)
            
            result = self.run_benchmark(
                connections=connections,
                duration=duration,
                threads=4,
                script=script,
                timeout=duration + 60  # Extra timeout за големи payloads
            )
            
            result["payload_size"] = size
            result["payload_size_formatted"] = self._format_size(size)
            results.append(result)
            
            # Кратка почивка
            if i < len(payload_sizes):
                print("  Cooling down for 2 seconds...")
                time.sleep(2)
        
        return results
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Форматира размер в human-readable формат"""
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.0f}KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.0f}MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f}GB"


def save_results(results: List[Dict], filename: str):
    """Записва резултатите в JSON файл"""
    output_path = Path("results") / filename
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results saved to {output_path}")


def load_results(filename: str) -> List[Dict]:
    """Зарежда резултати от JSON файл"""
    results_path = Path("results") / filename
    
    if not results_path.exists():
        raise FileNotFoundError(f"Results file not found: {results_path}")
    
    with open(results_path) as f:
        return json.load(f)