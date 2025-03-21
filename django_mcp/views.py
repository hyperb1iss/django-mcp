"""
Views for Django-MCP.

This module provides Django views for MCP endpoints and dashboard.
"""

import contextlib
import json

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from django_mcp.api_inspection import get_request_receive, get_request_send
from django_mcp.inspection import get_prompts, get_resources, get_tools
from django_mcp.server import get_mcp_server, get_sse_app


async def mcp_sse_view(request: HttpRequest) -> HttpRequest:
    """
    Server-Sent Events (SSE) endpoint for the MCP server.

    This view provides a streaming SSE connection to the MCP server.

    Args:
        request: Django request

    Returns:
        A streaming HttpResponse with Server-Sent Events
    """
    # Check if SSE is enabled
    try:
        sse_app = get_sse_app()
    except Exception as e:
        return JsonResponse({"error": f"MCP server not initialized or SSE not available: {e!s}"}, status=500)

    # Pass control to the FastMCP SSE app
    return await sse_app(request.scope, get_request_receive(request), get_request_send(request))


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

    # Get MCP server (or None if not initialized)
    mcp_server = None
    with contextlib.suppress(Exception):
        mcp_server = get_mcp_server()

    # Get MCP components
    tools = []
    resources = []
    prompts = []

    if mcp_server:
        # Get components using inspection module instead of direct access
        tools = get_tools()
        resources = get_resources()
        prompts = get_prompts()

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


@require_http_methods(["GET"])
def mcp_health_view(_request: HttpRequest) -> JsonResponse:
    """
    Health check endpoint for the MCP server.

    Args:
        _request: Django request (unused)

    Returns:
        JsonResponse with health check result
    """
    try:
        mcp_server = get_mcp_server()
        if not mcp_server:
            return JsonResponse({"status": "error", "message": "MCP server not initialized"}, status=500)

        return JsonResponse(
            {
                "status": "ok",
                "message": "MCP server is healthy",
                "server_name": mcp_server.name,
                "server_version": getattr(mcp_server, "version", "unknown"),
            }
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"Error accessing MCP server: {e!s}"}, status=500)


@require_http_methods(["GET"])
def mcp_info_view(_request: HttpRequest) -> JsonResponse:
    """
    Information endpoint for the MCP server.

    Args:
        _request: Django request (unused)

    Returns:
        JsonResponse with server information
    """
    try:
        mcp_server = get_mcp_server()
        if not mcp_server:
            return JsonResponse({"status": "error", "message": "MCP server not initialized"}, status=500)

        # Get server info
        info = {
            "name": mcp_server.name,
            "version": getattr(mcp_server, "version", "unknown"),
            "components": {
                "tools": [],
                "resources": [],
                "prompts": [],
            },
        }

        # Get component counts
        # Use the inspection module instead of accessing private members
        tools = get_tools()
        resources = get_resources()
        prompts = get_prompts()

        # Check server version
        info["components"]["tools"] = [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in tools
        ]

        info["components"]["resources"] = [
            {
                "uri_template": resource.uri_template,
                "description": resource.description,
            }
            for resource in resources
        ]

        info["components"]["prompts"] = [
            {
                "name": prompt.name,
                "description": prompt.description,
                "arguments": prompt.arguments,
            }
            for prompt in prompts
        ]

        # Convert to JSON-friendly structure
        return JsonResponse(info)
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"Error getting MCP server info: {e!s}"}, status=500)
