"""Корневая маршрутизация проекта: admin, аутентификация и приложение cinema."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Встроенные представления Django: /accounts/login/, /accounts/logout/ и др.
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("cinema.urls", namespace="cinema")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Обработчики ошибок (шаблоны 404.html / 500.html в каталоге cinema/templates).
handler404 = "cinema.views.custom_404"
handler500 = "cinema.views.custom_500"
