from django.contrib import admin
from django.urls import path, include
from accounts.views import dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('jobs/', include('jobs.urls')),
    path('chat/', include('chat.urls')),
    path('dashboard/', dashboard, name='dashboard'),
    path('', dashboard, name='home'),
]
