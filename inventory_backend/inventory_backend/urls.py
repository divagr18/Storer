from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from products.views import ProductViewSet
from transactions.views import TransactionViewSet
from suppliers.views import SupplierViewSet
from users.views import UserViewSet
import ai_assistant.urls
from inventory_logs.views import InventoryViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from products.views import get_demand_forecast, get_arima_demand_forecast, get_prophet_backtesting, get_arima_backtesting, get_dashboard_metrics, get_sales_profit_trend
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
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
    path('api/products/<str:product_sku>/forecast/prophet/<int:horizon>/', get_demand_forecast, name='product_forecast'), # Prophet endpoint -  URL updated to be more descriptive # URL updated
    path('api/products/<str:product_sku>/forecast/arima/<int:horizon>/', get_arima_demand_forecast, name='product_arima_forecast'), # New ARIMA endpoint # New ARIMA endpoint
    path('api/products/<str:product_sku>/backtest/prophet/<int:validation_horizon>/', get_prophet_backtesting, name='product_prophet_backtest'),
    path('api/products/<str:product_sku>/backtest/arima/<int:validation_horizon>/', get_arima_backtesting, name='product_arima_backtest'),
    path('api/metrics/', get_dashboard_metrics, name='dashboard_metrics'),
    path('api/sales_profit_trend/', get_sales_profit_trend, name='sales_profit_trend'),
    path('api/ai/', include('ai_assistant.urls')),  # New URL
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'), # Serves the schema file (e.g., schema.yaml/.json)
    # Optional UI:
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
]
