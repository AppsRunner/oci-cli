from django.contrib import admin
from django.urls import include, path

from apps.core import views as core_views

urlpatterns = [
    path("", core_views.index, name="index"),
    path("accounts/", include("apps.accounts.urls")),
    path("admin/", admin.site.urls),
]
