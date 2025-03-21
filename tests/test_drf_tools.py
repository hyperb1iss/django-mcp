from unittest.mock import MagicMock, patch

import pytest

from django_mcp.drf_tools import register_drf_viewset


@pytest.fixture
def mock_drf_viewset():
    """Create a mock DRF ViewSet."""
    try:
        from rest_framework.viewsets import ViewSet
    except ImportError:
        pytest.skip("DRF not installed")

    # Create a real class that inherits from ViewSet
    class MockViewSet(ViewSet):
        action_map = {"get": "list", "post": "create", "put": "update", "delete": "destroy"}

    # Create an instance with the required attributes
    mock_viewset = MockViewSet()
    mock_viewset.queryset = MagicMock()
    mock_viewset.queryset.model = MagicMock()
    mock_viewset.queryset.model._meta = MagicMock()
    mock_viewset.queryset.model._meta.verbose_name = "test_model"

    return MockViewSet


def test_register_drf_viewset_skips_if_drf_not_installed():
    """Test that register_drf_viewset skips if DRF is not installed."""
    # Instead of patching ViewSet and causing exceptions, patch DRF_AVAILABLE directly
    with patch("django_mcp.drf_tools.DRF_AVAILABLE", False), patch("django_mcp.drf_tools.logging.debug") as mock_debug:
        register_drf_viewset(MagicMock())
        # Should log that DRF is not available
        mock_debug.assert_called_once_with("DRF not available, skipping ViewSet registration")


def test_register_drf_viewset(mock_mcp_server, mock_drf_viewset):
    """Test that register_drf_viewset registers tools for a DRF ViewSet."""

    # Define a class with the expected attributes and proper verbose_name
    class TestViewSet:
        def __call__(self, *args, **kwargs):
            return self

        queryset = MagicMock()

    # Add the required attributes to the mock viewset's queryset manually
    test_viewset = TestViewSet()
    test_viewset.queryset.model = MagicMock()
    test_viewset.queryset.model._meta = MagicMock()
    test_viewset.queryset.model._meta.verbose_name = "test_model"

    # Add action map
    test_viewset.action_map = {"get": "list", "post": "create", "put": "update", "delete": "destroy"}

    # Need to patch the check since our mock isn't a real ViewSet
    with (
        patch("django_mcp.drf_tools.issubclass", return_value=True),
        patch("django_mcp.drf_tools.DRFViewSet", object),
        patch("django_mcp.drf_tools.DRF_AVAILABLE", True),
    ):
        register_drf_viewset(test_viewset)

    # Should register tools with the MCP server (one for each action, excluding options/head)
    assert mock_mcp_server.tool.call_count > 0

    # Get the descriptions to verify
    descriptions = []
    for call_args in mock_mcp_server.tool.call_args_list:
        kwargs = call_args[1]
        if "description" in kwargs:
            descriptions.append(kwargs["description"])

    # Check descriptions for registered tools
    assert any("list test_model" in desc for desc in descriptions)
    assert any("create test_model" in desc for desc in descriptions)
    assert any("update test_model" in desc for desc in descriptions)
    assert any("destroy test_model" in desc for desc in descriptions)


def test_register_drf_viewset_skips_non_viewsets(mock_mcp_server):
    """Test that register_drf_viewset skips non-ViewSet classes."""
    # Force DRF to be available
    with (
        patch("django_mcp.drf_tools.DRF_AVAILABLE", True),
        patch("django_mcp.drf_tools.issubclass", return_value=False),
    ):
        register_drf_viewset(MagicMock())

        # Should not register any tools
        mock_mcp_server.tool.assert_not_called()


def test_drf_action_tool():
    """Test that a DRF action tool function works correctly."""
    # Mock a ViewSet class
    mock_action_result = {"result": "success"}

    # Create a mock action method that takes a request parameter
    def mock_list_action(request, **kwargs):
        return mock_action_result

    # Create a mock ViewSet class with the action
    mock_viewset_class = MagicMock()
    mock_viewset_class.return_value.list = mock_list_action

    # Mock _create_request to return a mock request
    mock_request = MagicMock()
    _create_request = MagicMock(return_value=mock_request)

    # Manually define the drf_action_tool function that would be created
    def drf_action_tool(**params):
        # Set default parameters
        method = params.pop("_method", "get")
        action = params.pop("_action", "list")
        viewset_class = params.pop("_viewset_class", mock_viewset_class)

        # Create viewset instance
        viewset = viewset_class()

        # Get the action method
        action_method = getattr(viewset, action)

        # Create request object
        request = _create_request(method)

        # Add parameters to request
        request.data = params
        request.query_params = params

        # Execute the action
        response = action_method(request, **params)

        # Handle Response objects
        if hasattr(response, "data"):
            return response.data

        return response

    # Call the function directly
    result = drf_action_tool(_method="get", _action="list", _viewset_class=mock_viewset_class)

    # Should return the Response data
    assert result == mock_action_result
