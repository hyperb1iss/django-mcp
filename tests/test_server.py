from unittest.mock import MagicMock, patch

import pytest

from django_mcp.server import get_mcp_server, get_sse_app, reset_mcp_server


@pytest.mark.asyncio
async def test_get_mcp_server():
    """Test that get_mcp_server returns a FastMCP instance."""
    # Reset the server first to ensure we're creating a new one
    reset_mcp_server()

    # Just use the real implementation and verify it works
    server = get_mcp_server(name="Test Server")

    # Server should exist
    assert server is not None
    assert server.name == "Test Server"


@pytest.mark.asyncio
async def test_get_mcp_server_singleton():
    """Test that get_mcp_server returns the same instance on subsequent calls."""
    # This test can use the real implementation
    reset_mcp_server()

    server1 = get_mcp_server(name="Test Server")
    server2 = get_mcp_server()

    assert server1 is server2


@pytest.mark.asyncio
async def test_get_sse_app():
    """Test that get_sse_app returns the SSE application from the MCP server."""
    mock_server = MagicMock()
    mock_sse_app = MagicMock()
    mock_server.get_sse_app.return_value = mock_sse_app

    with patch("django_mcp.server.get_mcp_server", return_value=mock_server):
        sse_app = get_sse_app()

        assert sse_app == mock_sse_app
        mock_server.get_sse_app.assert_called_once()


def test_reset_mcp_server():
    """Test that reset_mcp_server resets the server instance."""
    # Initialize the server
    server1 = get_mcp_server(name="Test Server")

    # Reset it
    reset_mcp_server()

    # Get a new instance
    server2 = get_mcp_server(name="Test Server 2")

    # Should be different instances
    assert server1 is not server2


def test_server_settings():
    """Test that server is initialized with settings values when provided."""
    # Reset the server first
    reset_mcp_server()

    # Mock settings with our test values
    with patch("django_mcp.server.settings") as mock_settings:
        mock_settings.DJANGO_MCP_SERVER_NAME = "Settings Server"
        mock_settings.DJANGO_MCP_INSTRUCTIONS = "Settings Instructions"
        mock_settings.DJANGO_MCP_DEPENDENCIES = ["dep1", "dep2"]

        # Get server, which should use our mocked settings
        server = get_mcp_server()

        # Verify settings were used
        assert server.name == "Settings Server"
        assert server.instructions == "Settings Instructions"
        assert "dep1" in server.dependencies
        assert "dep2" in server.dependencies
