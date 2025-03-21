"""
Django admin integration for django-mcp.

This module provides utilities for exposing Django admin actions as MCP tools.
"""
# pylint: disable=duplicate-code

from typing import Any, TypeVar

from django.contrib.admin import AdminSite
from django.contrib.admin.options import ModelAdmin
from django.db.models import Model
from django.db.models.manager import Manager

from django_mcp.api_inspection import get_admin_site_registry
from django_mcp.inspection import (
    get_app_label,
    get_model_name,
    get_verbose_name,
    get_verbose_name_plural,
)
from django_mcp.server import get_mcp_server

# Define type variables for ModelAdmin
T_Model = TypeVar("T_Model", bound=Model)
ModelAdminT = TypeVar("ModelAdminT", bound="ModelAdmin")


def get_available_admin_sites() -> list[AdminSite]:
    """
    Get all registered Django admin sites.

    Returns:
        List of admin site instances
    """
    from django.contrib import admin

    # Start with the default admin site
    sites = [admin.site]

    # Look for other admin sites in the admin module
    for name in dir(admin):
        obj = getattr(admin, name)
        if isinstance(obj, AdminSite) and obj not in sites:
            sites.append(obj)

    return sites


def register_admin_tools(
    admin_class: type[ModelAdmin], model: type[Model], exclude_actions: list[str] | None = None, **_kwargs: Any
) -> None:
    """
    Register tools for Django admin actions.

    Args:
        admin_class: ModelAdmin subclass
        model: Django model class
        exclude_actions: List of action names to exclude
        **_kwargs: Additional kwargs (not used)
    """
    # Get MCP server
    get_mcp_server()

    # Get model metadata
    model_name = get_model_name(model)
    verbose_name = get_verbose_name(model)

    # Extract actions from the admin class
    actions = getattr(admin_class, "actions", [])
    if not actions:
        return

    # Convert actions dict to list of (name, func) tuples for iteration
    action_items = []

    # Handle both dict-style actions and list-style actions
    if isinstance(actions, dict):
        # Dict-style actions: {"name": function}
        action_items = list(actions.items())
    elif isinstance(actions, list):
        # List-style actions: [function1, function2]
        action_items = []
        for func in actions:
            # Try to get function name
            name = getattr(func, "__name__", str(func))
            action_items.append((name, func))

    # Filter excluded actions
    if exclude_actions:
        action_items = [(name, func) for name, func in action_items if name not in exclude_actions]

    # Register tools for each action
    for action_name, action_func in action_items:
        # Create a slug-friendly version of the action name
        action_name_slug = action_name.replace("_", "-")

        # Register an MCP tool for this action
        _register_admin_action_tool(
            model=model,
            model_name=model_name,
            verbose_name=verbose_name,
            action=action_func,
            action_name=action_name,
            action_name_slug=action_name_slug,
        )


def _register_admin_action_tool(
    model: type[Model],
    model_name: str,
    verbose_name: str,
    action: Any,
    action_name: str,
    action_name_slug: str,
) -> None:
    """
    Register an MCP tool for a specific admin action.

    Args:
        model: Django model class
        model_name: Model name
        verbose_name: Verbose name of the model
        action: Admin action function
        action_name: Name of the action
        action_name_slug: Slug version of the action name
    """
    mcp_server = get_mcp_server()

    @mcp_server.tool(description=f"Execute admin '{action_name}' action on {verbose_name}")
    def admin_action_tool(instance_id: int) -> str:
        """
        Execute an admin action on a model instance.

        Args:
            instance_id: Instance ID to operate on

        Returns:
            Result of the action
        """
        # Use correct typing for model manager
        objects: Any = getattr(model, "objects", None)
        if not isinstance(objects, Manager):
            return "Error: Model does not have a valid objects manager"

        # Get the instance
        try:
            instance = objects.get(pk=instance_id)
            # Execute the action
            result = action(None, None, [instance])
            if result is not None:
                return str(result)
            return f"Admin action '{action_name}' executed successfully on {verbose_name} {instance_id}"
        except Exception as e:
            return f"Error executing admin action: {e!s}"

    # Rename to avoid collisions
    admin_action_tool.__name__ = f"admin_{model_name}_{action_name_slug}"


def register_admin_site(admin_site: AdminSite, **_kwargs: Any) -> None:
    """
    Register tools for a Django admin site.

    Args:
        admin_site: Django admin site instance
        **_kwargs: Additional kwargs (not used)
    """
    # Create tools for model counts
    try:
        mcp_server = get_mcp_server()
    except Exception:
        # Server not initialized yet
        return

    # Register a tool to get admin model information
    @mcp_server.tool(description="Get admin model information")
    def admin_models() -> list[dict[str, Any]]:
        """
        Get information about all models registered in the admin.

        Returns:
            List of models with their admin URLs and counts
        """
        result = []

        for model, model_admin in get_admin_site_registry(admin_site).items():
            model_info = {
                "app_label": get_app_label(model),
                "model_name": get_model_name(model),
                "verbose_name": str(get_verbose_name(model)),
                "verbose_name_plural": str(get_verbose_name_plural(model)),
                "admin_url": f"/admin/{get_app_label(model)}/{get_model_name(model)}/",
                "count": model.objects.count(),
                "actions": [
                    {
                        "name": getattr(action, "short_description", action.__name__.replace("_", " ").lower()),
                        "method": action.__name__,
                    }
                    for action in getattr(model_admin, "actions", [])
                ],
                "list_display": getattr(model_admin, "list_display", ["__str__"]),
                "search_fields": getattr(model_admin, "search_fields", []),
                "list_filter": getattr(model_admin, "list_filter", []),
            }
            result.append(model_info)

        return sorted(result, key=lambda x: f"{x['app_label']}.{x['model_name']}")

    # Also register as a resource
    @mcp_server.resource("admin://models")
    def admin_models_resource() -> str:
        """
        Get information about all models registered in the admin.

        Returns:
            Markdown representation of admin models
        """
        models_info = admin_models()

        # Format as Markdown
        result = [
            "# Django Admin Models",
            "",
            "This resource provides information about all models in the Django admin.",
            "",
        ]

        for model_info in models_info:
            result.append(f"## {model_info['verbose_name_plural']}")
            result.append("")
            result.append(f"- **App**: {model_info['app_label']}")
            result.append(f"- **Model**: {model_info['model_name']}")
            result.append(f"- **Count**: {model_info['count']}")
            result.append(f"- **Admin URL**: {model_info['admin_url']}")
            result.append("")

        return "\n".join(result)


def register_admin_resource(
    model: type[Model],
    admin_class: type[ModelAdmin] | None = None,
    prefix: str | None = None,
    **kwargs: Any,
) -> None:
    """
    Register an MCP resource for admin configuration.

    This creates a resource that provides configuration data about the admin for a model.

    Args:
        model: Django model class
        admin_class: Optional ModelAdmin class (will be discovered if not provided)
        prefix: Optional prefix for the resource name
        **kwargs: Additional kwargs for resource registration
    """
    import json

    mcp_server = get_mcp_server()

    # Get model info
    model_name = get_model_name(model)
    app_label = get_app_label(model)
    verbose_name = get_verbose_name(model)

    # Create prefix if not provided
    if prefix is None:
        prefix = f"{app_label}_{model_name}"

    # Get admin class from registry if not provided
    if admin_class is None:
        admin_sites = get_available_admin_sites()

        # Look for our model in each admin site
        for site in admin_sites:
            registry = get_admin_site_registry(site)
            if model in registry:
                admin_class = registry[model].__class__
                break

    # URI template for this resource
    uri_template = kwargs.pop("uri_template", None) or f"admin://{app_label}/{model_name}/config"

    @mcp_server.resource(uri_template, **kwargs)
    def get_admin_configuration() -> str:
        """
        Get admin configuration for this model.

        Returns:
            JSON string with admin configuration
        """
        # Base configuration
        config: dict[str, Any] = {
            "model": {
                "name": model_name,
                "app_label": app_label,
                "verbose_name": str(verbose_name),
            },
            "admin": {},
            "stats": {},
        }

        # Add admin class information if available
        if admin_class:
            # Extract common admin options
            admin_config: dict[str, Any] = {}

            # List display
            if hasattr(admin_class, "list_display"):
                admin_config["list_display"] = list(admin_class.list_display)

            # List filter
            if hasattr(admin_class, "list_filter"):
                # Handle various types of list_filter items (strings, tuples, custom filters)
                filters: list[str] = []
                for item in admin_class.list_filter:
                    # Just store the name/string representation
                    filters.append(str(item))
                admin_config["list_filter"] = filters

            # Search fields
            if hasattr(admin_class, "search_fields"):
                admin_config["search_fields"] = list(admin_class.search_fields)

            config["admin"] = admin_config

        # Add model count
        # Use correct typing for model manager
        objects: Any = getattr(model, "objects", None)
        try:
            if isinstance(objects, Manager):
                count = objects.count()
                config["stats"]["count"] = str(count)  # Convert to string
            else:
                config["stats"]["error"] = "Could not access model manager"
        except Exception as e:
            config["stats"]["error"] = str(e)

        # Return as JSON
        return json.dumps(config)
