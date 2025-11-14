
from locust import HttpUser, task, between

class BenchmarkUser(HttpUser):
    wait_time = between(0, 0)
    host = "http://127.0.0.1:9090"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Generate payload once per user
        self.payload = "A" * 102400
    
    @task
    def post_request(self):
        self.client.post("/", data=self.payload)
