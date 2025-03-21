from django_mcp.decorators import mcp_prompt, mcp_resource, mcp_tool
from django_mcp.model_tools import register_model_tools

from .models import TestComment, TestPost


@mcp_tool(description="Simple test tool")
def test_tool(name: str) -> str:
    """A simple test tool that just returns a greeting."""
    return f"Hello, {name}!"


@mcp_resource(uri_template="test://greeting/{name}")
def test_resource(name: str) -> str:
    """A simple test resource that returns a greeting."""
    return f"# Greeting\n\nHello, {name}!"


@mcp_prompt(name="test_prompt")
def test_prompt(context: dict) -> str:
    """A simple test prompt that returns a greeting."""
    name = context.get("name", "User")
    return f"Hello, {name}! This is a test prompt."


# Register test models
register_model_tools(TestPost)
register_model_tools(TestComment)
