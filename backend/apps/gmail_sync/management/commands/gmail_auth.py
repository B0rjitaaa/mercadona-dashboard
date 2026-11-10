from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from google_auth_oauthlib.flow import InstalledAppFlow

from apps.gmail_sync.client import SCOPES


class Command(BaseCommand):
    help = "Authorise Gmail access (read receipts, send the weekly report) and store the token."

    def add_arguments(self, parser):
        parser.add_argument("--port", type=int, default=8080)

    def handle(self, *args, port: int, **options):
        credentials = Path(settings.GMAIL_CREDENTIALS_FILE)
        if not credentials.exists():
            raise CommandError(
                f"{credentials} not found. Download the OAuth 'Desktop app' client JSON "
                "from Google Cloud Console and save it there."
            )

        flow = InstalledAppFlow.from_client_secrets_file(str(credentials), SCOPES)
        # Running inside Docker: listen on all interfaces, redirect to the host's localhost.
        creds = flow.run_local_server(
            host="localhost",
            bind_addr="0.0.0.0",
            port=port,
            open_browser=False,
            authorization_prompt_message="\nOpen this URL in your browser:\n\n{url}\n",
            success_message="Mercadona Dashboard is now authorised. You can close this window.",
            prompt="consent",
            access_type="offline",
        )
        token = Path(settings.GMAIL_TOKEN_FILE)
        token.write_text(creds.to_json())
        self.stdout.write(self.style.SUCCESS(f"Token saved to {token}"))
