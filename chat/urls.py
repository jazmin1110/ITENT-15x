from django.urls import path
from . import views

urlpatterns = [
    path('', views.conversations, name='conversations'),
    path('<int:conversation_id>/', views.chat, name='chat'),
]
