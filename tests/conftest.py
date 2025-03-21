import os
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import RequestFactory
import pytest


def pytest_configure():
    """Configure Django settings for tests."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

    # Setup Django settings if not configured
    if not settings.configured:
        settings.configure(
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
                "django.contrib.sessions",
                "django.contrib.admin",
                "django_mcp",
                "tests",
            ],
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            SECRET_KEY="django-insecure-test-key",
            ROOT_URLCONF="tests.urls",
            MIDDLEWARE=[
                "django.middleware.security.SecurityMiddleware",
                "django.contrib.sessions.middleware.SessionMiddleware",
                "django.middleware.common.CommonMiddleware",
                "django.middleware.csrf.CsrfViewMiddleware",
                "django.contrib.auth.middleware.AuthenticationMiddleware",
                "django.contrib.messages.middleware.MessageMiddleware",
            ],
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "APP_DIRS": True,
                    "OPTIONS": {
                        "context_processors": [
                            "django.template.context_processors.debug",
                            "django.template.context_processors.request",
                            "django.contrib.auth.context_processors.auth",
                            "django.contrib.messages.context_processors.messages",
                        ],
                    },
                },
            ],
            DJANGO_MCP_SERVER_NAME="Test MCP Server",
            DJANGO_MCP_AUTO_DISCOVER=False,  # Disable auto-discovery for tests
        )

        # Initialize Django
        import django

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
    with patch("django_mcp.server.get_mcp_server", return_value=mock_server):
        with patch("django_mcp.decorators.get_mcp_server", return_value=mock_server):
            with patch("django_mcp.model_tools.get_mcp_server", return_value=mock_server):
                with patch("django_mcp.drf_tools.get_mcp_server", return_value=mock_server):
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
            return self.name

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
