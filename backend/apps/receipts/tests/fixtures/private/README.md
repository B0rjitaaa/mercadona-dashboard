# Private receipt PDFs

Real receipts used by `test_real_receipts.py`. **This folder is git-ignored**
(PDFs contain card digits and payment authorisation codes).

Naming: `YYYY-MM-DD_<total>.pdf`. For each PDF, an anonymised text version with the
same base name lives in `../real/` and is committed, so the parser is always tested
against real layouts even without the PDFs.
