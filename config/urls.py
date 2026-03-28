from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="auth/login.html"), name="login"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("recipes.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
