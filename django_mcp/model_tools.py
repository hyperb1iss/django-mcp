"""
Django model integration for django-mcp.

This module provides utilities for exposing Django models as MCP tools and resources.
"""
# pylint: disable=duplicate-code

from typing import Any

from django.db import models
from django.db.models import Model, Q

from django_mcp.inspection import (
    get_app_label,
    get_model_field_names,
    get_model_fields,
    get_model_name,
    get_verbose_name,
    get_verbose_name_plural,
)
from django_mcp.server import get_mcp_server


def register_model_tools(
    model: type[Model],
    prefix: str | None = None,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    **kwargs: Any,
) -> None:
    """
    Register standard CRUD tools for a Django model.

    Args:
        model: Django model class
        prefix: Optional prefix for tool names (defaults to model name)
        include: Optional list of tools to include (get, list, search, create)
        exclude: Optional list of tools to exclude
        **kwargs: Additional kwargs for tool registration
    """
    try:
        get_mcp_server()
    except Exception:
        # Server not initialized yet
        return

    # Get model metadata
    model_name = get_model_name(model)

    # Set default prefix if not provided
    if prefix is None:
        prefix = model_name

    # Default tools to include
    all_tools = ["get", "list", "search", "create"]

    # Determine which tools to register
    tools_to_register = all_tools
    if include is not None:
        tools_to_register = [t for t in all_tools if t in include]
    if exclude is not None:
        tools_to_register = [t for t in tools_to_register if t not in exclude]

    # Register individual tools
    if "get" in tools_to_register:
        register_model_get_tool(model, prefix, **kwargs)

    if "list" in tools_to_register:
        register_model_list_tool(model, prefix, **kwargs)

    if "search" in tools_to_register:
        register_model_search_tool(model, prefix, **kwargs)

    if "create" in tools_to_register:
        register_model_create_tool(model, prefix, **kwargs)


def register_model_get_tool(model: type[Model], prefix: str, **_kwargs: Any) -> None:
    """
    Register a tool to get a single model instance by ID.

    Args:
        model: Django model class
        prefix: Prefix for the tool name
        **_kwargs: Additional kwargs for tool registration (not used)
    """
    mcp_server = get_mcp_server()
    verbose_name = get_verbose_name(model)

    @mcp_server.tool(description=f"Get a {verbose_name} by ID")
    def get_model_instance(instance_id: int) -> dict[str, Any]:
        """
        Get a single instance of {verbose_name} by ID.

        Args:
            instance_id: The primary key of the {verbose_name} to retrieve
        """
        try:
            instance = model.objects.get(pk=instance_id)
            return _instance_to_dict(instance)
        except model.DoesNotExist:
            return {"error": f"{verbose_name.title()} with ID {instance_id} not found"}

    # Rename the function to avoid name collisions
    get_model_instance.__name__ = f"get_{prefix}_instance"


def register_model_list_tool(model: type[Model], prefix: str, **_kwargs: Any) -> None:
    """
    Register a tool to list model instances.

    Args:
        model: Django model class
        prefix: Prefix for the tool name
        **_kwargs: Additional kwargs for tool registration (not used)
    """
    mcp_server = get_mcp_server()
    verbose_name_plural = get_verbose_name_plural(model)

    @mcp_server.tool(description=f"List {verbose_name_plural}")
    def list_model_instances(limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        """
        List instances of {verbose_name}.

        Args:
            limit: Maximum number of instances to return
            offset: Number of instances to skip
        """
        instances = model.objects.all()[offset : offset + limit]
        return [_instance_to_dict(instance) for instance in instances]

    # Rename the function to avoid name collisions
    list_model_instances.__name__ = f"list_{prefix}_instances"


def register_model_search_tool(model: type[Model], prefix: str, **_kwargs: Any) -> None:
    """
    Register a tool to search model instances.

    Args:
        model: Django model class
        prefix: Prefix for the tool name
        **_kwargs: Additional kwargs for tool registration (not used)
    """
    mcp_server = get_mcp_server()
    verbose_name_plural = get_verbose_name_plural(model)

    @mcp_server.tool(description=f"Search for {verbose_name_plural}")
    def search_model_instances(query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Search for {verbose_name} instances by text fields.

        Args:
            query: Search query
            limit: Maximum number of instances to return
        """
        # Build Q objects for text fields
        q_objects = Q()
        for field in get_model_fields(model):
            if isinstance(field, models.CharField | models.TextField):
                q_objects |= Q(**{f"{field.name}__icontains": query})

        # Return empty list if no text fields
        if not q_objects:
            return []

        instances = model.objects.filter(q_objects)[:limit]
        return [_instance_to_dict(instance) for instance in instances]

    # Rename the function to avoid name collisions
    search_model_instances.__name__ = f"search_{prefix}_instances"


def register_model_create_tool(model: type[Model], prefix: str, **_kwargs: Any) -> None:
    """
    Register a tool for creating model instances.

    Args:
        model: Django model class
        prefix: Prefix for tool name
        **_kwargs: Additional kwargs for tool registration (not used)
    """
    try:
        mcp_server = get_mcp_server()
    except Exception:
        # Server not initialized yet
        return

    # Get model info
    verbose_name = get_verbose_name(model)
    model_name = get_model_name(model)

    # Tool name with prefix
    tool_name = f"{prefix}create_{model_name}" if prefix else f"create_{model_name}"

    # Define the function that creates instances
    @mcp_server.tool(description=f"Create a new {verbose_name}")
    def create_model_instance(**kwargs: Any) -> dict[str, Any]:
        """
        Create a new model instance.

        Args:
            **kwargs: Fields for the new instance

        Returns:
            Dictionary with created instance data
        """
        # Validate fields - only accept valid model fields
        valid_fields = set(get_model_field_names(model, exclude_pk=True))

        # Filter out invalid fields
        filtered_kwargs = {key: value for key, value in kwargs.items() if key in valid_fields}

        # Create the instance
        instance = model.objects.create(**filtered_kwargs)

        # Return as dict
        return _instance_to_dict(instance)

    # Rename the function to avoid name collisions
    create_model_instance.__name__ = tool_name


def register_model_resource(
    model: type[Model], lookup: str = "pk", fields: list[str] | None = None, **kwargs: Any
) -> None:
    """
    Register a model as an MCP resource.

    Args:
        model: Django model class
        lookup: Field to use for lookup (default: 'pk')
        fields: Optional list of fields to include
        **kwargs: Additional kwargs for resource registration
    """
    try:
        mcp_server = get_mcp_server()
    except Exception:
        # Server not initialized yet
        return

    # Create URI template based on app and model
    app_label = get_app_label(model)
    model_name = get_model_name(model)
    uri_template = f"{app_label}://{{{lookup}}}"

    # Define the resource function with a parameter that matches the URI template
    @mcp_server.resource(uri_template, **kwargs)
    def get_model_resource(pk: str) -> str:
        """
        Get a model instance as a resource.

        Args:
            pk: The primary key (or lookup value) of the instance

        Returns:
            Markdown representation of the instance
        """
        try:
            # Build lookup dict dynamically for flexibility
            lookup_dict = {lookup: pk}
            instance = model.objects.get(**lookup_dict)

            # Format as Markdown for better LLM consumption
            md_lines = [
                f"# {get_verbose_name(model).title()}: {instance}",
                "",
                f"Information about this {get_verbose_name(model)}.",
                "",
                "## Attributes",
                "",
            ]

            # Add fields
            instance_dict = _instance_to_dict(instance)
            field_names = fields if fields else instance_dict.keys()

            for field_name in field_names:
                if field_name in instance_dict:
                    md_lines.append(f"- **{field_name}**: {instance_dict[field_name]}")

            return "\n".join(md_lines)
        except model.DoesNotExist:
            return f"# Not Found\n\nThe {get_verbose_name(model)} with {lookup}={pk} does not exist."
        except Exception as e:
            return f"# Error\n\nError retrieving {get_verbose_name(model)}: {e!s}"

    # Rename the function to avoid name collisions
    get_model_resource.__name__ = f"get_{model_name}_resource"


def _instance_to_dict(instance: Model) -> dict[str, Any]:
    """
    Convert a model instance to a dictionary.

    Args:
        instance: A Django model instance

    Returns:
        Dictionary with field values
    """
    result = {}

    # Get all fields from the model
    fields = get_model_fields(instance)

    # Add each field to the result
    for field in fields:
        field_name = field.name
        value = getattr(instance, field_name)
        # Don't convert to string - keep the original Python type
        result[field_name] = value

    return result
