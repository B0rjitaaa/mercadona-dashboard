.PHONY: up up-jobs down build logs migrate makemigrations shell superuser test lint gmail-auth

up:            ; docker compose up -d
up-jobs:       ; docker compose --profile jobs up -d
down:          ; docker compose --profile jobs down
build:         ; docker compose build
logs:          ; docker compose logs -f
migrate:       ; docker compose exec backend python manage.py migrate
makemigrations:; docker compose exec backend python manage.py makemigrations
shell:         ; docker compose exec backend python manage.py shell
superuser:     ; docker compose exec backend python manage.py createsuperuser
test:          ; docker compose exec backend pytest
lint:          ; docker compose exec backend ruff check .
gmail-auth:    ; docker compose run --rm -p 8080:8080 backend python manage.py gmail_auth

# --- Production (home server) -------------------------------------------------
# PROD=1 makes the backup/restore targets act on the production stack.
PROD_COMPOSE := docker compose -f docker-compose.prod.yml
COMPOSE := $(if $(PROD),$(PROD_COMPOSE),docker compose)

STAMP := $(shell date +%Y%m%d-%H%M%S)

.PHONY: prod-up prod-down prod-logs prod-ps prod-backup-now backup restore

prod-up:       ; $(PROD_COMPOSE) up -d --build
prod-down:     ; $(PROD_COMPOSE) down
prod-logs:     ; $(PROD_COMPOSE) logs -f
prod-ps:       ; $(PROD_COMPOSE) ps
prod-backup-now: ; $(PROD_COMPOSE) exec backup sh /usr/local/bin/backup.sh

# Database dump + receipt PDFs into backups/ (git-ignored)
backup:
	mkdir -p backups
	$(COMPOSE) exec -T db sh -c 'pg_dump -U "$$POSTGRES_USER" -Fc "$$POSTGRES_DB"' > backups/db-$(STAMP).dump
	$(COMPOSE) exec -T backend tar -C /app/media -cf - . > backups/media-$(STAMP).tar
	@ls -lh backups/*-$(STAMP).*

# make restore DB=backups/db-X.dump MEDIA=backups/media-X.tar [PROD=1]
restore:
	@test -n "$(DB)" || (echo "DB=<file.dump> is required" && exit 1)
	$(COMPOSE) up -d db
	$(COMPOSE) exec -T db sh -c 'until pg_isready -q; do sleep 1; done'
	$(COMPOSE) exec -T db sh -c 'pg_restore -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" --clean --if-exists --no-owner' < $(DB)
	$(if $(MEDIA),$(COMPOSE) run --rm --no-deps -T backend tar -C /app/media -xf - < $(MEDIA))
