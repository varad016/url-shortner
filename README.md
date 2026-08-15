# URL Shortener — 3-Tier App

A simple 3-tier URL shortener, built to later deploy on Kubernetes with a Jenkins CI/CD pipeline.

## Architecture

- **Presentation tier**: Nginx — reverse proxy, entry point on port 8080
- **Application tier**: Flask (Gunicorn) — shorten/redirect/stats API + serves the single HTML page
- **Data tier**: PostgreSQL — stores `code -> original_url` mappings and click counts

```
client -> nginx (80) -> app (5000, gunicorn) -> postgres (5432)
```

## Run locally

```bash
docker compose up --build
```

Then open http://localhost:8080

## API

- `POST /api/shorten` — body `{"url": "https://..."}` → `{"short_url": "...", "code": "...", "original_url": "..."}`
- `GET /<code>` — 302 redirect to the original URL
- `GET /api/stats/<code>` — `{"code", "original_url", "created_at", "clicks"}`
- `GET /health` — health check for probes/load balancers

## Config (env vars, app tier)

| Var | Default |
|---|---|
| `DB_HOST` | `db` |
| `DB_PORT` | `5432` |
| `DB_NAME` | `urlshortener` |
| `DB_USER` | `postgres` |
| `DB_PASSWORD` | `postgres` |
| `BASE_URL` | `http://localhost:8080` |
| `CODE_LENGTH` | `6` |

## Next steps (K8s + Jenkins)

- Push `app` image to DockerHub
- Write K8s manifests: Deployment + Service for `app`, `nginx`, and `db` (or a StatefulSet + PVC for Postgres)
- Add a Jenkinsfile (Clone → Build → Push → Deploy), similar to the earlier Django project's pipeline
