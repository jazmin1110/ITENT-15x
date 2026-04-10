from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from accounts.views import dashboard, home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('jobs/', include('jobs.urls')),
    path('chat/', include('chat.urls')),
    path('dashboard/', dashboard, name='dashboard'),
    path('', home, name='home'),
]

# User uploads (avatars, verification docs). django.conf.urls.static.static()
# only wires URLs when DEBUG is True; production (e.g. Render with DEBUG=False)
# needs an explicit route. Files on free web tiers are still ephemeral across
# deploys—see README for durable storage options.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(
            r'^media/(?P<path>.*)$',
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]
