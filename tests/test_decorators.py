from unittest.mock import MagicMock, patch

from django_mcp.decorators import mcp_model_resource, mcp_model_tool, mcp_prompt, mcp_resource, mcp_tool


def test_mcp_tool_decorator(mock_mcp_server):
    """Test that mcp_tool decorator registers a function as an MCP tool."""

    @mcp_tool(description="Test tool")
    def test_func(arg1, arg2):
        return arg1 + arg2

    # Should register the tool with the MCP server
    mock_mcp_server.tool.assert_called_once_with(description="Test tool", name=None)

    # Original function should be preserved
    assert test_func(1, 2) == 3


def test_mcp_tool_with_no_server():
    """Test that mcp_tool decorator handles case when server isn't available."""
    with patch("django_mcp.decorators.get_mcp_server", side_effect=Exception("Server not available")):

        @mcp_tool(description="Test tool")
        def test_func(arg1, arg2):
            return arg1 + arg2

        # Original function should be preserved even without server
        assert test_func(1, 2) == 3


def test_mcp_resource_decorator(mock_mcp_server):
    """Test that mcp_resource decorator registers a function as an MCP resource."""

    @mcp_resource(uri_template="test://{id}", description="Test resource")
    def test_func(resource_id):
        return f"Resource {resource_id}"

    # Should register the resource with the MCP server
    mock_mcp_server.resource.assert_called_once_with("test://{id}", description="Test resource")

    # Original function should be preserved
    assert test_func(123) == "Resource 123"


def test_mcp_prompt_decorator(mock_mcp_server):
    """Test that mcp_prompt decorator registers a function as an MCP prompt."""

    @mcp_prompt(name="test_prompt", description="Test prompt")
    def test_func(context):
        return f"Prompt with {context}"

    # Should register the prompt with the MCP server
    mock_mcp_server.prompt.assert_called_once_with(name="test_prompt", description="Test prompt")

    # Original function should be preserved
    assert test_func("context") == "Prompt with context"


def test_mcp_model_tool_decorator(mock_mcp_server):
    """Test that mcp_model_tool decorator registers Django model tools."""
    with patch("django_mcp.model_tools.register_model_tools") as mock_register:

        @mcp_model_tool(model=MagicMock())
        def test_func():
            return "Model tool registered"

        # Should call register_model_tools
        mock_register.assert_called_once()

        # Original function should be preserved
        assert test_func() == "Model tool registered"


def test_mcp_model_resource_decorator(mock_mcp_server):
    """Test that mcp_model_resource decorator registers a Django model as an MCP resource."""
    mock_model = MagicMock()

    with patch("django_mcp.model_tools.register_model_resource") as mock_register:

        @mcp_model_resource(model=mock_model, lookup="slug", fields=["name", "description"])
        def test_func():
            return "Model resource registered"

        # Should call register_model_resource with correct args - check only specific args
        mock_register.assert_called_once()
        args, kwargs = mock_register.call_args
        assert args[1] == "slug"  # Check the lookup parameter
        assert args[2] == ["name", "description"]  # Check the fields parameter

        # Original function should be preserved
        assert test_func() == "Model resource registered"
