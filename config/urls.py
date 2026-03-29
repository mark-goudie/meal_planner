from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.urls import include, path
from django.views.decorators.cache import never_cache


@never_cache
def service_worker(request):
    """Serve service worker from root scope."""
    sw_path = settings.BASE_DIR / "recipes" / "static" / "recipes" / "sw.js"
    with open(sw_path) as f:
        return HttpResponse(f.read(), content_type="application/javascript", headers={"Service-Worker-Allowed": "/"})


urlpatterns = [
    path("sw.js", service_worker, name="service_worker"),
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="auth/login.html"), name="login"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("recipes.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
