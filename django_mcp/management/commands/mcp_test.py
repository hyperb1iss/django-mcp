"""
Django management command for testing MCP components.

This command allows you to invoke tools and prompts directly from the command line.
"""
# pylint: disable=duplicate-code

from argparse import ArgumentParser
import asyncio
import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from mcp.server.fastmcp import Context

from django_mcp.inspection import get_prompts, get_resources, get_tools, has_prompt, has_tool, match_resource_uri
from django_mcp.server import get_mcp_server


class Command(BaseCommand):
    """Django management command to test MCP components."""

    help = "Test MCP components"

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add command line arguments."""
        subparsers = parser.add_subparsers(dest="component_type", help="Component type to test")

        # Tool subcommand
        tool_parser = subparsers.add_parser("tool", help="Test a tool")
        tool_parser.add_argument("tool_name", help="Name of the tool to test")
        tool_parser.add_argument("--params", help="JSON string of parameters to pass to the tool")
        tool_parser.add_argument("--file", help="Path to JSON file containing parameters")

        # Resource subcommand
        resource_parser = subparsers.add_parser("resource", help="Test a resource")
        resource_parser.add_argument("resource_uri", help="URI of the resource to test")

        # Prompt subcommand
        prompt_parser = subparsers.add_parser("prompt", help="Test a prompt")
        prompt_parser.add_argument("prompt_name", help="Name of the prompt to test")
        prompt_parser.add_argument("--args", help="JSON string of arguments to pass to the prompt")
        prompt_parser.add_argument("--file", help="Path to JSON file containing arguments")

        # List subcommand
        list_parser = subparsers.add_parser("list", help="List available components")
        list_parser.add_argument(
            "--type",
            choices=["tools", "resources", "prompts"],
            default="tools",
            help="Component type to list (default: tools)",
        )

    def handle(self, **options: Any) -> None:
        """
        Execute command.

        Args:
            **options: Command line options
        """
        component_type = options.get("component_type")

        if not component_type:
            raise CommandError("You must specify a component type (tool, resource, prompt, or list)")

        # Initialize MCP server
        mcp_server = get_mcp_server()
        if not mcp_server:
            raise CommandError("MCP server is not initialized")

        # Handle different component types
        if component_type == "list":
            self._handle_list(options)
        elif component_type == "tool":
            self._handle_tool(mcp_server, options)
        elif component_type == "resource":
            self._handle_resource(mcp_server, options)
        elif component_type == "prompt":
            self._handle_prompt(mcp_server, options)
        else:
            raise CommandError(f"Unknown component type: {component_type}")

    def _handle_list(self, options: dict[str, Any]) -> None:
        """
        Handle list command.

        Args:
            options: Command line options
        """
        component_type = options.get("type", "tools")

        if component_type == "tools":
            self.stdout.write("Available tools:")
            tools = get_tools()
            for tool in tools:
                self.stdout.write(f"  - {tool.get('name', 'Unknown')}")

        elif component_type == "resources":
            self.stdout.write("Available resources:")
            resources = get_resources()
            for resource in resources:
                self.stdout.write(f"  - {resource.get('uri_template', 'Unknown')}")

        elif component_type == "prompts":
            self.stdout.write("Available prompts:")
            prompts = get_prompts()
            for prompt in prompts:
                self.stdout.write(f"  - {prompt.get('name', 'Unknown')}")

    def _handle_tool(self, mcp_server: Any, options: dict[str, Any]) -> None:
        """
        Handle tool command.

        Args:
            mcp_server: MCP server instance
            options: Command line options
        """
        tool_name = options["tool_name"]

        # Check if tool exists
        if not has_tool(tool_name):
            raise CommandError(f"Tool '{tool_name}' not found")

        # Get parameters
        params: dict[str, Any] = {}
        if options.get("params"):
            try:
                params = json.loads(options["params"])
            except json.JSONDecodeError as e:
                raise CommandError(f"Invalid JSON for parameters: {e}") from e

        if options.get("file"):
            try:
                with open(options["file"], encoding="utf-8") as f:
                    params = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                raise CommandError(f"Error loading parameters from file: {e}") from e

        # Create context
        context = Context()  # type: ignore

        # Execute tool
        try:
            self.stdout.write(f"Executing tool '{tool_name}'...")
            result = None

            # Execute the tool (using getattr to avoid mypy errors)
            result = asyncio.run(mcp_server.invoke_tool(tool_name, params, context))

            # Display result
            if isinstance(result, dict | list):
                self.stdout.write(json.dumps(result, indent=2))
            else:
                self.stdout.write(str(result))

        except Exception as e:
            raise CommandError(f"Error executing tool: {e}") from e

    def _handle_resource(self, mcp_server: Any, options: dict[str, Any]) -> None:
        """
        Handle resource command.

        Args:
            mcp_server: MCP server instance
            options: Command line options
        """
        resource_uri = options["resource_uri"]

        # Check if resource exists
        resource = match_resource_uri(resource_uri)
        if not resource:
            raise CommandError(f"No resource matching URI '{resource_uri}' found")

        # Create context
        context = Context()  # type: ignore

        # Read resource
        try:
            self.stdout.write(f"Reading resource '{resource_uri}'...")
            # Execute the resource (using getattr to avoid mypy errors)
            result = asyncio.run(mcp_server.read_resource(resource_uri, context))

            # Display result
            if isinstance(result, tuple) and len(result) == 2:
                content, mime_type = result
                self.stdout.write(f"MIME type: {mime_type}")
                self.stdout.write("Content:")
                self.stdout.write(content)
            else:
                self.stdout.write(str(result))

        except Exception as e:
            raise CommandError(f"Error reading resource: {e}") from e

    def _handle_prompt(self, mcp_server: Any, options: dict[str, Any]) -> None:
        """
        Handle prompt command.

        Args:
            mcp_server: MCP server instance
            options: Command line options
        """
        prompt_name = options["prompt_name"]

        # Check if prompt exists
        if not has_prompt(prompt_name):
            raise CommandError(f"Prompt '{prompt_name}' not found")

        # Get arguments
        args: dict[str, Any] = {}
        if options.get("args"):
            try:
                args = json.loads(options["args"])
            except json.JSONDecodeError as e:
                raise CommandError(f"Invalid JSON for arguments: {e}") from e

        if options.get("file"):
            try:
                with open(options["file"], encoding="utf-8") as f:
                    args = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                raise CommandError(f"Error loading arguments from file: {e}") from e

        # Create context
        context = Context()  # type: ignore

        # Execute prompt
        try:
            self.stdout.write(f"Executing prompt '{prompt_name}'...")
            # Execute the prompt (using getattr to avoid mypy errors)
            result = asyncio.run(mcp_server.invoke_prompt(prompt_name, args, context))

            # Display result
            self.stdout.write(str(result))

        except Exception as e:
            raise CommandError(f"Error executing prompt: {e}") from e
