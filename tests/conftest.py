import os
from unittest.mock import MagicMock, patch

import django
from django.conf import settings
from django.test import RequestFactory
import pytest


def pytest_configure():
    """Configure Django settings for tests."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

    # Initialize Django if not already set up
    if not settings.configured:
        django.setup()


@pytest.fixture
def mock_mcp_server():
    """Create a mock MCP server for testing."""

    # Define decorator factories that return the decorated function directly
    def mock_tool_decorator(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def mock_resource_decorator(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def mock_prompt_decorator(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    # Create the mock server with the decorators as attributes
    mock_server = MagicMock()
    mock_server.tool = MagicMock(side_effect=mock_tool_decorator)
    mock_server.resource = MagicMock(side_effect=mock_resource_decorator)
    mock_server.prompt = MagicMock(side_effect=mock_prompt_decorator)

    # Create a patch context for get_mcp_server
    with (
        patch("django_mcp.server.get_mcp_server", return_value=mock_server),
        patch("django_mcp.decorators.get_mcp_server", return_value=mock_server),
        patch("django_mcp.model_tools.get_mcp_server", return_value=mock_server),
        patch("django_mcp.drf_tools.get_mcp_server", return_value=mock_server),
    ):
        yield mock_server


@pytest.fixture
def request_factory():
    """Create a RequestFactory instance."""
    return RequestFactory()


@pytest.fixture
def test_model():
    """Create a simple test model for testing."""
    from django.db import models

    class TestModel(models.Model):
        name = models.CharField(max_length=100)
        description = models.TextField(blank=True)

        def __str__(self):
            return str(self.name)

        class Meta:
            app_label = "tests"
            # Ensure model isn't actually created
            abstract = True

    return TestModel


@pytest.fixture
def async_client():
    """Create an async test client."""
    from starlette.testclient import TestClient

    return TestClient
