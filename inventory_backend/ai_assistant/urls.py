from django.urls import path
from .views import ChatAPIView

app_name = 'ai_assistant' # Optional: Define an app namespace

urlpatterns = [
    # Define the path for the ChatAPIView
    path('chat/', ChatAPIView.as_view(), name='ai_chat'),
    # You can add more AI-related URLs here later
]