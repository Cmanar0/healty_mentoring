from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("dashboard/", include("general.urls", namespace="general")),
    path("", include("web.urls", namespace="web")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
