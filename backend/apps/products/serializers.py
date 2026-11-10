from rest_framework import serializers

from .models import Product, ProductAlias


class ProductSummarySerializer(serializers.ModelSerializer):
    category_path = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "mercadona_id",
            "name",
            "packaging",
            "thumbnail",
            "share_url",
            "unit_price",
            "bulk_price",
            "reference_price",
            "reference_format",
            "is_active",
            "is_manual",
            "category_path",
        ]

    def get_category_path(self, product: Product) -> list[str]:
        path, node = [], product.category
        while node is not None:
            path.insert(0, node.name)
            node = node.parent
        return path


class AliasSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAlias
        fields = ["description", "source", "score", "created_at"]


class LinkSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=200)
    product_id = serializers.IntegerField()


class ManualProductSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=200)
    name = serializers.CharField(max_length=300, allow_blank=True, required=False, default="")


class DescriptionSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=200)
