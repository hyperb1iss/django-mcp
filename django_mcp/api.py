"""
High-level API for django-mcp.

This module provides a simplified API for common MCP operations.
"""

from collections.abc import Callable
from functools import wraps
import inspect
import logging
from typing import Any, TypeVar, cast

from mcp.server.fastmcp import Context

from django_mcp.api_inspection import set_function_attribute
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
        is_async = inspect.iscoroutinefunction(func)

        # Get the tool name
        tool_name = name or func.__name__

        # Get the tool description
        tool_description = description or inspect.getdoc(func) or f"Tool: {tool_name}"

        # Check for parameter annotations and create parameters
        sig = inspect.signature(func)
        parameters = {}

        # Extract parameters from function signature
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue  # Skip self and cls parameters
            if param_name == "context":
                continue  # Skip context parameter

            # Get parameter type and default
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else Any
            default = param.default if param.default != inspect.Parameter.empty else None
            required = param.default == inspect.Parameter.empty

            # Add parameter to parameters dict
            parameters[param_name] = {
                "type": param_type,
                "required": required,
                "default": default,
            }

        # Create a wrapper that handles the tool format conversion
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # For async functions
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        # Register with the MCP server if available
        try:
            mcp_server = get_mcp_server()
            # Only register if the server is initialized
            if mcp_server:
                if is_async:
                    mcp_server.register_tool_async(tool_name, async_wrapper, tool_description, parameters)  # type: ignore
                else:
                    mcp_server.register_tool(tool_name, wrapper, tool_description, parameters)  # type: ignore
        except Exception:
            # Server might not be initialized yet, which is fine
            # The discovery will register it when server is initialized
            logger.debug("Could not register tool %s now, will register during discovery", tool_name)

        # Mark the function as an MCP tool for discovery
        func = set_function_attribute(func, "tool", True)
        func = set_function_attribute(func, "tool_name", tool_name)
        func = set_function_attribute(func, "tool_description", tool_description)
        func = set_function_attribute(func, "tool_parameters", parameters)
        return set_function_attribute(func, "tool_is_async", is_async)

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
        is_async = inspect.iscoroutinefunction(func)

        # Get the prompt name
        prompt_name = name or func.__name__

        # Get the prompt description
        prompt_description = description or inspect.getdoc(func) or f"Prompt: {prompt_name}"

        # Check for parameter annotations and create arguments
        sig = inspect.signature(func)
        arguments = {}

        # Extract arguments from function signature
        for arg_name, param in sig.parameters.items():
            if arg_name in ("self", "cls"):
                continue  # Skip self and cls parameters
            if arg_name == "context":
                continue  # Skip context parameter

            # Get parameter type and default
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else Any
            default = param.default if param.default != inspect.Parameter.empty else None
            required = param.default == inspect.Parameter.empty

            # Add argument to arguments dict
            arguments[arg_name] = {
                "type": param_type,
                "required": required,
                "default": default,
            }

        # Create a wrapper that handles the prompt format conversion
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            # Call the original function
            result = func(*args, **kwargs)

            # Return as string if not already in the right format
            if not isinstance(result, dict | list):
                return {"result": str(result)}
            return cast(dict[str, Any], result)

        # For async functions
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            # Call the original function
            result = await func(*args, **kwargs)

            # Return as string if not already in the right format
            if not isinstance(result, dict | list):
                return {"result": str(result)}
            return cast(dict[str, Any], result)

        # Register with the MCP server if available
        try:
            mcp_server = get_mcp_server()
            # Only register if the server is initialized
            if mcp_server:
                if is_async:
                    mcp_server.register_prompt_async(prompt_name, async_wrapper, prompt_description, arguments)  # type: ignore
                else:
                    mcp_server.register_prompt(prompt_name, wrapper, prompt_description, arguments)  # type: ignore
        except Exception:
            # Server might not be initialized yet, which is fine
            # The discovery will register it when server is initialized
            logger.debug("Could not register prompt %s now, will register during discovery", prompt_name)

        # Mark the function as an MCP prompt for discovery
        func = set_function_attribute(func, "prompt", True)
        func = set_function_attribute(func, "prompt_name", prompt_name)
        func = set_function_attribute(func, "prompt_description", prompt_description)
        func = set_function_attribute(func, "prompt_arguments", arguments)
        return set_function_attribute(func, "prompt_is_async", is_async)

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
        is_async = inspect.iscoroutinefunction(func)

        # Get the resource description
        resource_description = description or inspect.getdoc(func) or f"Resource: {uri_template}"

        # Register with the MCP server if available
        try:
            mcp_server = get_mcp_server()
            # Only register if the server is initialized
            if mcp_server:
                if is_async:
                    mcp_server.register_resource_async(uri_template, func, resource_description)  # type: ignore
                else:
                    mcp_server.register_resource(uri_template, func, resource_description)  # type: ignore
        except Exception:
            # Server might not be initialized yet, which is fine
            # The discovery will register it when server is initialized
            logger.debug("Could not register resource %s now, will register during discovery", uri_template)

        # Mark the function as an MCP resource for discovery
        func = set_function_attribute(func, "resource", True)
        func = set_function_attribute(func, "resource_uri_template", uri_template)
        func = set_function_attribute(func, "resource_description", resource_description)
        return set_function_attribute(func, "resource_is_async", is_async)

    return decorator


def invoke_tool(name: str, params: dict[str, Any], context: Context | None = None) -> Any:
    """
    Invoke an MCP tool.

    Args:
        name: Name of the tool to invoke.
        params: Parameters to pass to the tool.
        context: Optional context object for the tool execution.

    Returns:
        The result of invoking the tool.
    """
    try:
        mcp_server = get_mcp_server()
    except Exception as e:
        raise ValueError(f"MCP server not initialized: {e!s}") from e

    # Invoke the tool
    return mcp_server.invoke_tool(name, params, context)  # type: ignore


async def invoke_tool_async(name: str, params: dict[str, Any], context: Context | None = None) -> Any:
    """
    Invoke an MCP tool asynchronously.

    Args:
        name: Name of the tool to invoke.
        params: Parameters to pass to the tool.
        context: Optional context object for the tool execution.

    Returns:
        The result of invoking the tool.
    """
    try:
        mcp_server = get_mcp_server()
    except Exception as e:
        raise ValueError(f"MCP server not initialized: {e!s}") from e

    # Invoke the tool asynchronously
    return await mcp_server.invoke_tool_async(name, params, context)  # type: ignore


def invoke_prompt(name: str, args: dict[str, Any], context: Context | None = None) -> str:
    """
    Invoke an MCP prompt.

    Args:
        name: Name of the prompt to invoke.
        args: Arguments to pass to the prompt.
        context: Optional context object for the prompt execution.

    Returns:
        The result of invoking the prompt (as a string).
    """
    try:
        mcp_server = get_mcp_server()
    except Exception as e:
        raise ValueError(f"MCP server not initialized: {e!s}") from e

    # Invoke the prompt
    return cast(str, mcp_server.invoke_prompt(name, args, context))  # type: ignore


async def invoke_prompt_async(name: str, args: dict[str, Any], context: Context | None = None) -> str:
    """
    Invoke an MCP prompt asynchronously.

    Args:
        name: Name of the prompt to invoke.
        args: Arguments to pass to the prompt.
        context: Optional context object for the prompt execution.

    Returns:
        The result of invoking the prompt (as a string).
    """
    try:
        mcp_server = get_mcp_server()
    except Exception as e:
        raise ValueError(f"MCP server not initialized: {e!s}") from e

    # Invoke the prompt asynchronously
    return cast(str, await mcp_server.invoke_prompt_async(name, args, context))  # type: ignore


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

    # The FastMCP.read_resource method doesn't accept a context parameter
    return mcp_server.read_resource(uri)


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

    # Use the standard read_resource method since read_resource_async doesn't exist
    return await mcp_server.read_resource(uri)
