from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import InventoryLog
from .serializers import InventorySerializer
from products.models import Product

class InventoryViewSet(viewsets.ModelViewSet):
    queryset = InventoryLog.objects.all()
    serializer_class = InventorySerializer

    def create(self, request, *args, **kwargs):
        # Validate request data
        product_id = request.data.get('product')
        stock_change = int(request.data.get('stock_change', 0))
        reason = request.data.get('reason', '')

        if not product_id:
            return Response({"error": "Product ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        # Update product stock
        product.stock_level += stock_change
        product.save()

        # Log inventory change
        inventory_log = InventoryLog.objects.create(
            product=product,
            stock_change=stock_change,
            reason=reason
        )
        serializer = self.get_serializer(inventory_log)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
