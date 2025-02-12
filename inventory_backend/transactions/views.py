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
        transaction = serializer.save()
        product = transaction.product

        # Update stock level based on transaction type
        if transaction.transaction_type == 'sale':
            product.stock_level -= transaction.quantity
            reason = f"Sale of {transaction.quantity} units"
        elif transaction.transaction_type == 'purchase':
            product.stock_level += transaction.quantity
            reason = f"Purchase of {transaction.quantity} units"
        
        # Save product changes
        product.save()

        # Create inventory log
        InventoryLog.objects.create(
            product=product,
            stock_change=transaction.quantity if transaction.transaction_type == 'purchase' else -transaction.quantity,
            reason=reason
        )
