"""
Decorators for exposing Django functionality via MCP.

This module provides decorators for exposing Django functions, models,
views, and other components as MCP tools, resources, and prompts.
"""

from collections.abc import Callable
from typing import Any, TypeVar, cast

from django.db.models import Model

from django_mcp.server import get_mcp_server

# Type variables for better type hinting
F = TypeVar("F", bound=Callable[..., Any])
ModelType = TypeVar("ModelType", bound=type[Model])


def mcp_tool(description: str | None = None, name: str | None = None, **kwargs: Any) -> Callable[[F], F]:
    """
    Decorator to expose a function as an MCP tool.

    Args:
        description: Optional description of the tool
        name: Optional custom name for the tool
        **kwargs: Additional kwargs for FastMCP.tool

    Returns:
        Decorated function that's registered as an MCP tool
    """

    def decorator(func: F) -> F:
        # Try to get MCP server, but don't fail if not initialized yet
        try:
            mcp_server = get_mcp_server()

            # Register with FastMCP
            return cast(F, mcp_server.tool(description=description or func.__doc__, name=name, **kwargs)(func))
        except Exception:
            # Return the original function if server isn't ready
            # This happens during app initialization
            return func

    return decorator


def mcp_resource(uri_template: str, description: str | None = None, **kwargs: Any) -> Callable[[F], F]:
    """
    Decorator to expose a function as an MCP resource.

    Args:
        uri_template: URI template for the resource
        description: Optional description of the resource
        **kwargs: Additional kwargs for FastMCP.resource

    Returns:
        Decorated function that's registered as an MCP resource
    """

    def decorator(func: F) -> F:
        # Try to get MCP server, but don't fail if not initialized yet
        try:
            mcp_server = get_mcp_server()

            # Register with FastMCP
            return cast(F, mcp_server.resource(uri_template, description=description or func.__doc__, **kwargs)(func))
        except Exception:
            # Return the original function if server isn't ready
            return func

    return decorator


def mcp_prompt(name: str | None = None, description: str | None = None, **kwargs: Any) -> Callable[[F], F]:
    """
    Decorator to expose a function as an MCP prompt.

    Args:
        name: Optional name for the prompt
        description: Optional description of the prompt
        **kwargs: Additional kwargs for FastMCP.prompt

    Returns:
        Decorated function that's registered as an MCP prompt
    """

    def decorator(func: F) -> F:
        # Try to get MCP server, but don't fail if not initialized yet
        try:
            mcp_server = get_mcp_server()

            # Register with FastMCP
            return cast(F, mcp_server.prompt(name=name, description=description or func.__doc__, **kwargs)(func))
        except Exception:
            # Return the original function if server isn't ready
            return func

    return decorator


def mcp_model_tool(
    model: ModelType,
    prefix: str | None = None,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    **kwargs: Any,
) -> Callable[..., Any]:
    """
    Decorator to expose a Django model as MCP tools.
    This will create CRUD tools for the model.

    Args:
        model: Django model class
        prefix: Optional prefix for tool names
        include: Optional list of tools to include (get, list, search, create)
        exclude: Optional list of tools to exclude
        **kwargs: Additional kwargs for tool registration

    Returns:
        A decorator function that registers model tools
    """
    from django_mcp.model_tools import register_model_tools

    def decorator(func: Callable[..., Any] | None = None) -> Any:
        # If no function is provided, register default tools
        if func is None:
            register_model_tools(model, prefix, include, exclude, **kwargs)
            return lambda: None

        # Otherwise, register and return the function
        register_model_tools(model, prefix, include, exclude, **kwargs)
        return func

    return decorator


def mcp_model_resource(
    model: ModelType, lookup: str = "pk", fields: list[str] | None = None, **kwargs: Any
) -> Callable[..., Any]:
    """
    Decorator to expose a Django model as an MCP resource.

    Args:
        model: Django model class
        lookup: Field to use for lookup (default: 'pk')
        fields: Optional list of fields to include
        **kwargs: Additional kwargs for resource registration

    Returns:
        A decorator function that registers model resource
    """
    from django_mcp.model_tools import register_model_resource

    def decorator(func: Callable[..., Any] | None = None) -> Any:
        # If no function is provided, register default resource
        if func is None:
            register_model_resource(model, lookup, fields, **kwargs)
            return lambda: None

        # Otherwise, register and return the function
        register_model_resource(model, lookup, fields, **kwargs)
        return func

    return decorator
