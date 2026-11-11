# Mercadona Dashboard

Self-hosted platform to track supermarket spending from the digital Mercadona receipts that arrive in Gmail.

![Home page with demo data](docs/images/home.png)

**New here? Follow the [installation guide](docs/installation.md)**: it walks through
Docker, the Gmail and Google Cloud setup (step by step) and the first import.

See [docs/functional-requirements.md](docs/functional-requirements.md) for the full specification and [PRIVACY.md](PRIVACY.md) for the privacy policy.

## Quick start

```bash
cp .env.example .env
make up            # docker compose up -d
```

The development stack does not start Celery (`worker`, `beat`): the daily jobs run on the
production server. Use `make up-jobs` to start them locally when working on tasks.

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
make backup          # database dump + receipt PDFs into backups/
make seed-demo       # fictitious receipts in an empty database (remove: seed_demo --remove)
```

## Production

To run it on a home server (nginx + gunicorn, starts on boot) see the
[installation guide](docs/installation.md) for a first install and
[docs/deployment.md](docs/deployment.md) for the stack, backups and moving to another machine.

## Conventions

- Everything is written in English except the UI, which is multilingual (`frontend/src/i18n/locales`).
- Conventional Commits (`feat:`, `fix:`, `chore:`…).
- Branches: `feature/*` → `develop` → `main` (only when lint and tests pass).
- Real receipts never go into git. PDFs go in `backend/apps/receipts/tests/fixtures/private/`;
  run `docker compose exec backend python -m apps.receipts.tests.anonymise_fixtures` to create
  their anonymised text versions (also git-ignored) used by local tests.
