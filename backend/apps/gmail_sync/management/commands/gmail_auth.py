from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Authorise read-only Gmail access (OAuth2) and store the token."

    def handle(self, *args, **options):
        raise CommandError("Not implemented yet (phase 2, FR-01).")
