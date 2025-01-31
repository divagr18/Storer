from rest_framework import serializers
from .models import InventoryLog

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryLog
        fields = '__all__'