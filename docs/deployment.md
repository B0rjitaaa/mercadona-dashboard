# Deployment (home server)

The production stack runs on any Linux machine with Docker (e.g. Linux Mint) and is
reachable from the local network. It is **not** meant to be exposed to the Internet:
there is no login and it is served over plain HTTP.

| Service | Role |
|---|---|
| `web` | nginx: serves the compiled React app and receipt PDFs, proxies `/api`, `/admin` and `/static` |
| `backend` | Django under gunicorn (runs migrations and `collectstatic` on start) |
| `worker` / `beat` | Celery: daily catalogue download (06:00) and Gmail import (07:00) |
| `db` / `redis` | PostgreSQL 16 and Redis, only reachable inside the compose network |

Every service has `restart: unless-stopped`, so the stack comes back after a reboot as
long as Docker starts on boot (`sudo systemctl enable docker`).

## 1. Prepare the server

```bash
# Docker Engine + compose plugin (Linux Mint / Ubuntu)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # log out and back in

git clone https://github.com/B0rjitaaa/mercadona-dashboard.git
cd mercadona-dashboard
cp .env.prod.example .env       # fill in the blanks
```

Copy the Gmail OAuth files from the old machine into `secrets/`
(`credentials.json` and `token.json`). Without them, run `make gmail-auth` on the server.

## 2. Move the data (optional)

On the old machine, with its stack running:

```bash
make backup                      # → backups/db-<stamp>.dump and backups/media-<stamp>.tar
scp backups/*-<stamp>.* secrets/*.json <server>:mercadona-dashboard/...
```

On the server:

```bash
make restore PROD=1 DB=backups/db-<stamp>.dump MEDIA=backups/media-<stamp>.tar
```

## 3. Start

```bash
make prod-up      # build and start everything
make prod-ps      # status
make prod-logs    # follow logs
```

Open `http://<server-ip>:8080` (port set by `WEB_PORT`).

## Weekly email summary

Set `REPORT_EMAIL_TO` (and optionally `REPORT_DAY`, `REPORT_HOUR`, `REPORT_BASE_URL`) in
`.env` and run `make prod-up`. Sending needs a Gmail token with send permission; tokens
created before the summary existed can only read. Authorise again where you have a browser
(the OAuth redirect goes to `localhost`), e.g. on the development machine with
`make gmail-auth`, then copy `secrets/token.json` to the server and restart `worker`.
Settings → "Weekly email summary" shows whether the token can send, a preview and a
"Send now" button.

## Updating

```bash
git pull && make prod-up
```

## Backups

If the server already has a backup system, point it at the `db` service (`pg_dump`) and the
`media` volume. Setting `COMPOSE_FILE=docker-compose.prod.yml` in `.env` makes a plain
`docker compose` in this folder act on the production stack, which most scripts expect.

Otherwise enable the built-in `backup` service with `COMPOSE_PROFILES=backup` in `.env`.
It runs `deploy/backup.sh` every day at `BACKUP_HOUR:BACKUP_MINUTE` (03:30 by default):
a database dump and a tarball of the receipt PDFs go into `backups/` (git-ignored) and
files older than `BACKUP_KEEP_DAYS` (14) are deleted.

```bash
make prod-backup-now                 # run it immediately (backup profile)
make prod-logs                       # "backup ok" lines from the backup service
make restore PROD=1 DB=backups/db-<stamp>.dump MEDIA=backups/media-<stamp>.tar
```

The backups live on the same disk as the data: they protect against mistakes and
broken updates, not against a dead disk. Copy `backups/` elsewhere from time to time.
