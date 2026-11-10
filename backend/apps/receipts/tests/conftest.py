from pathlib import Path

import pytest

from .pdf_factory import build_receipt_pdf

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_text() -> str:
    return (FIXTURES / "sample_receipt.txt").read_text(encoding="utf-8")


@pytest.fixture
def sample_pdf(sample_text) -> bytes:
    return build_receipt_pdf(sample_text)


@pytest.fixture(autouse=True)
def _isolated_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture(autouse=True)
def _eager_celery(settings):
    from config.celery import app

    app.conf.task_always_eager = True
    yield
    app.conf.task_always_eager = False
