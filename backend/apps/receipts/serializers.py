from rest_framework import serializers

from .models import Receipt, ReceiptLine, Store


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["id", "chain", "code", "address", "postal_code", "city", "phone"]


class ReceiptLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiptLine
        fields = [
            "id",
            "position",
            "line_type",
            "description",
            "quantity",
            "unit",
            "unit_price",
            "amount",
        ]


class ReceiptListSerializer(serializers.ModelSerializer):
    store = StoreSerializer(read_only=True)
    line_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Receipt
        fields = [
            "id",
            "invoice_number",
            "kind",
            "issued_at",
            "store",
            "total",
            "payment_method",
            "status",
            "source",
            "line_count",
            "created_at",
        ]


class ReceiptDetailSerializer(ReceiptListSerializer):
    lines = ReceiptLineSerializer(many=True, read_only=True)

    class Meta(ReceiptListSerializer.Meta):
        fields = ReceiptListSerializer.Meta.fields + [
            "operation_number",
            "original_invoice_number",
            "vat_breakdown",
            "warnings",
            "error_message",
            "parsed_at",
            "pdf",
            "lines",
        ]


class ReceiptUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, file):
        if not file.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("Only PDF files are accepted.")
        head = file.read(5)
        file.seek(0)
        if head != b"%PDF-":
            raise serializers.ValidationError("File is not a valid PDF.")
        return file
