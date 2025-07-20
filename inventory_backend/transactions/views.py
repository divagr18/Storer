from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Transaction
from .serializers import TransactionSerializer
from products.models import Product
from inventory_logs.models import InventoryLog


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

    def perform_create(self, serializer):
        """Creates a new transaction, updates the related product's stock level accordingly, and logs the inventory change.

        Args:
            serializer: A serializer instance containing validated transaction data to be saved.

        Returns:
            None

        This method is typically called during the creation of a transaction record. It adjusts the product's stock level by decreasing it for sales and increasing it for purchases, then saves the updated product state. An InventoryLog entry is created to record the stock change and its reason."""
        transaction = serializer.save()
        product = transaction.product
        if transaction.transaction_type == "sale":
            product.stock_level -= transaction.quantity
            reason = f"Sale of {transaction.quantity} units"
        elif transaction.transaction_type == "purchase":
            product.stock_level += transaction.quantity
            reason = f"Purchase of {transaction.quantity} units"
        product.save()
        InventoryLog.objects.create(
            product=product,
            stock_change=transaction.quantity
            if transaction.transaction_type == "purchase"
            else -transaction.quantity,
            reason=reason,
        )
