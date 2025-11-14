#!/usr/bin/env python3
"""
Библиотека за benchmark тестове с Locust.
По-лесна алтернатива на wrk - pure Python, работи навсякъде.
"""

import subprocess
import json
import time
import tempfile
from typing import Dict, List, Optional
from pathlib import Path


class LocustBenchmark:
    """Wrapper клас за Locust benchmark инструмент"""
    
    def __init__(self, url: str = "http://127.0.0.1:9090"):
        self.url = url
        self.scripts_dir = Path("locust_scripts")
        self.scripts_dir.mkdir(exist_ok=True)
        
    def check_locust_installed(self) -> bool:
        """Проверява дали locust е инсталиран"""
        try:
            result = subprocess.run(["locust", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def create_locustfile(self, payload_size: int = 0) -> Path:
        """
        Създава Locust test file за benchmark.
        
        Args:
            payload_size: Размер на POST payload в bytes (0 = GET request)
            
        Returns:
            Path към създадения locustfile
        """
        script_path = self.scripts_dir / f"locustfile_{payload_size}.py"
        
        if payload_size == 0:
            # GET request
            locust_code = f'''
from locust import HttpUser, task, between

class BenchmarkUser(HttpUser):
    wait_time = between(0, 0)  # No wait between requests
    host = "{self.url}"
    
    @task
    def get_request(self):
        self.client.get("/")
'''
        else:
            # POST request with payload
            locust_code = f'''
from locust import HttpUser, task, between

class BenchmarkUser(HttpUser):
    wait_time = between(0, 0)
    host = "{self.url}"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Generate payload once per user
        self.payload = "A" * {payload_size}
    
    @task
    def post_request(self):
        self.client.post("/", data=self.payload)
'''
        
        script_path.write_text(locust_code)
        return script_path
    
    def run_benchmark(self,
                     users: int,
                     duration: int = 30,
                     spawn_rate: Optional[int] = None,
                     payload_size: int = 0) -> Dict:
        """
        Изпълнява Locust benchmark.
        
        Args:
            users: Брой паралелни потребители (concurrency)
            duration: Продължителност в секунди
            spawn_rate: Колко users/sec да spawn-ва (default: users)
            payload_size: Размер на POST payload (0 = GET)
            
        Returns:
            Dict с резултатите от теста
        """
        if spawn_rate is None:
            spawn_rate = users
        
        # Създаваме locustfile
        locustfile = self.create_locustfile(payload_size)
        
        # Временен файл за статистиките
        stats_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        stats_file.close()
        
        cmd = [
            "locust",
            "-f", str(locustfile),
            "--headless",  # No web UI
            "--users", str(users),
            "--spawn-rate", str(spawn_rate),
            "--run-time", f"{duration}s",
            "--host", self.url,
            "--html", f"/tmp/locust_report_{users}_{payload_size}.html",
            "--json",  # Output JSON stats
        ]
        
        print(f"  Running: locust -u {users} -r {spawn_rate} -t {duration}s ...")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=duration + 30
            )
            
            # Парсваме output-а
            return self._parse_locust_output(result.stdout, result.stderr, users, payload_size)
            
        except subprocess.TimeoutExpired:
            print(f"  ERROR: Benchmark timeout")
            return {
                "users": users,
                "payload_size": payload_size,
                "error": "timeout",
                "requests_per_sec": 0,
                "failed_requests": -1
            }
        except Exception as e:
            print(f"  ERROR: {e}")
            return {
                "users": users,
                "payload_size": payload_size,
                "error": str(e),
                "requests_per_sec": 0,
                "failed_requests": -1
            }
    
    def _parse_locust_output(self, stdout: str, stderr: str, users: int, payload_size: int) -> Dict:
        """
        Парсва output от Locust.
        
        Locust извежда статистики в табличен формат в stdout.
        """
        result = {
            "users": users,
            "payload_size": payload_size,
            "raw_output": stdout,
            "stderr": stderr
        }
        
        lines = stdout.split('\n')
        
        # Търсим в output-а за статистики
        # Locust извежда summary в края:
        # Type     Name           # reqs      # fails  |     Avg     Min     Max  Median  |   req/s failures/s
        
        for i, line in enumerate(lines):
            # Requests per second
            if "requests/s:" in line.lower() or "req/s" in line:
                # От summary line
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        # Последният număr е обикновено req/s
                        for part in reversed(parts):
                            try:
                                rps = float(part)
                                result["requests_per_sec"] = rps
                                break
                            except ValueError:
                                continue
                    except:
                        pass
            
            # Total requests
            if "Total requests" in line or "# reqs" in line:
                parts = line.split()
                for j, part in enumerate(parts):
                    try:
                        total = int(part)
                        if total > 0:
                            result["total_requests"] = total
                            break
                    except ValueError:
                        continue
            
            # Failed requests
            if "# fails" in line or "failures" in line.lower():
                parts = line.split()
                for part in parts:
                    try:
                        fails = int(part)
                        result["failed_requests"] = fails
                        break
                    except ValueError:
                        continue
            
            # Latency - Average
            if "Avg" in line and "ms" in line.lower():
                parts = line.split()
                try:
                    # Намираме числото след "Avg"
                    avg_idx = -1
                    for j, part in enumerate(parts):
                        if "Avg" in part:
                            avg_idx = j
                            break
                    
                    if avg_idx >= 0 and avg_idx + 1 < len(parts):
                        avg_lat = float(parts[avg_idx + 1])
                        result["latency_avg_ms"] = avg_lat
                except:
                    pass
            
            # Median latency
            if "Median" in line or "50%" in line:
                parts = line.split()
                try:
                    for j, part in enumerate(parts):
                        if "Median" in part or "50%" in part:
                            if j + 1 < len(parts):
                                median = float(parts[j + 1])
                                result.setdefault("latency_percentiles", {})["p50"] = median
                                break
                except:
                    pass
        
        # Fallback values
        result.setdefault("requests_per_sec", 0)
        result.setdefault("failed_requests", 0)
        result.setdefault("total_requests", 0)
        result.setdefault("latency_avg_ms", 0)
        result.setdefault("latency_percentiles", {})
        
        # Calculate throughput if we have payload size
        if payload_size > 0 and result["requests_per_sec"] > 0:
            # Throughput = requests/sec * payload_size (bytes) / 1024^2 (to MB)
            throughput_mbps = (result["requests_per_sec"] * payload_size) / (1024 * 1024)
            result["throughput_mbps"] = throughput_mbps
        else:
            result["throughput_mbps"] = 0
        
        return result
    
    def run_concurrency_test(self,
                            concurrency_levels: List[int],
                            duration: int = 30) -> List[Dict]:
        """
        Изпълнява серия от тестове с различни нива на паралелност.
        """
        results = []
        
        print(f"\n=== Concurrency Test (Duration: {duration}s) ===")
        for i, users in enumerate(concurrency_levels, 1):
            print(f"\n[{i}/{len(concurrency_levels)}] Testing with {users} users...")
            
            result = self.run_benchmark(
                users=users,
                duration=duration,
                spawn_rate=min(users, 100)  # Spawn max 100 users/sec
            )
            
            results.append(result)
            
            # Кратка почивка между тестовете
            if i < len(concurrency_levels):
                print("  Cooling down for 2 seconds...")
                time.sleep(2)
        
        return results
    
    def run_throughput_test(self,
                           payload_sizes: List[int],
                           users: int = 10,
                           duration: int = 30) -> List[Dict]:
        """
        Изпълнява серия от тестове с различни payload размери.
        """
        results = []
        
        print(f"\n=== Throughput Test (Duration: {duration}s, Users: {users}) ===")
        for i, size in enumerate(payload_sizes, 1):
            print(f"\n[{i}/{len(payload_sizes)}] Testing with {self._format_size(size)} payload...")
            
            result = self.run_benchmark(
                users=users,
                duration=duration,
                payload_size=size
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