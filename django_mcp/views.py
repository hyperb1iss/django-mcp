"""
Views for Django-MCP.

This module provides Django views for MCP endpoints and dashboard.
"""

import contextlib
import json

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


async def mcp_sse_view(request: HttpRequest) -> HttpResponse:
    """
    Handle SSE connections for MCP.

    This view is an ASGI endpoint for the MCP SSE server.

    Args:
        request: Django HTTP request

    Returns:
        Django HTTP response
    """
    from django_mcp.server import get_sse_app

    try:
        sse_app = get_sse_app()
    except Exception:
        return HttpResponse("MCP server not initialized", status=500)

    # Pass control to the FastMCP SSE app
    return await sse_app(request.scope, request._receive, request._send)


@csrf_exempt
@require_http_methods(["POST"])
async def mcp_message_view(request: HttpRequest) -> JsonResponse:
    """
    Handle MCP messages via HTTP POST.

    This is primarily useful for testing and debugging.

    Args:
        request: Django HTTP request

    Returns:
        JSON response with MCP result
    """
    from django_mcp.server import get_mcp_server

    try:
        mcp_server = get_mcp_server()
    except Exception:
        return JsonResponse({"error": "MCP server not initialized"}, status=500)

    # Get request body
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    # Process the message
    try:
        response = await mcp_server.handle_message(body)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(response)


def mcp_dashboard(request: HttpRequest) -> HttpResponse:
    """
    Render the MCP dashboard.

    This view shows all registered MCP components and server status.

    Args:
        request: Django HTTP request

    Returns:
        HTML response with MCP dashboard
    """
    from django.shortcuts import render

    from django_mcp.server import get_mcp_server

    # Get MCP server (or None if not initialized)
    mcp_server = None
    with contextlib.suppress(Exception):
        mcp_server = get_mcp_server()

    # Get MCP components
    tools = []
    resources = []
    prompts = []

    if mcp_server:
        # Access private managers via protected attributes (this is safe as we know the implementation)
        # In a normal application we'd use public APIs, but FastMCP doesn't expose these as public
        tools = list(mcp_server._tool_manager.tools.values())
        resources = list(mcp_server._resource_manager.resources.values())
        prompts = list(mcp_server._prompt_manager.prompts.values())

    # Check server version
    server_version = getattr(mcp_server, "version", "Unknown") if mcp_server else "Not initialized"

    # Get settings
    from django.conf import settings

    mcp_settings = {
        "DJANGO_MCP_SERVER_NAME": getattr(settings, "DJANGO_MCP_SERVER_NAME", None),
        "DJANGO_MCP_URL_PREFIX": getattr(settings, "DJANGO_MCP_URL_PREFIX", "mcp"),
        "DJANGO_MCP_INSTRUCTIONS": getattr(settings, "DJANGO_MCP_INSTRUCTIONS", None),
        "DJANGO_MCP_AUTO_DISCOVER": getattr(settings, "DJANGO_MCP_AUTO_DISCOVER", True),
        "DJANGO_MCP_EXPOSE_MODELS": getattr(settings, "DJANGO_MCP_EXPOSE_MODELS", True),
        "DJANGO_MCP_EXPOSE_ADMIN": getattr(settings, "DJANGO_MCP_EXPOSE_ADMIN", True),
        "DJANGO_MCP_EXPOSE_DRF": getattr(settings, "DJANGO_MCP_EXPOSE_DRF", True),
    }

    # Render dashboard template
    return render(
        request,
        "django_mcp/dashboard.html",
        {
            "server": mcp_server,
            "server_version": server_version,
            "tools": tools,
            "resources": resources,
            "prompts": prompts,
            "settings": mcp_settings,
        },
    )
