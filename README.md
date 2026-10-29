# AnyStream Video Platform - Monorepo

A security-first, high-performance video downloader platform comprising a unified FastAPI backend, Next.js web application, and Flutter mobile application.

---

## 1. Project Overview & Capabilities

- **Unified API Gateway**: Serves both Web and Mobile clients with identical data contracts.
- **Pure Python Execution**: Uses `yt-dlp` as a library without shell string interpolations.
- **SSRF Defense-in-Depth**: Strict URL scheme whitelisting, DNS pre-resolution, and comprehensive CIDR blacklisting blocking private, loopback, link-local, and cloud metadata IP ranges.
- **Isolated Workers**: Non-root containerized Celery workers with CPU/memory limits and dedicated ephemeral storage with automated 20-minute eviction.
- **Zero Raw PII Storage**: Client IPs are non-reversibly hashed via HMAC-SHA256 with rotating salts.
- **Real-Time Progress**: High-efficiency Server-Sent Events (SSE) with HTTP polling fallback.
- **Multi-Language & Accessible**: English (`en`) and Bangla (`bn`) internationalization with WCAG AA compliance.
- **Legal Safeguards**: Native DMCA/copyright takedown registry, DRM refusal checks, and Terms of Service enforcement.

---

## 2. Monorepo Directory Layout

```
.
├── backend/                  # FastAPI Backend & Worker Pipeline
│   ├── app/
│   │   ├── core/             # Security, config, SSRF validator, error codes
│   │   │   ├── config.py     # Pydantic BaseSettings
│   │   │   ├── errors.py     # Custom structured HTTP exceptions
│   │   │   ├── security.py   # IP hashing, filename sanitizer, token signing
│   │   │   └── ssrf.py       # CIDR blacklist & DNS resolver guard
│   │   ├── db/               # SQLAlchemy async session management
│   │   ├── models/           # DeclarativeBase ORM entities
│   │   │   ├── job.py        # DownloadJob entity & JobStatus enum
│   │   │   ├── takedown.py   # TakedownRecord entity & status
│   │   │   └── abuse.py      # Salted HMAC IP abuse audit trail
│   │   ├── schemas/          # Pydantic v2 request/response schemas
│   │   │   ├── extract.py    # URL inspection & format contracts
│   │   │   ├── job.py        # Job submission & SSE progress event schemas
│   │   │   ├── takedown.py   # Legal claim submission contracts
│   │   │   └── health.py     # Diagnostics contract
│   │   └── main.py           # (Phase 2)
│   ├── tests/                # Automated pytest suite
│   │   ├── test_ssrf.py      # SSRF & IP CIDR unit tests
│   │   ├── test_security.py  # Path traversal & cryptographic token tests
│   │   ├── test_schemas.py   # Input validation & injection rejection tests
│   │   └── test_models.py    # SQLAlchemy entity tests
│   ├── requirements.txt      # Production dependencies
│   └── requirements-dev.txt  # Testing and linting suite
├── frontend/                 # (Phase 3: Next.js App Router, Tailwind CSS, i18n)
├── mobile/                   # (Phase 4: Flutter Clean Architecture, Download Manager)
├── infra/                    # Docker, Nginx, and deployment configs
│   └── docker-compose.yml    # Complete orchestration definition
└── docs/                     # Specifications and architecture docs
    ├── ARCHITECTURE.md       # High-level architecture and data flows
    ├── THREAT_MODEL.md       # STRIDE & DREAD security analysis
    └── api/
        └── openapi.yaml      # OpenAPI 3.1.0 specification
```

---

## 3. Phase 1 Deliverables Summary

| Artifact | Location | Description |
| :--- | :--- | :--- |
| **Architecture Specification** | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System components, sequence flows, data lifecycle, and tech justifications. |
| **Threat Model** | [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) | STRIDE / DREAD threat modeling, SSRF defenses, and container isolation. |
| **OpenAPI 3.1 Spec** | [`docs/api/openapi.yaml`](docs/api/openapi.yaml) | Complete API schema, error models, and SSE contracts. |
| **SQLAlchemy Data Models** | [`backend/app/models/`](backend/app/models/) | `DownloadJob`, `TakedownRecord`, `AbuseLog` with full typing. |
| **Pydantic Validation Schemas** | [`backend/app/schemas/`](backend/app/schemas/) | Strictly validated data transfer objects rejecting shell characters and invalid protocols. |
| **SSRF & Security Core** | [`backend/app/core/`](backend/app/core/) | Comprehensive CIDR blocker, signed expiring download tokens, and RFC-compliant filename sanitizer. |
| **Unit Test Suite** | [`backend/tests/`](backend/tests/) | Automated unit tests for SSRF, security, schemas, and models. |

---

## 4. Running the Tests

To execute the test suite (once Python 3.12 virtual environment is created):

```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
# source venv/bin/activate

pip install -r requirements-dev.txt
pytest -v
```

