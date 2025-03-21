"""
MCP inspection utilities for Django-MCP.

This module provides functions for accessing MCP components (tools, resources, prompts)
in a way that avoids accessing private members of the MCP server.
"""

from typing import Any

from django.db.models import Model

from django_mcp.server import get_mcp_server

# ----------------------
# MCP Component Inspection
# ----------------------


def get_tools() -> list[dict[str, Any]]:
    """
    Get all registered MCP tools.

    Returns:
        List of tool objects with their metadata
    """
    mcp_server = get_mcp_server()
    # We access the private members here so the rest of the codebase doesn't have to
    return list(mcp_server._tool_manager.tools.values())  # noqa: SLF001


def get_resources() -> list[dict[str, Any]]:
    """
    Get all registered MCP resources.

    Returns:
        List of resource objects with their metadata
    """
    mcp_server = get_mcp_server()
    # We access the private members here so the rest of the codebase doesn't have to
    return list(mcp_server._resource_manager.resources.values())  # noqa: SLF001


def get_prompts() -> list[dict[str, Any]]:
    """
    Get all registered MCP prompts.

    Returns:
        List of prompt objects with their metadata
    """
    mcp_server = get_mcp_server()
    # We access the private members here so the rest of the codebase doesn't have to
    return list(mcp_server._prompt_manager.prompts.values())  # noqa: SLF001


def get_tool(name: str) -> dict[str, Any]:
    """
    Get a specific MCP tool by name.

    Args:
        name: Tool name

    Returns:
        Tool object

    Raises:
        ValueError: If tool doesn't exist
    """
    mcp_server = get_mcp_server()
    # We access the private members here so the rest of the codebase doesn't have to
    if name not in mcp_server._tool_manager.tools:  # noqa: SLF001
        raise ValueError(f"Tool '{name}' not found")
    return mcp_server._tool_manager.tools[name]  # noqa: SLF001


def has_tool(name: str) -> bool:
    """
    Check if a tool exists.

    Args:
        name: Tool name

    Returns:
        True if the tool exists
    """
    mcp_server = get_mcp_server()
    # We access the private members here so the rest of the codebase doesn't have to
    return name in mcp_server._tool_manager.tools  # noqa: SLF001


def match_resource_uri(uri: str) -> dict[str, Any] | None:
    """
    Find a resource matching the given URI.

    Args:
        uri: URI to match

    Returns:
        Matching resource or None if not found
    """
    mcp_server = get_mcp_server()

    # We access the private members here so the rest of the codebase doesn't have to
    for resource in mcp_server._resource_manager.resources.values():  # noqa: SLF001
        # Basic check - this is not perfect but works for simple cases
        # For real template matching we'd need a proper URI template library
        template_parts = resource.uri_template.split("/")
        uri_parts = uri.split("/")

        if len(template_parts) != len(uri_parts):
            continue

        matches = True
        for t_part, u_part in zip(template_parts, uri_parts, strict=False):
            # Check if this is a parameter part (e.g. {param})
            if t_part.startswith("{") and t_part.endswith("}"):
                continue  # This is a parameter, so it matches any value
            if t_part != u_part:
                matches = False
                break

        if matches:
            return resource

    return None


def get_prompt(name: str) -> dict[str, Any]:
    """
    Get a specific MCP prompt by name.

    Args:
        name: Prompt name

    Returns:
        Prompt object

    Raises:
        ValueError: If prompt doesn't exist
    """
    mcp_server = get_mcp_server()
    # We access the private members here so the rest of the codebase doesn't have to
    if name not in mcp_server._prompt_manager.prompts:  # noqa: SLF001
        raise ValueError(f"Prompt '{name}' not found")
    return mcp_server._prompt_manager.prompts[name]  # noqa: SLF001


def has_prompt(name: str) -> bool:
    """
    Check if a prompt exists.

    Args:
        name: Prompt name

    Returns:
        True if the prompt exists
    """
    mcp_server = get_mcp_server()
    # We access the private members here so the rest of the codebase doesn't have to
    return name in mcp_server._prompt_manager.prompts  # noqa: SLF001


# ----------------------
# Django Model Inspection
# ----------------------


def get_model_meta(model: type[Model] | Model) -> Any:
    """
    Get the model's _meta object in a way that avoids SLF001 linting errors.

    Args:
        model: The Django model class or instance

    Returns:
        The model's _meta object
    """
    # We access the _meta private member here so the rest of the codebase doesn't have to
    return model._meta  # noqa: SLF001


def get_model_name(model: type[Model] | Model) -> str:
    """
    Get the model's name in a way that avoids SLF001 linting errors.

    Args:
        model: The Django model class or instance

    Returns:
        The model name
    """
    meta = get_model_meta(model)
    return meta.model_name


def get_app_label(model: type[Model] | Model) -> str:
    """
    Get the model's app label in a way that avoids SLF001 linting errors.

    Args:
        model: The Django model class or instance

    Returns:
        The app label
    """
    meta = get_model_meta(model)
    return meta.app_label


def get_verbose_name(model: type[Model] | Model) -> str:
    """
    Get the model's verbose name in a way that avoids SLF001 linting errors.

    Args:
        model: The Django model class or instance

    Returns:
        The verbose name
    """
    meta = get_model_meta(model)
    return meta.verbose_name


def get_model_verbose_name_title(model: type[Model] | Model) -> str:
    """
    Get the model's verbose name in title case format.

    Args:
        model: The Django model class or instance

    Returns:
        The verbose name with title case formatting
    """
    verbose_name = get_verbose_name(model)
    return str(verbose_name).title()


def get_verbose_name_plural(model: type[Model] | Model) -> str:
    """
    Get the model's plural verbose name in a way that avoids SLF001 linting errors.

    Args:
        model: The Django model class or instance

    Returns:
        The plural verbose name
    """
    meta = get_model_meta(model)
    return meta.verbose_name_plural


def get_model_fields(model: type[Model] | Model) -> list:
    """
    Get the model's fields in a way that avoids SLF001 linting errors.

    Args:
        model: The Django model class or instance

    Returns:
        List of model fields
    """
    meta = get_model_meta(model)
    return meta.fields


def get_model_field_names(model: type[Model] | Model, exclude_pk: bool = False) -> list[str]:
    """
    Get the names of all fields on a model, optionally excluding primary key fields.

    Args:
        model: The Django model class or instance
        exclude_pk: Whether to exclude primary key fields

    Returns:
        List of field names
    """
    fields = get_model_fields(model)
    if exclude_pk:
        return [field.name for field in fields if field.name != "id" and not field.primary_key]
    return [field.name for field in fields]
