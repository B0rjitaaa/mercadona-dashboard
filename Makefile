.PHONY: up down build logs migrate makemigrations shell superuser test lint gmail-auth

up:            ; docker compose up -d
down:          ; docker compose down
build:         ; docker compose build
logs:          ; docker compose logs -f
migrate:       ; docker compose exec backend python manage.py migrate
makemigrations:; docker compose exec backend python manage.py makemigrations
shell:         ; docker compose exec backend python manage.py shell
superuser:     ; docker compose exec backend python manage.py createsuperuser
test:          ; docker compose exec backend pytest
lint:          ; docker compose exec backend ruff check .
gmail-auth:    ; docker compose run --rm -p 8080:8080 backend python manage.py gmail_auth
