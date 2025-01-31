from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import InventoryLog
from .serializers import InventorySerializer

class InventoryViewSet(viewsets.ModelViewSet):
    queryset = InventoryLog.objects.all()
    serializer_class = InventorySerializer