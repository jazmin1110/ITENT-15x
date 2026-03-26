from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('jobs/', include('jobs.urls')),
    path('chat/', include('chat.urls')),
    path('dashboard/', dashboard, name='dashboard'),
    path('', dashboard, name='home'),
]

# User uploads (avatars, verification docs). Needed whenever DEBUG is False (e.g. Render);
# use cloud storage + django-storages if you need durable media across deploys.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
