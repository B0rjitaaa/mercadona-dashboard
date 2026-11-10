"""Mercadona receipt PDF parser.

Pure Python: it must not import anything from Django. It takes a PDF and returns
dataclasses, so it can be tested in isolation against real PDFs in tests/fixtures/.
"""
