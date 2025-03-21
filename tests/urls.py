from django.urls import include, path

urlpatterns = [
    path("mcp/", include("django_mcp.urls")),
]
