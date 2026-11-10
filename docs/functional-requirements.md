# Mercadona Dashboard — Functional Requirements

> Self-hosted platform to track and analyse supermarket spending (initially Mercadona) from the digital receipts that arrive in a Gmail inbox.

- **Repository:** https://github.com/B0rjitaaa/mercadona-dashboard
- **Document version:** 0.7
- **Last updated:** 2026-11-10

### Changelog

| Version | Date | Changes |
|---|---|---|
| 0.1 | 2026-11-10 | Initial draft (Spanish). |
| 0.2 | 2026-11-10 | Translated to English. Added language policy (NFR-09, NFR-10), multilingual UI (FR-12), architecture & project structure (section 7). |
| 0.3 | 2026-11-10 | Gmail sender address (FR-01). Real receipt layout: VAT table and payment details (FR-02). Git branching model (NFR-11). Test fixture privacy (NFR-08). |
| 0.4 | 2026-11-10 | FR-01: dedicated mailbox with forwarded receipts, sync strategy, retries and concurrency. Data model: GmailMessage. |
| 0.5 | 2026-11-10 | FR-01: forward as attachment (.eml). FR-02: older receipt layout, return receipts, store identified by store code. |
| 0.6 | 2026-11-10 | Roadmap: web UI brought forward before product identification; until phase 3, products are grouped by receipt description. |
| 0.7 | 2026-11-10 | FR-04: identification against a daily local copy of the whole catalogue (no remote search), matching algorithm and thresholds. FR-05: catalogue price history comes from the same daily download. |

---

## 1. Goal

A web application that runs locally (Docker) and:

1. Automatically imports the Mercadona receipts that arrive by email every day.
2. Extracts every purchase line from the PDF (product, quantity, price, amount).
3. Links each line to the real product in Mercadona's catalogue, creating our own **product page**.
4. Shows how much is spent per month, what is bought and how prices evolve.

### Out of scope (v1)

- Access from outside the local network, multi-user accounts or permissions.
- Other supermarkets (the data model must allow it later, but it is not implemented now).
- Paper/photo receipts (OCR). Digital PDF only.

---

## 2. Glossary

| Term | Meaning |
|---|---|
| **Receipt (ticket)** | Simplified invoice (*factura simplificada*) PDF that Mercadona sends by email. |
| **Receipt line** | Each item inside a receipt (`Cnt.`, `Descripción`, `P. Unit`, `Importe`). |
| **Receipt description** | Abbreviated text printed on the receipt (e.g. `LECHE DESN P6`). |
| **Product** | Page in the platform representing a real item of Mercadona's catalogue. |
| **Alias** | Mapping between a receipt description and a product. A product can have many aliases. |
| **Store** | Shop where the purchase happened (address on the receipt). |
| **Warehouse (`wh`)** | Warehouse code used by Mercadona's API for prices and availability (e.g. `svq1`). |

---

## 3. Actors

- **User**: the single person using the platform (owner of the Gmail account).
- **System (scheduled jobs)**: background processes (Celery) that import emails, parse PDFs and query Mercadona's API.

---

## 4. Functional requirements

### FR-01 · Automatic receipt import from Gmail

**Description:** A scheduled job checks the Gmail inbox daily for new Mercadona receipts and downloads the attached PDF.

**Acceptance criteria:**

- Runs **once a day** at a configurable time (default 07:00).
- Can be **triggered manually** from the UI ("Sync now").
- Only processes emails matching a configurable filter (sender, subject and/or Gmail label). The filter lives in configuration, not in code.
- Receipts are sent by **`Ticket Digital Mercadona <ticket_digital@mail.mercadona.com>`**. Default filter: `from:ticket_digital@mail.mercadona.com has:attachment filename:pdf`.
- **Dedicated mailbox:** the recommended setup is a Gmail account used only for receipts. Receipts reach it via an automatic forwarding filter from the personal account (keeps the original sender) or by manual forwarding (sender becomes the personal address). Past receipts can be sent in bulk with Gmail's **"Forward as attachment"**: one email carrying many `.eml` files, each with its PDF. In that setup the filter is `has:attachment`; PDFs are extracted from direct attachments and from attached emails (`.eml`, nested at any depth), and any non-receipt PDF ends up as a receipt in "Error" status.
- An email may contain several PDFs (directly or inside attached emails); each one becomes a receipt.
- Every run lists all matching message IDs and skips the ones already seen, so the first run is the historical import and later runs only download new emails.
- A message that fails to download is retried on the next run.
- Only one sync can run at a time (database lock); a concurrent request is skipped.
- The PDF attachment is downloaded and stored locally so it can be re-processed.
- An already processed email **never creates a duplicate receipt** (checked by Gmail message ID and by simplified-invoice number).
- Optionally, processed emails get a Gmail label (e.g. `mercadona/processed`).
- First run performs a **historical import** (all matching emails), not just the last day.
- Gmail access uses OAuth2 with **read-only** scope (plus label modification if labelling is enabled).

**Run log:** each sync stores date, emails found, receipts created, duplicates skipped and errors.

---

### FR-02 · Receipt PDF parsing

**Description:** The system extracts the header, purchase lines and totals from the PDF.

**Header fields** (from the reference receipt):

| Field | Example |
|---|---|
| Company / tax ID | `MERCADONA, S.A.` / `A-46103834` |
| Store address | `CALLE EJEMPLO, 1` |
| Postal code and city | `28001 MADRID` |
| Phone | `910000000` |
| Date and time | `15/01/2026 10:30` |
| Operation (OP) | `1000001` |
| Simplified-invoice number | `1234-001-000001` (unique receipt identifier) |
| Total | `43,55 €` |
| Payment method | `TARJETA BANCARIA` |
| VAT breakdown | `4% 9,13 0,36 9,49` (rate, base, tax, total per rate) |

**Not stored:** card number digits, authorisation codes (`AUT`, `ARC`, `AID`) and card type printed below the VAT table.

**Layout versions:** older receipts have no `Cnt.` column header (`Descripción P. Unit Importe`) and a 3-column VAT table without the per-rate total; the printed store address also varies (`CT DE …` / `CTRA. DE …`, city in upper or title case). Both layouts must be supported.

**Store identification:** the first block of the invoice number is Mercadona's store code (`1234-001-000001` → store `1234`). Stores are identified by that code, not by the printed address.

**Return receipts:** marked with a `***** DEVOLUCIÓN *****` banner, a `DEVOLUCIÓN: <number>` line instead of `FACTURA SIMPLIFICADA` and `FRA. SIMPLIF. ORIGEN: <number>` (the refunded sale). Lines have negative quantity and amount, and the total is negative. They are stored as receipts of kind `return`, with lines of type `return`, so they reduce the spend of their month.

**Line types to support:**

1. **Single unit** — quantity 1, no unit price:
   `1 LECHE DESN P6 ............ 4,86`
2. **Multiple units** — quantity > 1, with unit price and amount:
   `2 SALMOREJO FRESCO   1,65   3,30`
3. **Weighed product** — the product line is followed by a line with weight and price per kg:
   `1 PLATANO` / `0,728 kg   3,20 €/kg   2,33`
4. **Other lines** that may appear on other receipts (discounts, returns, parking, etc.): must be detected and stored with a specific line type without breaking parsing.

**Footer:** after `TOTAL (€)` come the payment method line, the VAT table (`IVA BASE IMP. (€) CUOTA (€) TOTAL (€)`, one row per rate plus a `TOTAL` row) and the card payment details.

**Stored per line:** quantity (units or kg), unit of measure (`unit` / `kg`), description as printed, unit price (per unit or per kg), line amount.

If the receipt only shows the amount (quantity 1), unit price equals the amount.

**Validations:**

- The sum of line amounts must equal the `TOTAL`. Otherwise the receipt is flagged **"Needs review"** and highlighted in the UI.
- The sum of the VAT table totals must also equal the `TOTAL`.
- Amounts use a decimal comma (`4,86`) and are converted to exact decimals (never `float`).
- If the PDF cannot be parsed, the receipt is set to **"Error"** with the reason, and the original PDF is kept for retry.

**Receipt statuses:** `Pending` → `Processed` | `Needs review` | `Error`.

**Re-processing:** the user can re-run parsing on a receipt (useful after parser improvements).

---

### FR-03 · Manual receipt upload

**Description:** Besides Gmail, the user can upload a PDF from the UI.

- Same processing and validations as FR-02.
- Same duplicate check by simplified-invoice number.

---

### FR-04 · Product identification with Mercadona's API

**Description:** Each receipt description is linked to a real product of Mercadona's catalogue, and a product page is created (or reused) in the platform.

**API context:**

- Reference endpoint: `https://tienda.mercadona.es/api/home/?lang=es&wh=svq1&postal_code=41008`
- Endpoints used: `GET /api/categories/` (sections and categories) and `GET /api/categories/{id}/` (subcategories with their products and prices). The **whole catalogue (~4,300 products) is downloaded once a day** (~150 requests, ~1.5 minutes, 0.3 s between requests) and stored locally; identification runs locally against that copy, so no remote search endpoint is needed.
- `postal_code` and `wh` (warehouse) determine prices and assortment. Both must be **configurable** (default `41008` / `svq1`).
- The API is not public nor officially documented: it may change without notice. The integration must be isolated in a single module and be fault tolerant (if the API is down, the receipt is still stored and identification is retried later).
- Requests must be rate limited and cached.

**Identification process:**

1. **Known alias:** if the receipt description already has an alias, it is used directly. No API call.
2. **Automatic search:** otherwise the local catalogue is searched using the normalised description (accents removed, known abbreviations expanded: `LS` → Listo para Comer, `Q.` → Queso, `1/2` → Media, `P6` → Pack-6).
3. **Confidence score:** each candidate gets `0.7 × text + 0.3 × price`. Text: weighted share of receipt tokens that are a prefix of a word in the product name or packaging (`DESN` → *desnatada*; plurals allowed; a long token never matches a short word it merely starts with). Price: closeness of the last paid price to the current catalogue price (per kg for weighed products), 0 at 25 % difference.
   - High confidence (score ≥ 0.85 and ≥ 0.08 above the second candidate) → linked automatically and alias created.
   - Low confidence or several candidates → line stays **"Unidentified"**.
4. **Manual review:** in an "Unidentified products" inbox the user sees the receipt description and the proposed candidates (name, photo, packaging, price) and can:
   - Confirm a candidate.
   - Search the catalogue manually and pick another.
   - Link to an existing product in the platform.
   - Create a "manual" product (not linked to Mercadona) if it is not in the online catalogue.
5. The decision is stored as an alias: **next time that description appears it is linked automatically.**

> Receipt descriptions are abbreviated (`BURGER M VA/CE 500G`, `T CHOCO CRUJIENTE`), so manual review will be frequent at the beginning and nearly zero once aliases are trained.

**Product data from the API** (when available): Mercadona ID, full name, brand, photo(s), packaging (e.g. "6 bricks x 1 L"), current price, reference unit price (€/L, €/kg), category and subcategory, online shop URL.

**Correction:** the user can undo or change a link; affected historical lines are reassigned.

---

### FR-05 · Catalogue price tracking

**Description:** Besides the price the user paid (receipts), the catalogue price of identified products is stored periodically.

- Prices come from the daily catalogue download (FR-04), for every product in the catalogue, bought or not.
- A new record is stored only when the price **changes** (unit price or price per kg/L).
- If a product leaves the catalogue it is flagged **"Discontinued"** without deleting its history.

Each product therefore has two price series:

- **Paid price** (from my receipts): only when I buy it.
- **Catalogue price** (from the API): continuous, even when I don't buy it.

---

### FR-06 · Product page

**Description:** Detail page for each product.

**Content:**

- Basic data: photo, name, brand, packaging, category, link to Mercadona's online shop, status (active/discontinued).
- Associated receipt aliases (e.g. `LECHE DESN P6`).
- **Indicators:**
  - Times bought and total units/kg.
  - Total amount spent on the product.
  - First and last purchase.
  - Average purchase frequency (e.g. "every 9 days").
  - Current, minimum, maximum and average price.
  - Price change since first purchase (in € and %).
- **Charts:**
  - Price over time: paid price (one point per purchase) and catalogue price (continuous line) on the same chart.
  - For weighed products, price is shown in €/kg.
  - Units bought / spend per month (bars).
- **Purchase history:** table with date, receipt (link), quantity, unit price and amount.

---

### FR-07 · Monthly spending

**Description:** View to know how much is spent each month.

- Current month total compared with the previous month and the 12-month average.
- Bar chart with spend per month (range selector: 6 months, 12 months, all).
- Number of receipts and average receipt per month.
- Spend breakdown by **category** (Mercadona's product category), with distribution chart.
- **Top products** of the month by spend and by number of purchases.
- Selecting a month navigates to that month's receipts.

---

### FR-08 · Receipt list and detail

- Receipt list filterable by date range, store, status and free-text search (product).
- Columns: date, store, number of items, total, payment method, status.
- Receipt detail: header, lines (linked to each product page or flagged "unidentified"), totals and access to the original PDF.
- Actions: re-process, delete, manually correct a line.

---

### FR-09 · Product list

- Own catalogue with every product ever bought.
- Search by name, filter by category and status.
- Sort by: most bought, highest spend, largest price increase, most recently bought.
- Card or table view, with a price sparkline.

---

### FR-10 · Dashboard (home page)

At-a-glance summary:

- Current month spend vs. previous month.
- Spend chart for the last 12 months.
- Latest imported receipts.
- **Price alerts:** frequently bought products whose catalogue price recently went up or down.
- Pending items: receipts in "Needs review"/"Error" and unidentified products.
- Date and result of the last Gmail sync.

---

### FR-11 · Settings

Screen (or environment variables) for:

- Connecting/disconnecting the Gmail account (OAuth flow).
- Email filter (sender, subject, label).
- Time of the daily sync and of the price update.
- Postal code and warehouse (`wh`) for Mercadona's API.
- Whether to label processed emails.

---

### FR-12 · Multilingual user interface

**Description:** The frontend is available in several languages.

- Initial languages: **Spanish (`es`)** and **English (`en`)**. Adding a new language only requires adding a translation file.
- The initial language is detected from the browser; if not supported, falls back to English.
- Language selector always visible in the UI; the choice is remembered in the browser.
- Dates, numbers and currency are formatted according to the selected language (e.g. `1.234,56 €` in `es`, `€1,234.56` in `en`), using the browser's `Intl` API.
- Data coming from receipts or from Mercadona's catalogue (product names, receipt descriptions, categories) is shown **as is**, not translated.
- The backend API is language-neutral: it returns codes (e.g. receipt status `needs_review`) and the frontend translates them.

---

## 5. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 | **Local deployment** with `docker compose up`: every service (backend, worker, scheduler, database, Redis, frontend) runs in containers. |
| NFR-02 | **Privacy:** data, PDFs and Gmail credentials are stored locally only. Credentials are never committed (`.env` and `secrets/` are git-ignored; an `.env.example` is provided). |
| NFR-03 | **Idempotency:** running sync or re-processing several times never duplicates data. |
| NFR-04 | **Resilience:** a Gmail or Mercadona API failure does not stop the rest; jobs retry with exponential backoff. |
| NFR-05 | **Traceability:** the original PDF of each receipt and the log of every job run are kept. |
| NFR-06 | **Monetary precision:** every amount is stored as an exact decimal. |
| NFR-07 | **Extensibility:** the data model allows other supermarkets in the future (store chain as its own entity, one parser per chain). |
| NFR-08 | **Quality:** automated parser tests against real receipts covering every line type. Real receipts (PDFs and their anonymised text versions) are kept locally in git-ignored folders, since even without card data they reveal purchase history and location and the repository is public; their tests are skipped when absent. Committed fixtures are synthetic. Lint (`ruff`) and tests must pass before merging. |
| NFR-09 | **Project language:** everything except the frontend UI is written in **English**: code, identifiers, comments, docstrings, API fields, log messages, documentation, commit messages and pull requests. |
| NFR-10 | **UI language:** the frontend is multilingual (see FR-12). No user-facing text is hard-coded in components; it always goes through translation files. |
| NFR-11 | **Version control:** commits are authored by the repository owner (Borja), Conventional Commits style (`feat:`, `fix:`, `chore:`…). Branching model: `feature/*` → `develop` → `main`. Features are merged into `develop`; `develop` is merged into `main` only when lint and tests pass. |

---

## 6. Technology stack

| Layer | Technology |
|---|---|
| Backend / API | Python 3.13 + Django 5.2 + Django REST Framework |
| Background jobs | Celery (worker) + Celery Beat (scheduler) |
| Broker / cache | Redis |
| Database | **PostgreSQL 16** |
| Frontend | React + TypeScript (Vite), React Router, TanStack Query |
| Internationalisation | i18next + react-i18next |
| Charts | Recharts |
| PDF parsing | `pdfplumber` |
| Gmail | Gmail API with OAuth2 |
| Tooling | `uv` (Python deps), `ruff`, `pytest`, Vitest |
| Infrastructure | Docker + docker compose |

### Why PostgreSQL

- First-class Django support (`Decimal`, `JSONField`, full-text search).
- Fuzzy text matching via the `pg_trgm` extension, very useful to compare abbreviated receipt descriptions with product names (FR-04).
- Date functions (`date_trunc`) to aggregate monthly spending efficiently (FR-07).
- `JSONField` to keep the raw Mercadona API response without modelling every field.
- Official, lightweight Docker image, easy to back up with `pg_dump`.

*Alternative:* SQLite would be enough for the data volume, but struggles with concurrent writes from several Celery workers and lacks `pg_trgm`.

---

## 7. Architecture and project structure

### Repository layout

Monorepo with backend and frontend side by side.

```
mercadona-dashboard/
├── docker-compose.yml
├── .env.example
├── Makefile                  # shortcuts: make up, make test, make migrate…
├── docs/
│   └── functional-requirements.md
├── secrets/                  # Gmail credentials/token (git-ignored)
├── backend/
│   ├── Dockerfile            # single image for api, worker and beat
│   ├── pyproject.toml
│   ├── manage.py
│   ├── config/               # Django project
│   │   ├── settings/ (base.py, dev.py)
│   │   ├── urls.py
│   │   └── celery.py         # Celery app + Beat schedule
│   └── apps/
│       ├── core/             # shared base models, job run log, settings
│       ├── receipts/         # Store, Receipt, ReceiptLine
│       │   └── parsing/      # PDF parser (pure Python, no Django)
│       ├── gmail_sync/       # Gmail client, OAuth, sync_gmail task
│       ├── mercadona/        # API client (no models)
│       ├── products/         # Product, ProductAlias, CatalogPrice, matching
│       └── analytics/        # read-only endpoints: monthly spend, top products…
└── frontend/
    ├── Dockerfile
    ├── package.json
    └── src/
        ├── api/              # HTTP client + types
        ├── i18n/             # i18next setup + locales/{es,en}.json
        ├── features/
        │   ├── dashboard/
        │   ├── receipts/
        │   ├── products/
        │   ├── spending/
        │   ├── review/       # "unidentified products" inbox
        │   └── settings/
        ├── components/       # shared UI, charts
        └── routes.tsx
```

### Backend apps

| App | Responsibility | Requirements |
|---|---|---|
| `receipts` | Models, manual upload, re-processing and the **parser** | FR-02, FR-03, FR-08 |
| `gmail_sync` | OAuth, email search, PDF download, daily job | FR-01 |
| `mercadona` | Isolated HTTP client: caching, rate limiting, retries | FR-04, FR-05 |
| `products` | Product pages, aliases, matching algorithm, catalogue prices | FR-04, FR-05, FR-06, FR-09 |
| `analytics` | Aggregation queries, no own models | FR-07, FR-10 |
| `core` | Job run log, settings editable from the UI | FR-11 |

Two pieces are kept as **pure Python, independent from Django**:

- **PDF parser** — takes a PDF and returns dataclasses. Tested against real PDFs stored as fixtures; it is the part most likely to change.
- **Mercadona client** — if the API changes, only this module is touched.

### Docker services

| Service | Image / command | Host port (default) |
|---|---|---|
| `db` | `postgres:16-alpine` (volume `pgdata`) | 5433 |
| `redis` | `redis:7-alpine` | — |
| `backend` | `./backend` — Django dev server | 8001 |
| `worker` | `./backend` — `celery -A config worker` | — |
| `beat` | `./backend` — `celery -A config beat` | — |
| `frontend` | `./frontend` — Vite dev server (proxies `/api` to `backend`) | 5173 |

- `backend`, `worker` and `beat` share **the same image**, only the command differs.
- PDFs are stored in a `media` volume shared by `backend` and `worker`.
- Host ports are configurable in `.env` (`BACKEND_HOST_PORT`, `FRONTEND_HOST_PORT`, `POSTGRES_HOST_PORT`).
- **Gmail OAuth:** first authorisation is done with `make gmail-auth` (`python manage.py gmail_auth`), which opens the browser flow. The token refreshes automatically afterwards.

---

## 8. Data model (conceptual)

```
Store ──< Receipt ──< ReceiptLine >── Product ──< CatalogPrice
                                         │
                                         └──< ProductAlias

GmailMessage (every email seen by the sync)
JobRun (log of background job executions)
```

| Entity | Main fields |
|---|---|
| **Store** | Chain, address, postal code, city, phone. |
| **Receipt** | Simplified-invoice number (unique), date/time, operation number, store, total, payment method, status, PDF (unique by SHA-256), source (`upload`/`gmail`), Gmail message ID. |
| **ReceiptLine** | Receipt, line type, original description, quantity, unit (`unit`/`kg`), unit price, amount, product (optional). |
| **Product** | Mercadona ID (optional), name, brand, packaging, category, photo, URL, status, raw API data. |
| **ProductAlias** | Normalised receipt description → product; source (automatic/manual). |
| **CatalogPrice** | Product, date, price, reference unit price. |
| **GmailMessage** | Gmail message ID (unique), received date, sender, subject, number of PDFs, status (`imported`, `duplicate`, `no_pdf`, `error`). |
| **JobRun** | Job type, start, end, result, counters, errors. |

---

## 9. Scheduled jobs

| Job | Frequency | Description |
|---|---|---|
| `sync_gmail` | Daily (configurable) + manual | Finds new emails, downloads PDFs and queues their parsing. |
| `parse_receipt` | Per PDF | Extracts header and lines, validates totals, stores the receipt. |
| `match_products` | After each receipt + daily retry | Links unmatched lines using aliases or Mercadona's API. |
| `update_catalog_prices` | Daily | Updates the catalogue price of linked products. |

---

## 10. Main flow

```
Gmail ──(sync_gmail)──> PDF stored
                           │
                    (parse_receipt)
                           │
              Receipt + lines in DB ── total matches? ── no ──> "Needs review"
                           │
                    (match_products)
                    ┌──────┴────────┐
               known alias      no alias
                    │               │
                    │      Mercadona API search
                    │          ┌────┴────┐
                    │        high       low
                    │     confidence  confidence
                    │          │          │
                    └────> Product   "Unidentified" inbox
                              │          │ (user picks)
                              │<─────────┘ (alias created)
                              │
                 Product page + price history
```

---

## 11. Roadmap

| Phase | Scope |
|---|---|
| **1 · Foundation** | docker compose with every service, models, Django admin, manual PDF upload and parser (FR-02, FR-03, FR-08 API). |
| **2 · Gmail** | OAuth, daily and manual sync, historical import (FR-01). |
| **3 · Products** | Mercadona API integration, aliases and review inbox (FR-04). |
| **4 · Analytics & UI** | Monthly spend, product page with charts, dashboard, multilingual UI (FR-06, FR-07, FR-09, FR-10, FR-12). **Brought forward before phase 3**: products are grouped by receipt description until they are linked to the catalogue; category breakdown (FR-07) and catalogue price (FR-06) arrive with phases 3 and 5. |
| **5 · Prices** | Daily catalogue price tracking and alerts (FR-05). |

---

## 12. Risks and open questions

- **Unofficial Mercadona API:** it may change or block requests. Mitigation: isolated module, caching, low request rate, and the platform keeps working with receipt data alone if the API fails.
- **Search endpoint:** need to confirm which endpoint allows text search of products (the online shop uses its own search engine); validate in phase 3.
- **Abbreviated descriptions:** automatic identification won't be perfect; the manual review inbox is essential.
- **Receipt format variations:** collect several real PDFs (with discounts, returns, weighed products, different payment methods) for parser tests.
- **Catalogue price vs. physical store:** the online price for warehouse `svq1` may differ from the physical store; that's why both series are stored separately.
- **To decide:** automatic database backups?
