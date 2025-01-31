from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from products.views import ProductViewSet
from transactions.views import TransactionViewSet
from suppliers.views import SupplierViewSet
from users.views import UserViewSet
from inventory_logs.views import InventoryViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# Initialize the router for REST API routes
router = routers.DefaultRouter()

# Registering viewsets for API routes
router.register(r'products', ProductViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'users', UserViewSet)
router.register(r'inventory_logs',InventoryViewSet)

# URL patterns
urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),
    
    # API root with router endpoints
    path('api/', include(router.urls)),
    
    # JWT authentication routes
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
