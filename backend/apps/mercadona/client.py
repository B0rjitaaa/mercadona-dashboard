"""Client for the (unofficial) tienda.mercadona.es API.

Every call to Mercadona goes through this module, so an API change only affects it.
The API is undocumented: requests are throttled, retried with backoff and identified
with a plain user agent.
"""

import time
from collections.abc import Iterator
from dataclasses import dataclass

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "Mozilla/5.0 (compatible; mercadona-dashboard/0.1)"


class MercadonaError(Exception):
    pass


@dataclass(frozen=True)
class CatalogEntry:
    """A product as listed in a category page, with where it was found."""

    product: dict
    section: dict  # level 0 (e.g. "Aceite, especias y salsas")
    category: dict  # level 1 (e.g. "Aceite, vinagre y sal")
    subcategory: dict  # level 2 (e.g. "Aceite de oliva")


class MercadonaClient:
    def __init__(
        self,
        warehouse: str | None = None,
        postal_code: str | None = None,
        delay: float = 0.3,
        session: requests.Session | None = None,
    ):
        self.base_url = settings.MERCADONA_BASE_URL.rstrip("/")
        self.warehouse = warehouse or settings.MERCADONA_WAREHOUSE
        self.postal_code = postal_code or settings.MERCADONA_POSTAL_CODE
        self.delay = delay
        self.session = session or self._build_session()

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=4,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        return session

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        params = {"lang": "es", "wh": self.warehouse}
        try:
            response = self.session.get(url, params=params, timeout=20)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise MercadonaError(f"GET {path} failed: {exc}") from exc
        finally:
            if self.delay:
                time.sleep(self.delay)

    def categories(self) -> list[dict]:
        """Sections (level 0) with their categories (level 1)."""
        return self._get("categories/")["results"]

    def category(self, category_id: int) -> dict:
        """A level-1 category with its subcategories (level 2) and their products."""
        return self._get(f"categories/{category_id}/")

    def iter_catalog(self, errors: list[str] | None = None) -> Iterator[CatalogEntry]:
        """Every product of the catalogue. Failed categories are appended to `errors`."""
        for section in self.categories():
            for category in section.get("categories", []):
                try:
                    data = self.category(category["id"])
                except MercadonaError as exc:
                    if errors is None:
                        raise
                    errors.append(str(exc))
                    continue
                for subcategory in data.get("categories", []):
                    for product in subcategory.get("products", []):
                        yield CatalogEntry(product, section, category, subcategory)
