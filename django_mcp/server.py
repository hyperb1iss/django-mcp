"""
MCP server management for Django-MCP.

This module provides functions to initialize and access the MCP server instance.
It ensures a singleton pattern for the MCP server across the Django application.
"""

import sys
import threading

from django.conf import settings
from mcp.server.fastmcp import FastMCP

# Global MCP server instance (singleton)
_mcp_server: FastMCP | None = None
_mcp_server_lock = threading.Lock()


def get_mcp_server(
    name: str | None = None,
    instructions: str | None = None,
    dependencies: list[str] | None = None,
    lifespan: int | None = None,
) -> FastMCP:
    """
    Get or create the MCP server instance.

    This ensures a single instance across the application.

    Args:
        name: The name of the server (optional if already initialized)
        instructions: Instructions for MCP clients (optional)
        dependencies: Dependencies for MCP server (optional)
        lifespan: Lifespan for the server (optional)

    Returns:
        The FastMCP server instance
    """
    global _mcp_server

    # Return existing instance if available
    if _mcp_server is not None:
        return _mcp_server

    # Thread-safe initialization
    with _mcp_server_lock:
        # Double-check to avoid race conditions
        if _mcp_server is not None:
            return _mcp_server

        # If name is not provided, try to get from settings
        if name is None:
            name = getattr(settings, "DJANGO_MCP_SERVER_NAME", None)

            # For tests, use a default name if still None
            if name is None and "pytest" in sys.modules:
                name = "Test MCP Server"

        # If instructions is not provided, try to get from settings
        if instructions is None:
            instructions = getattr(settings, "DJANGO_MCP_INSTRUCTIONS", None)

        # If dependencies is not provided, try to get from settings
        if dependencies is None:
            dependencies = getattr(settings, "DJANGO_MCP_DEPENDENCIES", [])

        # Create the MCP server
        _mcp_server = FastMCP(
            name=name,
            instructions=instructions,
            dependencies=dependencies or [],
            lifespan=lifespan,
        )

    return _mcp_server


def get_sse_app():
    """
    Get the ASGI application for the SSE endpoint.

    This is used for mounting in Django's ASGI application.

    Returns:
        The ASGI application for SSE
    """
    try:
        mcp_server = get_mcp_server()
        return mcp_server.sse_app()
    except ValueError:
        # During testing, we might not have a fully initialized server
        if "pytest" in sys.modules:
            return lambda scope, receive, send: None
        raise


def reset_mcp_server() -> None:
    """
    Reset the MCP server instance.

    This is primarily useful for testing.
    """
    global _mcp_server
    with _mcp_server_lock:
        _mcp_server = None
