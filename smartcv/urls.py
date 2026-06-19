from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("payments/", include("payments.urls")),
    path("", include("ai.urls")),
    path("", include("resumes.urls")),
    path("favicon.ico", RedirectView.as_view(url="/static/favicon.ico", permanent=True)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
