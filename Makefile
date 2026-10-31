.PHONY: help up down build test test-backend test-web lint clean

help:
	@echo "AnyStream Video Downloader Management Commands:"
	@echo "  make up           - Start full container stack with Docker Compose"
	@echo "  make down         - Stop and remove all containers"
	@echo "  make build        - Rebuild all container images"
	@echo "  make test         - Run both backend and web test suites"
	@echo "  make test-backend - Run backend pytest suite"
	@echo "  make test-web     - Run frontend vitest suite"

up:
	docker compose -f infra/docker-compose.yml --env-file infra/.env up -d

down:
	docker compose -f infra/docker-compose.yml down

build:
	docker compose -f infra/docker-compose.yml build

test-backend:
	cd backend && pytest -v

test-web:
	cd web && pnpm test

test: test-backend test-web
