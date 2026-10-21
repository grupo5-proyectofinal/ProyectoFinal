from django.conf import settings
from django.contrib import admin
from django.http import Http404, HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve


def spa(request, _path=""):
    """Rutas del SPA (client-side routing): devuelve index.html."""
    index = settings.FRONTEND_BUILD / "index.html"
    if not index.is_file():
        raise Http404
    return HttpResponse(index.read_text(encoding="utf-8"), content_type="text/html")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('users.urls')),
    path('api/v1/', include('pools.urls')),
    path('api/v1/', include('notificaciones.urls')),
    # Media subida por usuarios (en producción requiere disco persistente).
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^(?!api/|admin/|media/|static/)(?P<_path>.*)$', spa),
]
