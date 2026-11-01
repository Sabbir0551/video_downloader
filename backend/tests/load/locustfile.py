import random
from locust import HttpUser, task, between

SAMPLE_URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://vimeo.com/76979871",
    "https://x.com/Rainmaker1973/status/2116364555429540007",
    "https://soundcloud.com/octobersveryown/drake-gods-plan",
]

class AnyStreamLoadUser(HttpUser):
    wait_time = between(1, 3)

    @task(5)
    def check_health(self):
        self.client.get("/health")

    @task(4)
    def list_platforms(self):
        self.client.get("/api/v1/platforms")

    @task(3)
    def extract_info(self):
        url = random.choice(SAMPLE_URLS)
        self.client.post("/api/v1/info", json={"url": url})

    @task(1)
    def create_download_job(self):
        url = random.choice(SAMPLE_URLS)
        with self.client.post(
            "/api/v1/downloads",
            json={"url": url, "format_id": "best"},
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201, 202, 429, 503):
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
