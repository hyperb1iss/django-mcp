"""
Django model integration for django-mcp.

This module provides utilities for exposing Django models as MCP tools and resources.
"""
# pylint: disable=duplicate-code

import json
from typing import Any

from django.db import models
from django.db.models import Model, Q
from django.db.models.manager import Manager

from django_mcp.inspection import (
    get_app_label,
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
        model: The Django model class
        prefix: Prefix for the tool name
        **_kwargs: Additional keyword arguments
    """
    verbose_name = get_verbose_name(model)
    mcp_server = get_mcp_server()

    @mcp_server.tool(description=f"Get a {verbose_name} by ID")
    def get_model_instance(instance_id: int) -> dict[str, Any]:
        """
        Get a single instance of {verbose_name} by ID.

        Args:
            instance_id: The primary key of the {verbose_name} to retrieve
        """
        # Use correct typing for model manager
        objects: Any = getattr(model, "objects", None)
        if not isinstance(objects, Manager):
            return {"error": "Model does not have a valid objects manager"}

        try:
            instance = objects.get(pk=instance_id)
            return _instance_to_dict(instance)
        except Exception as e:
            # More generic exception handling to cover DoesNotExist
            return {"error": f"{verbose_name.title()} with ID {instance_id} not found: {e!s}"}

    # Rename the function to avoid name collisions
    get_model_instance.__name__ = f"get_{prefix}_instance"


def register_model_list_tool(model: type[Model], prefix: str, **_kwargs: Any) -> None:
    """
    Register a tool to list model instances.

    Args:
        model: The Django model class
        prefix: Prefix for the tool name
        **_kwargs: Additional keyword arguments
    """
    verbose_name_plural = get_verbose_name_plural(model)
    mcp_server = get_mcp_server()

    @mcp_server.tool(description=f"List {verbose_name_plural}")
    def list_model_instances(limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        """
        List instances of {verbose_name_plural}.

        Args:
            limit: Maximum number of instances to return
            offset: Offset to start from
        """
        # Use correct typing for model manager
        objects: Any = getattr(model, "objects", None)
        if not isinstance(objects, Manager):
            return [{"error": "Model does not have a valid objects manager"}]

        instances = objects.all()[offset : offset + limit]
        return [_instance_to_dict(instance) for instance in instances]

    # Rename the function to avoid name collisions
    list_model_instances.__name__ = f"list_{prefix}_instances"


def register_model_search_tool(model: type[Model], prefix: str, **_kwargs: Any) -> None:
    """
    Register a tool to search model instances.

    Args:
        model: The Django model class
        prefix: Prefix for the tool name
        **_kwargs: Additional keyword arguments
    """
    verbose_name_plural = get_verbose_name_plural(model)
    mcp_server = get_mcp_server()

    @mcp_server.tool(description=f"Search for {verbose_name_plural}")
    def search_model_instances(query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Search for {verbose_name_plural}.

        Args:
            query: Search query
            limit: Maximum number of instances to return
        """
        # Use correct typing for model manager
        objects: Any = getattr(model, "objects", None)
        if not isinstance(objects, Manager):
            return [{"error": "Model does not have a valid objects manager"}]

        # Get searchable fields from model
        fields = _get_searchable_fields(model)
        q_objects = Q()
        for field in fields:
            q_objects |= Q(**{f"{field}__icontains": query})

        instances = objects.filter(q_objects)[:limit]
        return [_instance_to_dict(instance) for instance in instances]

    # Rename the function to avoid name collisions
    search_model_instances.__name__ = f"search_{prefix}_instances"


def register_model_create_tool(model: type[Model], prefix: str, **_kwargs: Any) -> None:
    """
    Register a tool to create model instances.

    Args:
        model: The Django model class
        prefix: Prefix for the tool name
        **_kwargs: Additional keyword arguments
    """
    verbose_name = get_verbose_name(model)
    mcp_server = get_mcp_server()

    @mcp_server.tool(description=f"Create a new {verbose_name}")
    def create_model_instance(**kwargs: Any) -> dict[str, Any]:
        """
        Create a new {verbose_name}.
        """
        # Use correct typing for model manager
        objects: Any = getattr(model, "objects", None)
        if not isinstance(objects, Manager):
            return {"error": "Model does not have a valid objects manager"}

        # Filter kwargs to only include model fields
        filtered_kwargs = {}
        model_fields = _get_model_fields(model)
        for field_name, value in kwargs.items():
            if field_name in model_fields:
                filtered_kwargs[field_name] = value

        # Create the instance
        instance = objects.create(**filtered_kwargs)
        return _instance_to_dict(instance)

    # Rename the function to avoid name collisions
    create_model_instance.__name__ = f"create_{prefix}_instance"


def register_model_resource(
    model: type[Model], lookup: str = "pk", fields: list[str] | None = None, **kwargs: Any
) -> None:
    """
    Register a resource for a model.

    Args:
        model: The Django model class
        lookup: Field to use for lookup (default: "pk")
        fields: List of fields to include (default: all fields)
        **kwargs: Additional keyword arguments for resource registration
    """
    mcp_server = get_mcp_server()
    verbose_name = get_verbose_name(model)
    app_label = get_app_label(model)
    model_name = get_model_name(model)

    # Create URI template
    uri_template = kwargs.pop("uri_template", None)
    if uri_template is None:
        # Use the app_label and the lookup field in the URI template
        uri_template = f"{app_label}://{{{lookup}}}"

    # Get all field names if not specified
    if not fields:
        fields = _get_model_fields(model)

    @mcp_server.resource(uri_template, **kwargs)
    def get_model_resource(pk: str) -> str:
        """
        Get model instance as a resource.

        Args:
            pk: The ID to look up

        Returns:
            Model instance as JSON string
        """
        # Use correct typing for model manager
        objects: Any = getattr(model, "objects", None)
        if not isinstance(objects, Manager):
            return json.dumps({"error": "Model does not have a valid objects manager"})

        # Build lookup dict based on lookup field
        lookup_dict = {lookup: pk}

        try:
            instance = objects.get(**lookup_dict)
        except Exception as e:
            # More generic exception handling to cover DoesNotExist
            return json.dumps(
                {
                    "error": f"{verbose_name.title()} not found",
                    "id": pk,
                    "lookup": lookup,
                    "details": str(e),
                }
            )

        # Convert instance to dict
        instance_dict = {}
        for field in fields:
            if hasattr(instance, field):
                value = getattr(instance, field)
                # Handle special cases like dates and models
                if hasattr(value, "isoformat"):
                    instance_dict[field] = value.isoformat()
                elif isinstance(value, Model):
                    # For related models, just include ID
                    instance_dict[field] = getattr(value, "pk", str(value))
                else:
                    instance_dict[field] = value

        # Return as JSON
        return json.dumps(instance_dict)

    # Rename the function to avoid name collisions
    get_model_resource.__name__ = f"get_{app_label}_{model_name}_resource"


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


def _get_searchable_fields(model: type[Model]) -> list[str]:
    """
    Get a list of searchable field names from the model.

    Args:
        model: The Django model class

    Returns:
        List of field names that can be used for text search
    """
    searchable_fields = []
    for field in model._meta.fields:  # noqa: SLF001
        # Only consider text fields for search
        if isinstance(field, models.CharField | models.TextField):
            searchable_fields.append(field.name)
    return searchable_fields


def _get_model_fields(model: type[Model]) -> list[str]:
    """
    Get a list of all field names from the model.

    Args:
        model: The Django model class

    Returns:
        List of all field names
    """
    return [field.name for field in model._meta.fields]  # noqa: SLF001
