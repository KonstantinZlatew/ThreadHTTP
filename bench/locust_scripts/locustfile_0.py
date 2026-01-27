
from locust import HttpUser, task, between

class BenchmarkUser(HttpUser):
    wait_time = between(0, 0)  # No wait between requests
    host = "http://127.0.0.1:9090"
    
    @task
    def get_request(self):
        self.client.get("/")
