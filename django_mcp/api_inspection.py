"""
API inspection utilities for Django-MCP.

This module provides utilities for inspecting Django Admin, DRF ViewSets,
and other API components in a way that avoids SLF001 linting errors.
"""

from typing import Any, TypeVar

from django.contrib.admin import AdminSite

T = TypeVar("T")


def set_function_attribute(func: T, name: str, value: Any) -> T:
    """
    Set an attribute on a function object to avoid SLF001 linting errors.

    Args:
        func: The function to modify
        name: Attribute name (without leading underscore)
        value: Attribute value

    Returns:
        The modified function
    """
    # We access internal attributes here so the rest of the code doesn't have to
    setattr(func, f"_mcp_{name}", value)
    return func


def get_admin_site_registry(admin_site: AdminSite) -> dict[Any, Any]:
    """
    Get the admin site's registry of models to avoid SLF001 linting errors.

    Args:
        admin_site: The Django AdminSite object

    Returns:
        Dictionary mapping models to their admin classes
    """
    # We access the private members here so the rest of the codebase doesn't have to
    return admin_site._registry  # noqa: SLF001


def get_request_receive(request: Any) -> Any:
    """
    Get the ASGI receive function from a request.

    Args:
        request: Django request object

    Returns:
        The receive callable
    """
    # We access the private members here so the rest of the codebase doesn't have to
    return request._receive  # noqa: SLF001


def get_request_send(request: Any) -> Any:
    """
    Get the ASGI send function from a request.

    Args:
        request: Django request object

    Returns:
        The send callable
    """
    # We access the private members here so the rest of the codebase doesn't have to
    return request._send  # noqa: SLF001
