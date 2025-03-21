"""
Admin integration for Django-MCP.

This module provides functionality for exposing Django admin actions
and functionality as MCP tools and resources.
"""

from typing import Any

from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.sites import AdminSite
from django.db.models import Model
from django.http import HttpRequest

from django_mcp.server import get_mcp_server


def register_admin_tools(
    admin_class: type[ModelAdmin], model: type[Model], exclude_actions: list[str] | None = None, **kwargs: Any
) -> None:
    """
    Register tools for Django admin actions for a model.

    Args:
        admin_class: ModelAdmin class
        model: Django model class
        exclude_actions: Optional list of actions to exclude
        **kwargs: Additional kwargs for tool registration
    """
    try:
        mcp_server = get_mcp_server()
    except Exception:
        # Server not initialized yet
        return

    # Get model info
    model_name = model._meta.model_name
    verbose_name = model._meta.verbose_name

    # Get admin actions
    actions = getattr(admin_class, "actions", [])
    if exclude_actions is None:
        exclude_actions = ["delete_selected"]  # Exclude delete by default for safety

    # Register a tool for each action
    for action_name in actions:
        # Skip excluded actions
        if action_name in exclude_actions:
            continue

        # Get the action
        action = getattr(admin_class, action_name)

        # Get action description
        description = getattr(action, "short_description", action_name.replace("_", " ").title())

        # Create the tool function
        @mcp_server.tool(description=f"Admin action: {description} for {verbose_name}")
        def admin_action_tool(
            ids: list[int],
            _action_name: str = action_name,
            _model: type[Model] = model,
            _admin_class: type[ModelAdmin] = admin_class,
        ) -> dict[str, Any]:
            """
            Execute admin action on selected objects.

            Args:
                ids: List of object IDs to act upon
            """
            # Get action function (bound to admin class)
            admin_instance = _admin_class(model=_model, admin_site=AdminSite())
            action_func = getattr(admin_instance, _action_name)

            # Get QuerySet of objects
            queryset = _model.objects.filter(pk__in=ids)

            # Create fake request (needed by many admin actions)
            request = _create_fake_request()

            # Execute the action
            response = action_func(request, queryset)

            return {
                "success": True,
                "action": _action_name,
                "affected_count": queryset.count(),
                "result": str(response) if response else "Action executed successfully",
            }

        # Rename the function to avoid name collisions
        admin_action_tool.__name__ = f"admin_{model_name}_{action_name}"


def register_admin_site(admin_site: AdminSite, **kwargs: Any) -> None:
    """
    Register tools for a Django admin site.

    This creates more general admin tools, such as listing
    all models or accessing admin views.

    Args:
        admin_site: Django AdminSite instance
        **kwargs: Additional kwargs for tool registration
    """
    try:
        mcp_server = get_mcp_server()
    except Exception:
        # Server not initialized yet
        return

    # Register tool to list all models in admin
    @mcp_server.tool(description="List all models in the admin site")
    def list_admin_models() -> list[dict[str, Any]]:
        """
        List all models available in the admin site.
        """
        result = []

        for model, model_admin in admin_site._registry.items():
            model_info = {
                "app_label": model._meta.app_label,
                "model_name": model._meta.model_name,
                "verbose_name": str(model._meta.verbose_name),
                "verbose_name_plural": str(model._meta.verbose_name_plural),
                "admin_url": f"/admin/{model._meta.app_label}/{model._meta.model_name}/",
                "count": model.objects.count(),
                "actions": [
                    {
                        "name": action_name,
                        "description": getattr(
                            getattr(model_admin, action_name, None),
                            "short_description",
                            action_name.replace("_", " ").title(),
                        ),
                    }
                    for action_name in getattr(model_admin, "actions", [])
                    if action_name != "delete_selected"  # Skip delete for safety
                ],
            }
            result.append(model_info)

        return result


def register_admin_model_resource(admin_class: type[ModelAdmin], model: type[Model], **kwargs: Any) -> None:
    """
    Register a resource for an admin model.

    This creates a resource that returns the model's admin metadata,
    including available fields, list display, and actions.

    Args:
        admin_class: ModelAdmin class
        model: Django model class
        **kwargs: Additional kwargs for resource registration
    """
    try:
        mcp_server = get_mcp_server()
    except Exception:
        # Server not initialized yet
        return

    # Get model info
    app_label = model._meta.app_label
    model_name = model._meta.model_name

    # Create resource URI template
    uri_template = f"admin://{app_label}/{model_name}"

    @mcp_server.resource(uri_template, **kwargs)
    def get_admin_model_resource() -> str:
        """
        Get admin metadata for a model.
        """
        # Create instance of admin class
        admin_instance = admin_class(model=model, admin_site=AdminSite())

        # Get admin metadata
        list_display = getattr(admin_instance, "list_display", ("__str__",))
        list_filter = getattr(admin_instance, "list_filter", ())
        search_fields = getattr(admin_instance, "search_fields", ())
        actions = getattr(admin_instance, "actions", [])

        # Format as Markdown for better LLM consumption
        result = [
            f"# Admin for {model._meta.verbose_name_plural}",
            "",
            f"This resource describes the admin configuration for {model._meta.verbose_name_plural}.",
            "",
            "## Display Configuration",
            "",
            f"- **List Display**: {', '.join(list_display)}",
            f"- **List Filter**: {', '.join(list_filter)}",
            f"- **Search Fields**: {', '.join(search_fields)}",
            "",
            "## Available Actions",
            "",
        ]

        # Add actions
        for action_name in actions:
            action = getattr(admin_instance, action_name, None)
            if action:
                description = getattr(action, "short_description", action_name.replace("_", " ").title())
                result.append(f"- **{action_name}**: {description}")

        # Add model count
        count = model.objects.count()
        result.append("")
        result.append(f"Total {model._meta.verbose_name_plural}: {count}")

        return "\n".join(result)


def _create_fake_request() -> HttpRequest:
    """
    Create a fake HTTP request for admin actions.

    Many admin actions require a request object, so we create a minimal one.

    Returns:
        A minimal HttpRequest object
    """
    from django.contrib.auth.models import AnonymousUser
    from django.http import HttpRequest

    request = HttpRequest()
    request.user = AnonymousUser()
    request.META = {"SCRIPT_NAME": "", "PATH_INFO": "/"}

    return request
