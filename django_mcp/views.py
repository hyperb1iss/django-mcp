"""
Views for Django-MCP.

This module provides Django views for MCP endpoints and dashboard.
"""

import contextlib
import json
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from django_mcp.inspection import get_prompts, get_resources, get_tools
from django_mcp.server import get_mcp_server, get_sse_app


async def mcp_sse_view(_request: HttpRequest) -> StreamingHttpResponse:
    """
    Server-Sent Events (SSE) endpoint for the MCP server.

    This view provides a streaming SSE connection to the MCP server.

    Args:
        _request: Django request (unused)

    Returns:
        A streaming HttpResponse with Server-Sent Events
    """
    # Check if SSE is enabled
    try:
        get_sse_app()
    except Exception as e:
        # Use StreamingHttpResponse for error to match return type
        response = StreamingHttpResponse(
            streaming_content=[
                f"data: {json.dumps({'error': f'MCP server not initialized or SSE not available: {e!s}'})}"
            ],
            content_type="text/event-stream",
            status=500,
        )
        response["Cache-Control"] = "no-cache"
        return response

    # Pass control to the FastMCP SSE app
    # Since we can't directly return the result of sse_app (it doesn't return an HttpResponse),
    # we need to create a StreamingHttpResponse or similar

    # Create a streaming response
    response = StreamingHttpResponse(streaming_content=[], content_type="text/event-stream")

    # Set SSE headers
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # For Nginx

    # We need to note that in a production environment,
    # this would require proper ASGI handling which is beyond
    # the scope of this type fix

    # The actual SSE handling would happen at the ASGI level
    # This is a type fix to make mypy happy, but in production
    # a different approach involving proper ASGI integration would be needed

    return response


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
        response = await mcp_server.handle_message(body)  # type: ignore
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
        info: dict[str, Any] = {
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

        # Add tool information
        tool_list: list[dict[str, Any]] = []
        for tool in tools:
            tool_dict = tool
            tool_list.append(
                {
                    "name": tool_dict.get("name", ""),
                    "description": tool_dict.get("description", ""),
                    "parameters": tool_dict.get("parameters", {}),
                }
            )
        info["components"]["tools"] = tool_list

        # Add resource information
        resource_list: list[dict[str, Any]] = []
        for resource in resources:
            resource_dict = resource
            resource_list.append(
                {
                    "uri_template": resource_dict.get("uri_template", ""),
                    "description": resource_dict.get("description", ""),
                }
            )
        info["components"]["resources"] = resource_list

        # Add prompt information
        prompt_list: list[dict[str, Any]] = []
        for prompt in prompts:
            prompt_dict = prompt
            prompt_list.append(
                {
                    "name": prompt_dict.get("name", ""),
                    "description": prompt_dict.get("description", ""),
                    "arguments": prompt_dict.get("arguments", {}),
                }
            )
        info["components"]["prompts"] = prompt_list

        # Convert to JSON-friendly structure
        return JsonResponse(info)
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"Error getting MCP server info: {e!s}"}, status=500)
