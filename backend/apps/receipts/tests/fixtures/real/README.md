# Anonymised real receipts

Text versions of the PDFs in `../private/`, with card digits and payment authorisation
codes removed. **Git-ignored**: even without payment data they reveal purchase history,
dates and store location, and this repository is public.

Generate them with:

    docker compose exec backend python -m apps.receipts.tests.anonymise_fixtures

`test_real_receipts.py` runs against every file here and is skipped when there are none.
