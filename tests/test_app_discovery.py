from unittest.mock import MagicMock, patch

from django_mcp.apps import DjangoMCPConfig


def test_app_config_ready_skips_management_commands():
    """Test that app config ready() skips initialization for management commands."""
    # Skip the path validation by patching _path_from_module
    with patch("django.apps.config.AppConfig._path_from_module", return_value="/fake/path"):
        app_config = DjangoMCPConfig("django_mcp", MagicMock())

        with (
            patch("sys.argv", ["manage.py", "makemigrations"]),
            patch.object(app_config, "initialize_mcp_server") as mock_init,
        ):
            app_config.ready()

            # Should not initialize MCP server for management commands
            mock_init.assert_not_called()


def test_app_config_ready_initializes_for_runserver():
    """Test that app config ready() initializes MCP for runserver command."""
    # Skip the path validation by patching _path_from_module
    with patch("django.apps.config.AppConfig._path_from_module", return_value="/fake/path"):
        app_config = DjangoMCPConfig("django_mcp", MagicMock())

        # Force auto-discover to be called
        with (
            patch.object(app_config, "_should_skip_initialization", return_value=False),
            patch.object(app_config, "_should_auto_discover", return_value=True),
            patch("sys.argv", ["manage.py", "runserver"]),
            patch.object(app_config, "initialize_mcp_server") as mock_init,
            patch.object(app_config, "auto_discover_mcp_components") as mock_discover,
            patch("os.environ.get", return_value=None),
        ):
            app_config.ready()

            # Should initialize MCP server for runserver
            mock_init.assert_called_once()
            mock_discover.assert_called_once()


def test_app_config_initializes_mcp_server():
    """Test that app config initializes MCP server with settings."""
    # Skip the path validation by patching _path_from_module
    with patch("django.apps.config.AppConfig._path_from_module", return_value="/fake/path"):
        app_config = DjangoMCPConfig("django_mcp", MagicMock())

        # Patch the imported get_mcp_server at the module level
        with patch("django_mcp.apps.get_mcp_server") as mock_get_server:
            mock_server = MagicMock()
            mock_get_server.return_value = mock_server

            app_config.initialize_mcp_server()

            # Should get MCP server
            mock_get_server.assert_called_once()

            # Should store MCP server in app_config
            assert app_config.mcp_server == mock_server


def test_app_config_auto_discovers_mcp_components():
    """Test that app config auto-discovers MCP components in installed apps."""
    # Skip the path validation by patching _path_from_module
    with patch("django.apps.config.AppConfig._path_from_module", return_value="/fake/path"):
        app_config = DjangoMCPConfig("django_mcp", MagicMock())

        # Test that auto_discover_mcp_components calls the correct methods
        with patch.object(app_config, "_import_mcp_module") as mock_import_method:
            app_config.auto_discover_mcp_components()

            # Check that _import_mcp_module was called multiple times
            assert mock_import_method.call_count > 0
