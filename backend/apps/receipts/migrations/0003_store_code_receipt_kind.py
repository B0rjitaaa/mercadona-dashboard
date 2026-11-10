from django.db import migrations, models


def fill_store_codes(apps, schema_editor):
    """Derive each store's code from its receipts and merge stores sharing a code."""
    Store = apps.get_model("receipts", "Store")
    Receipt = apps.get_model("receipts", "Receipt")

    kept: dict[str, int] = {}
    for store in Store.objects.order_by("pk"):
        invoice = (
            Receipt.objects.filter(store=store)
            .exclude(invoice_number=None)
            .values_list("invoice_number", flat=True)
            .first()
        )
        code = invoice.split("-")[0] if invoice and "-" in invoice else f"unknown-{store.pk}"
        if code in kept:
            Receipt.objects.filter(store=store).update(store_id=kept[code])
            store.delete()
        else:
            store.code = code
            store.save(update_fields=["code"])
            kept[code] = store.pk


class Migration(migrations.Migration):
    dependencies = [("receipts", "0002_gmail_message_id_not_unique")]

    operations = [
        migrations.RemoveConstraint(model_name="store", name="unique_store_location"),
        migrations.AddField(
            model_name="store",
            name="code",
            field=models.CharField(default="", max_length=10),
            preserve_default=False,
        ),
        migrations.RunPython(fill_store_codes, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="store",
            constraint=models.UniqueConstraint(fields=("chain", "code"), name="unique_store_code"),
        ),
        migrations.AddField(
            model_name="receipt",
            name="kind",
            field=models.CharField(
                choices=[("sale", "Sale"), ("return", "Return")], default="sale", max_length=10
            ),
        ),
        migrations.AddField(
            model_name="receipt",
            name="original_invoice_number",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AlterField(
            model_name="receiptline",
            name="line_type",
            field=models.CharField(
                choices=[
                    ("product", "Product"),
                    ("discount", "Discount"),
                    ("return", "Return"),
                    ("other", "Other"),
                ],
                default="product",
                max_length=20,
            ),
        ),
    ]
