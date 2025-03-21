"""
High-level API for django-mcp.

This module provides a simplified API for common MCP operations.
"""

from collections.abc import Callable
import inspect
from typing import Any, TypeVar

from django_mcp.context import Context
from django_mcp.server import get_mcp_server

# Type variables for better type hinting
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


def tool(name: str | None = None, description: str | None = None, is_async: bool = False) -> Callable[[F], F]:
    """
    Decorator to register a function as an MCP tool.

    Args:
        name: Optional name for the tool. If not provided, the function name will be used.
        description: Optional description for the tool. If not provided, the function's docstring will be used.
        is_async: Whether the tool function is asynchronous.

    Returns:
        The decorated function.

    Example:
        @tool(description="Get the current user info")
        def get_user_info(context: Context) -> Dict[str, Any]:
            return {"username": context.user.username if context.user else None}
    """

    def decorator(func: F) -> F:
        # Tool name from function name if not provided
        tool_name = name or func.__name__
        # Description from docstring if not provided
        tool_description = description or (func.__doc__ or "").strip()

        # Get the parameters from function signature
        sig = inspect.signature(func)
        parameters = []

        for param_name, param in list(sig.parameters.items())[1:]:  # Skip 'context' param
            param_type = "string"  # Default type
            param_desc = ""
            is_required = param.default == inspect.Parameter.empty

            # Get parameter type from type annotation if available
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == str:
                    param_type = "string"
                elif param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation in (dict, dict):
                    param_type = "object"
                elif param.annotation in (list, list):
                    param_type = "array"

            parameters.append(
                {"name": param_name, "type": param_type, "description": param_desc, "required": is_required}
            )

        # Register the tool
        try:
            mcp_server = get_mcp_server()
            if mcp_server:
                if is_async:

                    async def wrapper(context: Context, **kwargs: Any) -> Any:
                        return await func(context, **kwargs)

                    mcp_server.register_tool_async(tool_name, wrapper, tool_description, parameters)
                else:
                    mcp_server.register_tool(tool_name, func, tool_description, parameters)
        except Exception:
            # Server might not be initialized yet, which is fine
            # The discovery will register it when server is initialized
            pass

        # Mark the function as an MCP tool for discovery
        func._mcp_tool = True  # type: ignore
        func._mcp_tool_name = tool_name  # type: ignore
        func._mcp_tool_description = tool_description  # type: ignore
        func._mcp_tool_parameters = parameters  # type: ignore
        func._mcp_tool_is_async = is_async  # type: ignore

        return func

    return decorator


def prompt(name: str | None = None, description: str | None = None, is_async: bool = False) -> Callable[[F], F]:
    """
    Decorator to register a function as an MCP prompt.

    Args:
        name: Optional name for the prompt. If not provided, the function name will be used.
        description: Optional description for the prompt. If not provided, the function's docstring will be used.
        is_async: Whether the prompt function is asynchronous.

    Returns:
        The decorated function.

    Example:
        @prompt(description="Generate a greeting message")
        def greeting(context: Context, name: str) -> str:
            return f"Hello, {name}!"
    """

    def decorator(func: F) -> F:
        # Prompt name from function name if not provided
        prompt_name = name or func.__name__
        # Description from docstring if not provided
        prompt_description = description or (func.__doc__ or "").strip()

        # Get the arguments from function signature
        sig = inspect.signature(func)
        arguments = []

        for param_name, param in list(sig.parameters.items())[1:]:  # Skip 'context' param
            param_desc = ""
            is_required = param.default == inspect.Parameter.empty

            arguments.append({"name": param_name, "description": param_desc, "required": is_required})

        # Register the prompt
        try:
            mcp_server = get_mcp_server()
            if mcp_server:
                if is_async:

                    async def wrapper(context: Context, **kwargs: Any) -> str:
                        result = await func(context, **kwargs)
                        return str(result)

                    mcp_server.register_prompt_async(prompt_name, wrapper, prompt_description, arguments)
                else:

                    def wrapper(context: Context, **kwargs: Any) -> str:
                        result = func(context, **kwargs)
                        return str(result)

                    mcp_server.register_prompt(prompt_name, wrapper, prompt_description, arguments)
        except Exception:
            # Server might not be initialized yet, which is fine
            # The discovery will register it when server is initialized
            pass

        # Mark the function as an MCP prompt for discovery
        func._mcp_prompt = True  # type: ignore
        func._mcp_prompt_name = prompt_name  # type: ignore
        func._mcp_prompt_description = prompt_description  # type: ignore
        func._mcp_prompt_arguments = arguments  # type: ignore
        func._mcp_prompt_is_async = is_async  # type: ignore

        return func

    return decorator


def resource(uri_template: str, description: str | None = None, is_async: bool = False) -> Callable[[F], F]:
    """
    Decorator to register a function as an MCP resource.

    Args:
        uri_template: URI template for the resource.
        description: Optional description for the resource. If not provided, the function's docstring will be used.
        is_async: Whether the resource function is asynchronous.

    Returns:
        The decorated function.

    Example:
        @resource(uri_template="user/{id}", description="Get user data")
        def get_user(context: Context, uri: str) -> Dict[str, Any]:
            user_id = uri.split('/')[-1]
            return {"id": user_id, "name": f"User {user_id}"}
    """

    def decorator(func: F) -> F:
        # Description from docstring if not provided
        resource_description = description or (func.__doc__ or "").strip()

        # Register the resource
        try:
            mcp_server = get_mcp_server()
            if mcp_server:
                if is_async:
                    mcp_server.register_resource_async(uri_template, func, resource_description)
                else:
                    mcp_server.register_resource(uri_template, func, resource_description)
        except Exception:
            # Server might not be initialized yet, which is fine
            # The discovery will register it when server is initialized
            pass

        # Mark the function as an MCP resource for discovery
        func._mcp_resource = True  # type: ignore
        func._mcp_resource_uri_template = uri_template  # type: ignore
        func._mcp_resource_description = resource_description  # type: ignore
        func._mcp_resource_is_async = is_async  # type: ignore

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
