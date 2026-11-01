import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 50 },   // Warm up to 50 VUs
    { duration: '1m', target: 200 },   // Scale to 200 VUs
    { duration: '30s', target: 500 },  // Spike to 500 VUs
    { duration: '30s', target: 0 },    // Ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<1500'], // 95% of requests should be below 1.5s
    http_req_failed: ['rate<0.05'],    // Less than 5% errors
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000';

export default function () {
  // 1. Health check
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, { 'health is 200': (r) => r.status === 200 });

  // 2. Platforms listing
  const platformsRes = http.get(`${BASE_URL}/api/v1/platforms`);
  check(platformsRes, { 'platforms total 100': (r) => r.json().total === 100 });

  // 3. Platform detection
  const detectRes = http.get(`${BASE_URL}/api/v1/platforms/detect?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ`);
  check(detectRes, { 'detected youtube': (r) => r.json().detected === true });

  sleep(1);
}
