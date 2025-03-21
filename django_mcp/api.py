"""
High-level API for django-mcp.

This module provides a simplified API for common MCP operations.
"""

import asyncio
from collections.abc import Callable
from functools import wraps
import inspect
import logging
from typing import Any, TypeVar

from django_mcp.api_inspection import set_function_attribute
from django_mcp.context import Context
from django_mcp.server import get_mcp_server

# Type variables for better type hinting
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

# Logger for MCP API
logger = logging.getLogger("django_mcp.api")


def tool(name: str | None = None, description: str | None = None) -> Callable[[F], F]:
    """
    Register a tool with the MCP server.

    This decorator can be applied to any function to expose it as an MCP tool.

    Args:
        name: Optional name for the tool (defaults to function name)
        description: Optional description for the tool (defaults to docstring)

    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        # Check if it's an async function
        is_async = asyncio.iscoroutinefunction(func)

        # Extract tool information
        tool_name = name or func.__name__
        tool_description = description or (func.__doc__ or "").strip()

        # Extract parameters from function signature
        sig = inspect.signature(func)
        parameters = []

        for param_name, param in sig.parameters.items():
            # Skip self, cls, and context parameters
            if param_name in ("self", "cls", "context") or param_name.startswith("_"):
                continue

            # Get parameter type from type annotation if available
            param_type = "string"  # default
            if param.annotation != inspect.Parameter.empty:
                if param.annotation is str:
                    param_type = "string"
                elif param.annotation is int:
                    param_type = "integer"
                elif param.annotation is float:
                    param_type = "number"
                elif param.annotation is bool:
                    param_type = "boolean"
                elif param.annotation in (dict, dict):
                    param_type = "object"
                elif param.annotation in (list, list):
                    param_type = "array"

            # Check if parameter is required
            required = param.default == inspect.Parameter.empty

            # Add parameter info
            parameters.append(
                {
                    "name": param_name,
                    "type": param_type,
                    "description": "",  # No way to get param descriptions in Python
                    "required": required,
                }
            )

        # Register with the MCP server if available
        try:
            mcp_server = get_mcp_server()
            # Only register if the server is initialized
            if mcp_server:
                if is_async:
                    mcp_server.register_tool_async(tool_name, func, tool_description, parameters)
                else:
                    mcp_server.register_tool(tool_name, func, tool_description, parameters)
        except Exception:
            # Server might not be initialized yet, which is fine
            # The discovery will register it when server is initialized
            logger.debug(f"Could not register tool {tool_name} now, will register during discovery")

        # Mark the function as an MCP tool for discovery
        func = set_function_attribute(func, "tool", True)
        func = set_function_attribute(func, "tool_name", tool_name)
        func = set_function_attribute(func, "tool_description", tool_description)
        func = set_function_attribute(func, "tool_parameters", parameters)
        func = set_function_attribute(func, "tool_is_async", is_async)

        return func

    return decorator


def prompt(name: str | None = None, description: str | None = None) -> Callable[[F], F]:
    """
    Register a prompt with the MCP server.

    This decorator can be applied to any function to expose it as an MCP prompt.

    Args:
        name: Optional name for the prompt (defaults to function name)
        description: Optional description for the prompt (defaults to docstring)

    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        # Check if it's an async function
        is_async = asyncio.iscoroutinefunction(func)

        # Extract prompt information
        prompt_name = name or func.__name__
        prompt_description = description or (func.__doc__ or "").strip()

        # Extract arguments from function signature
        sig = inspect.signature(func)
        arguments = []

        for param_name, param in sig.parameters.items():
            # Skip self, cls parameters
            if param_name in ("self", "cls") or param_name.startswith("_"):
                continue

            # Check if parameter is required
            required = param.default == inspect.Parameter.empty

            # Add argument info
            arguments.append(
                {
                    "name": param_name,
                    "description": "",  # No way to get param descriptions in Python
                    "required": required,
                }
            )

        # Create a wrapper that handles the prompt format conversion
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            # Call the original function
            result = func(*args, **kwargs)

            # Return as string if not already in the right format
            if not isinstance(result, (dict, list)):
                return str(result)
            return result

        # For async functions
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            # Call the original function
            result = await func(*args, **kwargs)

            # Return as string if not already in the right format
            if not isinstance(result, (dict, list)):
                return str(result)
            return result

        # Register with the MCP server if available
        try:
            mcp_server = get_mcp_server()
            # Only register if the server is initialized
            if mcp_server:
                if is_async:
                    mcp_server.register_prompt_async(prompt_name, async_wrapper, prompt_description, arguments)
                else:
                    mcp_server.register_prompt(prompt_name, wrapper, prompt_description, arguments)
        except Exception:
            # Server might not be initialized yet, which is fine
            # The discovery will register it when server is initialized
            logger.debug(f"Could not register prompt {prompt_name} now, will register during discovery")

        # Mark the function as an MCP prompt for discovery
        func = set_function_attribute(func, "prompt", True)
        func = set_function_attribute(func, "prompt_name", prompt_name)
        func = set_function_attribute(func, "prompt_description", prompt_description)
        func = set_function_attribute(func, "prompt_arguments", arguments)
        func = set_function_attribute(func, "prompt_is_async", is_async)

        return func

    return decorator


def resource(uri_template: str, description: str | None = None) -> Callable[[F], F]:
    """
    Register a resource with the MCP server.

    This decorator can be applied to any function to expose it as an MCP resource.

    Args:
        uri_template: URI template for the resource
        description: Optional description for the resource (defaults to docstring)

    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        # Check if it's an async function
        is_async = asyncio.iscoroutinefunction(func)

        # Extract resource information
        resource_description = description or (func.__doc__ or "").strip()

        # Register with the MCP server if available
        try:
            mcp_server = get_mcp_server()
            # Only register if the server is initialized
            if mcp_server:
                if is_async:
                    mcp_server.register_resource_async(uri_template, func, resource_description)
                else:
                    mcp_server.register_resource(uri_template, func, resource_description)
        except Exception:
            # Server might not be initialized yet, which is fine
            # The discovery will register it when server is initialized
            logger.debug(f"Could not register resource {uri_template} now, will register during discovery")

        # Mark the function as an MCP resource for discovery
        func = set_function_attribute(func, "resource", True)
        func = set_function_attribute(func, "resource_uri_template", uri_template)
        func = set_function_attribute(func, "resource_description", resource_description)
        func = set_function_attribute(func, "resource_is_async", is_async)

        return func

    return decorator


def invoke_tool(name: str, params: dict[str, Any], context: Context | None = None) -> Any:
    """
    Invoke an MCP tool.

    Args:
        name: Name of the tool to invoke.
        params: Parameters to pass to the tool.
        context: Optional context object. If not provided, a new context will be created.

    Returns:
        The result of the tool invocation.

    Raises:
        ValueError: If the tool doesn't exist or the MCP server is not initialized.
    """
    mcp_server = get_mcp_server()
    if not mcp_server:
        raise ValueError("MCP server not initialized")

    if context is None:
        context = Context()

    return mcp_server.invoke_tool(name, params, context)


async def invoke_tool_async(name: str, params: dict[str, Any], context: Context | None = None) -> Any:
    """
    Invoke an asynchronous MCP tool.

    Args:
        name: Name of the tool to invoke.
        params: Parameters to pass to the tool.
        context: Optional context object. If not provided, a new context will be created.

    Returns:
        The result of the tool invocation.

    Raises:
        ValueError: If the tool doesn't exist or the MCP server is not initialized.
    """
    mcp_server = get_mcp_server()
    if not mcp_server:
        raise ValueError("MCP server not initialized")

    if context is None:
        context = Context()

    return await mcp_server.invoke_tool_async(name, params, context)


def invoke_prompt(name: str, args: dict[str, Any], context: Context | None = None) -> str:
    """
    Invoke an MCP prompt.

    Args:
        name: Name of the prompt to invoke.
        args: Arguments to pass to the prompt.
        context: Optional context object. If not provided, a new context will be created.

    Returns:
        The result of the prompt invocation as a string.

    Raises:
        ValueError: If the prompt doesn't exist or the MCP server is not initialized.
    """
    mcp_server = get_mcp_server()
    if not mcp_server:
        raise ValueError("MCP server not initialized")

    if context is None:
        context = Context()

    return mcp_server.invoke_prompt(name, args, context)


async def invoke_prompt_async(name: str, args: dict[str, Any], context: Context | None = None) -> str:
    """
    Invoke an asynchronous MCP prompt.

    Args:
        name: Name of the prompt to invoke.
        args: Arguments to pass to the prompt.
        context: Optional context object. If not provided, a new context will be created.

    Returns:
        The result of the prompt invocation as a string.

    Raises:
        ValueError: If the prompt doesn't exist or the MCP server is not initialized.
    """
    mcp_server = get_mcp_server()
    if not mcp_server:
        raise ValueError("MCP server not initialized")

    if context is None:
        context = Context()

    return await mcp_server.invoke_prompt_async(name, args, context)


def read_resource(uri: str, context: Context | None = None) -> Any:
    """
    Read an MCP resource.

    Args:
        uri: URI of the resource to read.
        context: Optional context object. If not provided, a new context will be created.

    Returns:
        The resource data.

    Raises:
        ValueError: If the resource doesn't exist or the MCP server is not initialized.
    """
    mcp_server = get_mcp_server()
    if not mcp_server:
        raise ValueError("MCP server not initialized")

    if context is None:
        context = Context()

    return mcp_server.read_resource(uri, context)


async def read_resource_async(uri: str, context: Context | None = None) -> Any:
    """
    Read an asynchronous MCP resource.

    Args:
        uri: URI of the resource to read.
        context: Optional context object. If not provided, a new context will be created.

    Returns:
        The resource data.

    Raises:
        ValueError: If the resource doesn't exist or the MCP server is not initialized.
    """
    mcp_server = get_mcp_server()
    if not mcp_server:
        raise ValueError("MCP server not initialized")

    if context is None:
        context = Context()

    return await mcp_server.read_resource_async(uri, context)
