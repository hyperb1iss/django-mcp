"""
ASGI integration for Django-MCP.

This module provides functions to integrate MCP with Django's ASGI application.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from django.conf import settings
from django.core.asgi import get_asgi_application as django_get_asgi_application


def get_asgi_application() -> Callable[
    [dict[str, Any], Callable[[], Awaitable[dict[str, Any]]], Callable[[dict[str, Any]], Awaitable[None]]],
    Awaitable[None],
]:
    """
    Get the ASGI application.

    This wraps Django's get_asgi_application to add MCP support.

    Returns:
        The ASGI application
    """
    # Get Django's ASGI application
    django_application = django_get_asgi_application()

    # Setting for the MCP server
    # Get this early to avoid circular imports
    mcp_prefix = getattr(settings, "DJANGO_MCP_URL_PREFIX", "mcp")

    # Get MCP's SSE application (lazy-loaded to avoid circular imports)
    from django_mcp.server import get_sse_app

    mcp_sse_app = get_sse_app()

    # Define the ASGI application
    async def application(
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """
        ASGI application that routes to either Django or MCP.

        Args:
            scope: The ASGI scope
            receive: The ASGI receive function
            send: The ASGI send function
        """
        # Check if this is an MCP request
        path = scope.get("path", "")

        if path.startswith(f"/{mcp_prefix}"):
            # Route to MCP SSE app
            await mcp_sse_app(scope, receive, send)
        else:
            # Route to Django
            await django_application(scope, receive, send)  # type: ignore

    return application


def mount_mcp_in_starlette_app(app: Any) -> Any:
    """
    Mount MCP in a Starlette app.

    This is useful for manually mounting MCP in a Starlette app.

    Args:
        app: The Starlette app to mount MCP in

    Returns:
        The modified Starlette app
    """
    from starlette.routing import Mount

    from django_mcp.server import get_sse_app

    # Get MCP URL prefix from settings
    mcp_prefix = getattr(settings, "DJANGO_MCP_URL_PREFIX", "mcp")

    # Get MCP's SSE application
    sse_app = get_sse_app()

    # Mount the SSE app
    app.routes.append(Mount(f"/{mcp_prefix}", app=sse_app))  # type: ignore

    return app
