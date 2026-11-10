# Mercadona Dashboard

Self-hosted platform to track supermarket spending from the digital Mercadona receipts that arrive in Gmail.

See [docs/functional-requirements.md](docs/functional-requirements.md) for the full specification and [PRIVACY.md](PRIVACY.md) for the privacy policy.

## Quick start

```bash
cp .env.example .env
make up            # docker compose up -d
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8001/api/ |
| Django admin | http://localhost:8001/admin/ (`make superuser` first) |

## Common commands

```bash
make logs            # follow logs
make test            # backend tests
make lint            # ruff
make makemigrations  # create migrations
make migrate         # apply migrations
```

## Conventions

- Everything is written in English except the UI, which is multilingual (`frontend/src/i18n/locales`).
- Conventional Commits (`feat:`, `fix:`, `chore:`…).
- Branches: `feature/*` → `develop` → `main` (only when lint and tests pass).
- Real receipt PDFs go in `backend/apps/receipts/tests/fixtures/private/` (git-ignored). Run
  `docker compose exec backend python -m apps.receipts.tests.anonymise_fixtures` to create
  their anonymised text fixtures.
