# AnyStream Video Platform - Monorepo

A security-first, high-performance video downloader platform comprising a unified FastAPI backend, Celery worker pipeline, Next.js web application, and planned mobile support.

---

## 1. Project Overview & Capabilities

- **Unified API Gateway**: Serves web and API clients with identical contracts.
- **Pure Python Execution**: Uses `yt-dlp` as a library without shell string interpolations.
- **SSRF Defense-in-Depth**: Strict URL scheme allowlisting, DNS pre-resolution, and comprehensive CIDR blacklisting blocking private, loopback, link-local, and cloud metadata IP ranges.
- **Isolated Workers**: Containerized Celery workers with CPU/memory limits and dedicated ephemeral storage with automated 30-minute eviction (`JOB_EXPIRY_MINUTES = 30`).
- **Zero Raw PII Storage**: Client IPs are non-reversibly hashed via HMAC-SHA256 with rotating salts.
- **Real-Time Progress**: High-efficiency Server-Sent Events (SSE) with HTTP polling fallback.
- **Multi-Language & Accessible**: English (`en`) and Bangla (`bn`) internationalization with WCAG AA compliance.
- **Legal Safeguards**: Native DMCA/copyright takedown registry, DRM refusal checks, and Terms of Service enforcement.

---

## 2. Monorepo Directory Layout

```
.
├── backend/                  # FastAPI Backend & Celery Worker Pipeline
│   ├── app/
│   │   ├── api/              # API router endpoints (/info, /downloads, /jobs, /takedown, /health)
│   │   ├── core/             # Security, config, SSRF validator, error codes
│   │   │   ├── config.py     # Pydantic BaseSettings
│   │   │   ├── errors.py     # Custom structured HTTP exceptions
│   │   │   ├── security.py   # IP hashing, filename sanitizer, token signing
│   │   │   └── ssrf.py       # CIDR blacklist & DNS resolver guard
│   │   ├── db/               # SQLAlchemy async & sync session management
│   │   ├── models/           # DeclarativeBase ORM entities (job, takedown, abuse)
│   │   ├── schemas/          # Pydantic v2 request/response schemas
│   │   ├── services/         # Extraction, storage, cleaner, and rate limiting
│   │   ├── worker/           # Celery application & download execution tasks
│   │   └── main.py           # FastAPI application entrypoint
│   ├── tests/                # Automated pytest suite
│   ├── requirements.txt      # Production dependencies
│   └── requirements-dev.txt  # Testing and linting suite
├── web/                      # Next.js 16 App Router Frontend (React 19, Tailwind CSS v4, i18n)
│   ├── src/
│   │   ├── app/              # App router pages (Home, DMCA, Privacy, Terms)
│   │   ├── components/       # Accessible UI components (URL input, format picker, progress)
│   │   ├── lib/              # API client, i18n translations (EN/BN), local storage
│   │   └── types/            # TypeScript API contracts
│   ├── tests/                # Playwright E2E tests
│   └── package.json          # pnpm package configuration
├── infra/                    # Docker, Nginx, and deployment configs
│   └── docker-compose.yml    # Complete orchestration definition
└── docs/                     # Specifications and architecture docs
    ├── ARCHITECTURE.md       # High-level architecture and data flows
    ├── THREAT_MODEL.md       # STRIDE & DREAD security analysis
    └── api/
        └── openapi.yaml      # OpenAPI 3.1.0 specification (synced from FastAPI)
```

> **Note on Mobile Client**: A Flutter-based mobile client is planned for a future release. Currently, the Next.js web application is built as a fully responsive, mobile-first Progressive Web Application (PWA) compatible with all modern mobile browsers.

---

## 3. API Contract Summary

The API provides standardized endpoints for media extraction, asynchronous downloading, progress monitoring, and takedown claims:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/health`, `/api/v1/health` | `GET` | Service health, dependency status (PostgreSQL, Redis), disk space, and worker reachability. |
| `/api/v1/info`, `/api/v1/extract` | `POST` | Inspect media URL, validate against SSRF, and return available formats/qualities. |
| `/api/v1/downloads`, `/api/v1/jobs` | `POST` | Submit an asynchronous download job; returns job ID and job access token. |
| `/api/v1/downloads/{job_id}` | `GET` | Retrieve download job status and progress details. |
| `/api/v1/downloads/{job_id}/stream` | `GET` | Stream real-time progress via Server-Sent Events (SSE). |
| `/api/v1/downloads/{job_id}/file` | `GET` | Stream the downloaded media file using a signed expiring token. |
| `/api/v1/downloads/{job_id}` | `DELETE` | Cancel an in-flight job and purge its artifacts. |
| `/api/v1/takedown` | `POST` | File a DMCA or legal takedown notice. |

---

## 4. Running the Tests

### Backend Tests (pytest)

```bash
cd backend
# Create virtual environment if needed
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt
pytest -v
```

### Frontend Tests (Vitest & Playwright)

```bash
cd web
pnpm install
# Run unit & component tests
pnpm test
# Run TypeScript compilation & production build
pnpm run build
# Run Playwright E2E tests (requires running backend & web dev server)
pnpm run test:e2e
```
