"""
DRF integration for Django-MCP.

This module provides functionality for exposing Django REST Framework
API endpoints as MCP tools and resources.
"""

import contextlib
import logging
from typing import Any

# Import ViewSet conditionally since DRF might not be installed
try:
    from rest_framework.response import Response
    from rest_framework.viewsets import ViewSet

    DRF_AVAILABLE = True
except ImportError:
    # Create dummy classes for type checking
    class ViewSet:
        pass

    class Response:
        @property
        def data(self):
            return {}

    DRF_AVAILABLE = False

from django_mcp.inspection import get_model_verbose_name_title, get_verbose_name
from django_mcp.server import get_mcp_server


def register_drf_viewset(viewset_class: Any, **_kwargs: Any) -> None:
    """
    Register tools for a DRF ViewSet class.

    Args:
        viewset_class: DRF ViewSet class
        **_kwargs: Additional kwargs for tool registration (unused)
    """
    # Skip if DRF is not available
    if not DRF_AVAILABLE:
        logging.debug("DRF not available, skipping ViewSet registration")
        return

    # Skip if not a ViewSet
    try:
        if not issubclass(viewset_class, ViewSet):
            logging.debug(f"{viewset_class} is not a ViewSet, skipping")
            return
    except TypeError:
        # Handle case where viewset_class is not actually a class (e.g. in tests)
        logging.debug(f"{viewset_class} is not a class, skipping")
        return

    try:
        mcp_server = get_mcp_server()
    except Exception:
        # Server not initialized yet
        return

    # Get model name from queryset if available
    model_name = "resource"
    if hasattr(viewset_class, "queryset") and viewset_class.queryset is not None:
        if hasattr(viewset_class.queryset, "model") and viewset_class.queryset.model is not None:
            model = viewset_class.queryset.model
            with contextlib.suppress(AttributeError, TypeError):
                model_name = get_verbose_name(model)

    # Map HTTP methods to actions
    actions = getattr(
        viewset_class,
        "action_map",
        {"get": "retrieve", "post": "create", "put": "update", "patch": "partial_update", "delete": "destroy"},
    )

    # Skip head and options
    skip_methods = {"head", "options"}

    # Register a tool for each action
    for method, action in actions.items():
        if method.lower() in skip_methods:
            continue

        # Get parameters for the action
        _get_parameters_for_action(viewset_class, action, method)

        # Create the tool function
        @mcp_server.tool(
            description=f"API action: {action} {model_name}", name=f"api_{model_name.replace(' ', '_')}_{action}"
        )
        def drf_action_tool(
            _method: str = method, _action: str = action, _viewset_class: Any = viewset_class, **params: Any
        ) -> Any:
            """
            Execute a DRF ViewSet action.

            Args:
                _method: HTTP method
                _action: ViewSet action
                _viewset_class: ViewSet class
                **params: Action parameters
            """
            # Create viewset instance
            try:
                viewset = _viewset_class()
            except Exception as e:
                return {"error": f"Failed to instantiate ViewSet: {e!s}"}

            # Get the action method
            action_method = getattr(viewset, _action, None)
            if not action_method:
                return {"error": f"Action {_action} not found on ViewSet"}

            # Create request object
            request = _create_request(_method)

            # Add parameters to request
            request.data = params
            request.query_params = params

            # Execute the action
            try:
                response = action_method(request, **params)

                # Handle Response objects
                if hasattr(response, "data"):
                    return response.data

                return response
            except Exception as e:
                return {"error": f"Error executing action: {e!s}"}


def register_serializer_resource(
    serializer_class: Any, uri_template: str, lookup_field: str = "pk", **kwargs: Any
) -> None:
    """
    Register a DRF serializer as an MCP resource.

    Args:
        serializer_class: DRF Serializer class
        uri_template: URI template for the resource
        lookup_field: Field to use for lookup (default: 'pk')
        **kwargs: Additional kwargs for resource registration
    """
    # Skip if DRF is not available
    if not DRF_AVAILABLE:
        logging.debug("DRF not available, skipping Serializer registration")
        return

    try:
        mcp_server = get_mcp_server()
    except Exception:
        # Server not initialized yet
        return

    # Get model class from serializer if available
    model_class = None
    if hasattr(serializer_class, "Meta") and hasattr(serializer_class.Meta, "model"):
        model_class = serializer_class.Meta.model

    @mcp_server.resource(uri_template, **kwargs)
    def get_serializer_resource(**kwargs: Any) -> str:
        """
        Get a serialized resource.

        Args:
            **kwargs: Lookup parameters

        Returns:
            Markdown representation of the serialized resource
        """
        # Get lookup value
        lookup_value = kwargs.get(lookup_field)
        if not lookup_value:
            return "# Error\n\nLookup field not provided."

        # If we have a model class, get the instance
        if model_class:
            try:
                instance = model_class.objects.get(**{lookup_field: lookup_value})
                serializer = serializer_class(instance)

                # Format as Markdown
                verbose_name_title = get_model_verbose_name_title(model_class)
                md_lines = [f"# {verbose_name_title}: {instance}", "", "## Serialized Data", ""]

                # Add serialized fields
                for field, value in serializer.data.items():
                    md_lines.append(f"- **{field}**: {value}")

                return "\n".join(md_lines)
            except model_class.DoesNotExist:
                return f"# Not Found\n\nThe resource with {lookup_field}={lookup_value} does not exist."
            except Exception as e:
                return f"# Error\n\nError retrieving resource: {e!s}"
        else:
            return "# Error\n\nNo model class available for this serializer."


def _get_parameters_for_action(_viewset_class: Any, action: str, _method: str) -> list[dict[str, Any]]:
    """
    Get parameters for a DRF action.

    Args:
        _viewset_class: DRF ViewSet class (unused)
        action: Action name
        _method: HTTP method (unused)

    Returns:
        List of parameter descriptions
    """
    # This is a simplified version - in a real implementation, we would
    # inspect the serializer and action method to determine parameters

    # Default parameters for common actions
    if action == "list":
        return [
            {"name": "page", "description": "Page number for pagination", "required": False, "type": "integer"},
            {"name": "limit", "description": "Number of results per page", "required": False, "type": "integer"},
        ]
    elif action == "retrieve":
        return [
            {"name": "id", "description": "ID of the resource to retrieve", "required": True, "type": "integer"},
        ]
    elif action in {"update", "partial_update"}:
        return [
            {"name": "id", "description": "ID of the resource to update", "required": True, "type": "integer"},
            # Fields would be added dynamically in a real implementation
        ]
    elif action == "destroy":
        return [
            {"name": "id", "description": "ID of the resource to delete", "required": True, "type": "integer"},
        ]

    # Default - empty parameters
    return []


def _create_request(method: str) -> Any:
    """
    Create a fake request object for DRF actions.

    Args:
        method: HTTP method

    Returns:
        A minimal Request object
    """

    # Create a minimal request object
    class FakeRequest:
        def __init__(self, method):
            self.method = method.upper()
            self.data = {}
            self.query_params = {}
            self.META = {"SCRIPT_NAME": "", "PATH_INFO": "/"}

    return FakeRequest(method)
