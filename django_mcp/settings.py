"""
Settings for Django-MCP.

This module defines default settings and validates MCP-specific settings.
"""

from typing import Any

from django.conf import settings

# Default settings
DEFAULTS: dict[str, Any] = {
    # Core MCP server settings
    "DJANGO_MCP_SERVER_NAME": None,  # Default to project name (set in apps.py)
    "DJANGO_MCP_URL_PREFIX": "mcp",  # URL prefix for MCP endpoints
    "DJANGO_MCP_INSTRUCTIONS": None,  # Instructions for MCP clients
    "DJANGO_MCP_DEPENDENCIES": [],  # Dependencies for MCP server
    # Auto-discovery settings
    "DJANGO_MCP_AUTO_DISCOVER": True,  # Auto-discover MCP components
    "DJANGO_MCP_EXPOSE_MODELS": True,  # Auto-expose Django models
    "DJANGO_MCP_EXPOSE_ADMIN": True,  # Auto-expose Django admin
    "DJANGO_MCP_EXPOSE_DRF": True,  # Auto-expose DRF ViewSets
    # Test settings
    "DJANGO_MCP_SKIP_IN_TESTS": False,  # Skip MCP initialization in tests
    # Security settings
    "DJANGO_MCP_ALLOWED_ORIGINS": [],  # CORS allowed origins for SSE endpoint
    # Advanced settings
    "DJANGO_MCP_SSE_KEEPALIVE": 15,  # SSE keepalive interval in seconds
    "DJANGO_MCP_SSE_RETRY": 3000,  # SSE client retry interval in milliseconds
}


# Required settings (with default values)
# This automatically sets the settings if they're not already defined
for key, default_value in DEFAULTS.items():
    if not hasattr(settings, key):
        setattr(settings, key, default_value)


def get_mcp_setting(name: str, default: Any = None) -> Any:
    """
    Get a Django-MCP setting or default.

    First checks Django's settings, then falls back to MCP defaults,
    and finally to the provided default value.

    Args:
        name: The setting name
        default: Default value if setting not found

    Returns:
        Setting value or default
    """
    # Check Django settings first
    if hasattr(settings, name):
        return getattr(settings, name)

    # Check MCP defaults
    if name in DEFAULTS:
        return DEFAULTS[name]

    # Fall back to provided default
    return default


def validate_settings() -> list[str]:
    """
    Validate Django-MCP settings.

    This checks for any issues in the MCP-specific settings.

    Returns:
        List of warning messages if any
    """
    warnings: list[str] = []

    # Check server name (not critical, will use default)
    server_name = get_mcp_setting("DJANGO_MCP_SERVER_NAME")
    if server_name and not isinstance(server_name, str):
        warnings.append("DJANGO_MCP_SERVER_NAME should be a string")

    # Check URL prefix
    url_prefix = get_mcp_setting("DJANGO_MCP_URL_PREFIX")
    if not url_prefix:
        warnings.append("DJANGO_MCP_URL_PREFIX should not be empty")
    elif not isinstance(url_prefix, str):
        warnings.append("DJANGO_MCP_URL_PREFIX should be a string")

    # Check dependencies
    dependencies = get_mcp_setting("DJANGO_MCP_DEPENDENCIES")
    if dependencies and not isinstance(dependencies, list | tuple):
        warnings.append("DJANGO_MCP_DEPENDENCIES should be a list or tuple")

    # Check allowed origins
    allowed_origins = get_mcp_setting("DJANGO_MCP_ALLOWED_ORIGINS")
    if allowed_origins and not isinstance(allowed_origins, list | tuple):
        warnings.append("DJANGO_MCP_ALLOWED_ORIGINS should be a list or tuple")

    # Check SSE settings
    sse_keepalive = get_mcp_setting("DJANGO_MCP_SSE_KEEPALIVE")
    if not isinstance(sse_keepalive, int) or sse_keepalive <= 0:
        warnings.append("DJANGO_MCP_SSE_KEEPALIVE should be a positive integer")

    sse_retry = get_mcp_setting("DJANGO_MCP_SSE_RETRY")
    if not isinstance(sse_retry, int) or sse_retry <= 0:
        warnings.append("DJANGO_MCP_SSE_RETRY should be a positive integer")

    return warnings
