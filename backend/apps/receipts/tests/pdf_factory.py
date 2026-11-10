"""Build receipt-like PDFs for tests, mimicking the Mercadona column layout."""

import io
import re

from reportlab.lib.pagesizes import A6
from reportlab.pdfgen import canvas

RE_ITEM = re.compile(r"^(\d+) (.+?)(?: (\d+,\d{2}))? (-?\d+,\d{2})$")
RE_WEIGHT = re.compile(r"^(\S+ kg) (\S+ €/kg) (\S+)$")


def build_receipt_pdf(text: str) -> bytes:
    buffer = io.BytesIO()
    width, height = A6
    pdf = canvas.Canvas(buffer, pagesize=A6)
    y = height - 20
    in_items = False

    for line in text.strip().splitlines():
        pdf.setFont("Helvetica", 7)
        if line.startswith("Cnt."):
            in_items = True
            pdf.drawString(15, y, "Cnt. Descripción")
            pdf.drawRightString(200, y, "P. Unit")
            pdf.drawRightString(width - 15, y, "Importe")
        elif in_items and (m := RE_WEIGHT.match(line)):
            pdf.drawString(40, y, m[1])
            pdf.drawRightString(200, y, m[2])
            pdf.drawRightString(width - 15, y, m[3])
        elif in_items and (m := RE_ITEM.match(line)):
            pdf.drawRightString(22, y, m[1])
            pdf.drawString(27, y, m[2])
            if m[3]:
                pdf.drawRightString(200, y, m[3])
            pdf.drawRightString(width - 15, y, m[4])
        elif line.startswith(("TOTAL", "TARJETA", "EFECTIVO")):
            pdf.setFont("Helvetica-Bold", 7)
            label, amount = line.rsplit(" ", 1)
            pdf.drawRightString(200, y, label)
            pdf.drawRightString(width - 15, y, amount)
        else:
            pdf.drawCentredString(width / 2, y, line)
        y -= 10

    pdf.save()
    return buffer.getvalue()
