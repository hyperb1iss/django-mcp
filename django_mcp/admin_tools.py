"""
Django admin integration utilities for Django-MCP.

This module provides functions for exposing Django admin functionality as MCP tools and resources.
"""

from typing import Any

from django.contrib.admin import AdminSite
from django.contrib.admin.options import ModelAdmin
from django.db.models import Model

from django_mcp.api_inspection import get_admin_site_registry
from django_mcp.inspection import (
    get_app_label,
    get_model_name,
    get_verbose_name,
    get_verbose_name_plural,
)
from django_mcp.server import get_mcp_server


def register_admin_tools(
    admin_class: type[ModelAdmin], model: type[Model], exclude_actions: list[str] | None = None, **_kwargs: Any
) -> None:
    """
    Register tools for a Django admin model.

    This function adds tools that correspond to admin actions for a model.

    Args:
        admin_class: The ModelAdmin class
        model: Django model class
        exclude_actions: Optional list of actions to exclude
        **_kwargs: Additional kwargs (not used)
    """
    try:
        get_mcp_server()
    except Exception:
        # Server not initialized yet
        return

    # Get model info
    model_name = get_model_name(model)
    verbose_name = get_verbose_name(model)

    # Get admin actions
    actions = getattr(admin_class, "actions", [])
    if exclude_actions is None:
        exclude_actions = []

    for action in actions:
        if action in exclude_actions:
            continue

        # Get action details
        action_name = getattr(action, "short_description", action.__name__.replace("_", " ").lower())
        action_name_slug = action.__name__

        # Register as MCP tool
        _register_admin_action_tool(
            model=model,
            model_name=model_name,
            verbose_name=verbose_name,
            action=action,
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
    """Register an admin action as an MCP tool."""
    try:
        mcp_server = get_mcp_server()
    except Exception:
        # Server not initialized yet
        return

    @mcp_server.tool(description=f"Execute admin '{action_name}' action on {verbose_name}")
    def admin_action_tool(id: int) -> str:
        """
        Execute an admin action on a model instance.

        Args:
            id: Instance ID to operate on

        Returns:
            Result of the action
        """
        # Get the instance
        try:
            instance = model.objects.get(pk=id)
            # Execute the action
            result = action(None, None, [instance])
            if result:
                return result
            return f"Admin action '{action_name}' executed successfully on {verbose_name} {id}"
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
    Register a resource that provides information about a model's admin configuration.

    Args:
        model: Django model class
        admin_class: Optional ModelAdmin class
        prefix: Optional prefix for the resource URI
        **kwargs: Additional kwargs for resource registration
    """
    try:
        mcp_server = get_mcp_server()
    except Exception:
        # Server not initialized yet
        return

    # Get model info
    app_label = get_app_label(model)
    model_name = get_model_name(model)

    # Create resource URI template
    if prefix:
        uri_template = f"{prefix}admin://{app_label}/{model_name}"
    else:
        uri_template = f"admin://{app_label}/{model_name}"

    # Register resource
    @mcp_server.resource(uri_template, **kwargs)
    def get_admin_configuration() -> str:
        """
        Get admin configuration for a model.

        Returns:
            Markdown representation of admin configuration
        """
        # Format as Markdown for better LLM consumption
        result = [
            f"# Admin for {get_verbose_name_plural(model)}",
            "",
            f"This resource describes the admin configuration for {get_verbose_name_plural(model)}.",
            "",
            "## Display Configuration",
            "",
        ]

        if admin_class:
            # Add admin configuration
            if hasattr(admin_class, "list_display"):
                result.append("### List Display")
                result.append("")
                for field in admin_class.list_display:
                    result.append(f"- {field}")
                result.append("")

            if hasattr(admin_class, "list_filter"):
                result.append("### List Filters")
                result.append("")
                for field in admin_class.list_filter:
                    result.append(f"- {field}")
                result.append("")

            if hasattr(admin_class, "search_fields"):
                result.append("### Search Fields")
                result.append("")
                for field in admin_class.search_fields:
                    result.append(f"- {field}")
                result.append("")

        # Add model count
        count = model.objects.count()
        result.append("")
        result.append(f"Total {get_verbose_name_plural(model)}: {count}")

        return "\n".join(result)
