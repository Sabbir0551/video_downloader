# AnyStream High-Concurrency Capacity & Scaling Plan

This document details the architectural blueprints, bottleneck analyses, and operational configurations required to scale **AnyStream** to:
- **500 active concurrent video downloads**
- **5,000 metadata info extraction requests / minute**
- **Zero degradation on 100 supported social media platforms**

---

## 1. Workload Analysis & Resource Formulas

### A. Info Extraction Requests (5,000 req/min ≈ 83.3 req/sec)
- **Profile**: Network I/O and TLS handshakes to upstream social CDNs. CPU usage per extraction is low (JSON parsing and format filtering).
- **Average duration**: 400ms – 1,200ms without cache.
- **Cache Hit Ratio Target**: ~65% in production (due to trending videos and link sharing).
- **Cached response time**: < 15ms via Redis.
- **Uncached throughput needed**: ~30 req/sec handled by API instances.
- **API Worker Sizing**: 4 Uvicorn worker processes per API container × 3 replicas = 12 workers, easily sustaining 150+ req/sec.

### B. Active Concurrent Downloads (500 simultaneous streams)
- **Average stream bitrate**: 4.5 Mbps (1080p H.264/VP9) or 15 Mbps (4K HDR).
- **Average download duration**: 30–90 seconds.
- **Bandwidth Required**:
  - Direct server egress: $500 \times 6\text{ Mbps} = 3,000\text{ Mbps} = 3\text{ Gbps}$.
  - **Offloaded Architecture**: 100% of user download bandwidth is offloaded directly to Cloudflare R2 / AWS S3 via presigned redirect URLs.
  - Ingress bandwidth into worker nodes: ~3 Gbps split across worker cluster.

---

## 2. Infrastructure Architecture & Queue Separation

```
[ Clients / Web / PWA ]
          │
    (HTTPS / Nginx)
          │
  ┌───────┴──────────────────────┐
  │  Stateless FastAPI Pods (x3) │  ◄── Rate limiting & SSRF Guard
  └───────┬──────────────┬───────┘
          │              │
      (PubSub/SSE)   (Job Enqueue)
          │              │
          ▼              ▼
     [ Redis 7 ]   [ PostgreSQL 16 ]
          │
   ┌──────┴─────────────────────────────────┐
   │              Celery Queues             │
   ├───────────────────┬────────────────────┤
   │ media_downloads   │ media_transcode    │
   │ (I/O Bound)       │ (CPU Bound FFmpeg) │
   │ Concurrency: 64   │ Concurrency: 8     │
   │ Replicas: 8       │ Replicas: 4        │
   └───────────────────┴────────────────────┘
          │
    (S3/R2 Upload)
          ▼
   [ Cloudflare R2 ] ───(Direct Presigned Download)───► [ End User ]
```

### Queue Separation Strategy
1. **`media_downloads` Queue**:
   - I/O bound worker pool (`gevent` or `eventlet` or high concurrency threads).
   - Dedicated solely to network downloading and DASH/HLS native stream muxing.
2. **`media_transcode` Queue**:
   - CPU intensive worker pool (`prefork` or hardware accelerated `nvenc`/`vaapi`).
   - Handles H.264 compatible conversion only when requested.
3. **`janitor_maintenance` Queue**:
   - Lightweight periodic beat tasks (deleting expired files, tracking upstream yt-dlp release versions).

---

## 3. Backpressure & Admission Control

When system capacity is constrained, AnyStream enforces non-blocking admission control:

1. **Queue Depth Backpressure**:
   - When queue length in `media_downloads` exceeds 500, new submissions immediately return:
     ```http
     HTTP/503 Service Unavailable
     Retry-After: 30
     Content-Type: application/json

     {
       "error_code": "GLOBAL_CONCURRENCY_EXCEEDED",
       "message": "System download capacity is currently full. Please try again shortly."
     }
     ```
2. **Disk Backpressure**:
   - Hard quota floor (`MIN_FREE_DISK_BYTES = 2 GB`). If available disk space falls below threshold, new downloads are temporarily queued or deferred until the janitor completes eviction.
3. **Per-IP Fairness**:
   - Maximum 2 concurrent active downloads per IP hash, preventing denial-of-wallet or starvation from single clients.

---

## 4. Kubernetes Autoscaling with KEDA (Manifest Sample)

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: anystream-download-worker-scaler
  namespace: anystream
spec:
  scaleTargetRef:
    name: anystream-worker-downloads
  minReplicaCount: 4
  maxReplicaCount: 20
  triggers:
  - type: redis
    metadata:
      address: redis-service:6379
      listName: media_downloads
      listLength: "15"
```

---

## 5. Grafana Dashboard & Prometheus Metrics

Exposed via `/metrics`:
- `anystream_http_requests_total{endpoint, status_code}`
- `anystream_active_downloads_gauge`
- `anystream_job_duration_seconds{status, format}`
- `anystream_queue_depth_gauge{queue_name}`
- `anystream_circuit_breaker_status{platform_id}`

---

## 6. Load Test Scenarios (Locust / k6)

Located under `tests/load/`:
- `locustfile.py`: Simulates 5,000 concurrent browsing users pasting URLs and initiating downloads.
- `k6_stress_test.js`: Ramping arrival-rate test from 50 to 1,000 virtual users checking SSRF, rate limit enforcement, and SSE progress stream stability.

