from django.db import migrations, models


def nulls_to_empty(apps, schema_editor):
    Receipt = apps.get_model("receipts", "Receipt")
    Receipt.objects.filter(gmail_message_id__isnull=True).update(gmail_message_id="")


class Migration(migrations.Migration):
    """One email may carry several PDFs, so gmail_message_id is no longer unique."""

    dependencies = [("receipts", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="receipt",
            name="gmail_message_id",
            field=models.CharField(blank=True, max_length=64, null=True, db_index=True),
        ),
        migrations.RunPython(nulls_to_empty, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="receipt",
            name="gmail_message_id",
            field=models.CharField(blank=True, default="", max_length=64, db_index=True),
        ),
    ]
