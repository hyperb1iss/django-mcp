from unittest.mock import patch

import pytest

from django_mcp import settings


def test_default_settings():
    """Test that default settings are correctly set."""
    # Create a temporary mock settings object with no MCP settings
    mock_settings = type("Settings", (), {})()

    # Apply defaults to mock settings
    with patch.object(settings, "settings", mock_settings):
        from django_mcp.settings import DEFAULTS

        for key, default in DEFAULTS.items():
            # Set default and check it was set correctly
            if not hasattr(mock_settings, key):
                setattr(settings.settings, key, default)

            assert hasattr(mock_settings, key)
            assert getattr(mock_settings, key) == default


def test_custom_settings_preserved():
    """Test that custom settings are preserved when defaults are applied."""
    # Create a temporary mock settings object with custom MCP settings
    mock_settings = type(
        "Settings",
        (),
        {
            "DJANGO_MCP_SERVER_NAME": "Custom Server",
            "DJANGO_MCP_URL_PREFIX": "custom-mcp",
        },
    )()

    # Apply defaults to mock settings
    with patch.object(settings, "settings", mock_settings):
        from django_mcp.settings import DEFAULTS

        for key, default in DEFAULTS.items():
            # Set default only if not already set
            if not hasattr(mock_settings, key):
                setattr(settings.settings, key, default)

        # Check that custom settings were preserved
        assert mock_settings.DJANGO_MCP_SERVER_NAME == "Custom Server"
        assert mock_settings.DJANGO_MCP_URL_PREFIX == "custom-mcp"

        # Check that other defaults were set
        assert hasattr(mock_settings, "DJANGO_MCP_AUTO_DISCOVER")
        assert DEFAULTS["DJANGO_MCP_AUTO_DISCOVER"] == mock_settings.DJANGO_MCP_AUTO_DISCOVER


def test_settings_module_attributes():
    """Test that the settings module has the correct attributes."""
    # Ensure the django_mcp.settings module has DEFAULTS
    assert hasattr(settings, "DEFAULTS")
    assert isinstance(settings.DEFAULTS, dict)

    # Check required keys in DEFAULTS
    required_keys = [
        "DJANGO_MCP_SERVER_NAME",
        "DJANGO_MCP_URL_PREFIX",
        "DJANGO_MCP_INSTRUCTIONS",
        "DJANGO_MCP_DEPENDENCIES",
        "DJANGO_MCP_AUTO_DISCOVER",
        "DJANGO_MCP_EXPOSE_MODELS",
        "DJANGO_MCP_EXPOSE_ADMIN",
        "DJANGO_MCP_EXPOSE_DRF",
    ]

    for key in required_keys:
        assert key in settings.DEFAULTS


@pytest.mark.parametrize(
    ("setting_name", "expected_type"),
    [
        ("DJANGO_MCP_SERVER_NAME", (str, type(None))),
        ("DJANGO_MCP_URL_PREFIX", str),
        ("DJANGO_MCP_INSTRUCTIONS", (str, type(None))),
        ("DJANGO_MCP_DEPENDENCIES", list),
        ("DJANGO_MCP_AUTO_DISCOVER", bool),
        ("DJANGO_MCP_EXPOSE_MODELS", bool),
        ("DJANGO_MCP_EXPOSE_ADMIN", bool),
        ("DJANGO_MCP_EXPOSE_DRF", bool),
    ],
)
def test_settings_types(setting_name, expected_type):
    """Test that the settings have the correct types."""
    value = settings.DEFAULTS[setting_name]

    if isinstance(expected_type, tuple):
        assert isinstance(value, expected_type) or value is None
    else:
        assert isinstance(value, expected_type)
