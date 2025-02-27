from rest_framework import serializers
from .models import Product

class ProductSerializer(serializers.ModelSerializer):
    reorder_point = serializers.IntegerField(read_only=True)
    class Meta:
        model = Product
        fields = '__all__'