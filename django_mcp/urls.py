"""
URL patterns for Django-MCP.

This module defines the URL patterns for MCP endpoints and dashboard.
"""

from django.conf import settings
from django.urls import path

from django_mcp import views

app_name = "django_mcp"

# Get MCP URL prefix from settings (default to /mcp)
mcp_prefix = getattr(settings, "DJANGO_MCP_URL_PREFIX", "mcp")

urlpatterns = [
    # SSE endpoint for MCP server
    path(f"{mcp_prefix}/", views.mcp_sse_view, name="mcp_sse"),
    # HTTP message endpoint (for testing/debugging)
    path(f"{mcp_prefix}/message/", views.mcp_message_view, name="mcp_message"),
    # Dashboard
    path(f"{mcp_prefix}/dashboard/", views.mcp_dashboard, name="mcp_dashboard"),
]
