"""
Django management command for testing MCP components.

This command allows you to invoke tools and prompts directly from the command line.
"""
# pylint: disable=duplicate-code

import asyncio
import json

from django.core.management.base import BaseCommand, CommandError

from django_mcp.context import Context
from django_mcp.inspection import get_prompts, get_resources, get_tools, has_prompt, has_tool, match_resource_uri
from django_mcp.server import get_mcp_server


class Command(BaseCommand):
    """Django management command to test MCP components."""

    help = "Test MCP components"

    def add_arguments(self, parser):
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

    def handle(self, **options):
        """Execute the command."""
        try:
            mcp_server = get_mcp_server()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"MCP server not initialized: {e!s}"))
            return

        if not mcp_server:
            self.stderr.write(self.style.ERROR("MCP server not initialized"))
            return

        component_type = options.get("component_type")

        if not component_type:
            self.stderr.write(self.style.ERROR("No component type specified"))
            self.print_help("manage.py", "mcp_test")
            return

        if component_type == "list":
            self._handle_list(options)
        elif component_type == "tool":
            self._handle_tool(mcp_server, options)
        elif component_type == "resource":
            self._handle_resource(mcp_server, options)
        elif component_type == "prompt":
            self._handle_prompt(mcp_server, options)

    def _handle_list(self, options):
        """Handle listing components."""
        component_type = options.get("type", "tools")

        if component_type == "tools":
            # Use the inspection module instead of accessing private members
            tools = get_tools()
            self.stdout.write(self.style.SUCCESS(f"Available tools ({len(tools)}):"))
            for tool in tools:
                self.stdout.write(f"  - {tool.name}")

        elif component_type == "resources":
            # Use the inspection module instead of accessing private members
            resources = get_resources()
            self.stdout.write(self.style.SUCCESS(f"Available resources ({len(resources)}):"))
            for resource in resources:
                self.stdout.write(f"  - {resource.uri_template}")

        elif component_type == "prompts":
            # Use the inspection module instead of accessing private members
            prompts = get_prompts()
            self.stdout.write(self.style.SUCCESS(f"Available prompts ({len(prompts)}):"))
            for prompt in prompts:
                self.stdout.write(f"  - {prompt.name}")

    def _handle_tool(self, mcp_server, options):
        """Handle tool testing."""
        tool_name = options.get("tool_name")

        # Get parameters from either --params or --file
        params = {}
        if options.get("params"):
            try:
                params = json.loads(options.get("params"))
            except json.JSONDecodeError as err:
                raise CommandError("Invalid JSON in --params") from err
        elif options.get("file"):
            try:
                with open(options.get("file"), encoding="utf-8") as f:
                    params = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                raise CommandError(f"Error reading parameters file: {e!s}") from e

        self.stdout.write(self.style.SUCCESS(f"Testing tool: {tool_name}"))
        self.stdout.write(f"Parameters: {json.dumps(params, indent=2)}")

        # Create a context
        context = Context()

        # Check if the tool exists using the inspection module
        if not has_tool(tool_name):
            self.stderr.write(self.style.ERROR(f"Tool '{tool_name}' not found"))
            return

        # Run the tool
        try:
            if asyncio.iscoroutinefunction(mcp_server.invoke_tool):
                result = asyncio.run(mcp_server.invoke_tool(tool_name, params, context))
            else:
                result = mcp_server.invoke_tool(tool_name, params, context)

            self.stdout.write(self.style.SUCCESS("Result:"))
            if isinstance(result, dict | list):
                self.stdout.write(json.dumps(result, indent=2))
            else:
                self.stdout.write(str(result))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error invoking tool: {e!s}"))

    def _handle_resource(self, mcp_server, options):
        """Handle resource testing."""
        resource_uri = options.get("resource_uri")

        self.stdout.write(self.style.SUCCESS(f"Testing resource: {resource_uri}"))

        # Create a context
        context = Context()

        # Check if there's a resource handler for this URI using the inspection module
        resource = match_resource_uri(resource_uri)
        if not resource:
            self.stderr.write(self.style.ERROR(f"No resource found for URI: {resource_uri}"))
            return

        # Read the resource
        try:
            if asyncio.iscoroutinefunction(mcp_server.read_resource):
                result = asyncio.run(mcp_server.read_resource(resource_uri, context))
            else:
                result = mcp_server.read_resource(resource_uri, context)

            self.stdout.write(self.style.SUCCESS("Result:"))
            if isinstance(result, dict | list):
                self.stdout.write(json.dumps(result, indent=2))
            else:
                self.stdout.write(str(result))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error reading resource: {e!s}"))

    def _handle_prompt(self, mcp_server, options):
        """Handle prompt testing."""
        prompt_name = options.get("prompt_name")

        # Get arguments from either --args or --file
        args = {}
        if options.get("args"):
            try:
                args = json.loads(options.get("args"))
            except json.JSONDecodeError as err:
                raise CommandError("Invalid JSON in --args") from err
        elif options.get("file"):
            try:
                with open(options.get("file"), encoding="utf-8") as f:
                    args = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                raise CommandError(f"Error reading arguments file: {e!s}") from e

        self.stdout.write(self.style.SUCCESS(f"Testing prompt: {prompt_name}"))
        self.stdout.write(f"Arguments: {json.dumps(args, indent=2)}")

        # Create a context
        context = Context()

        # Check if the prompt exists using the inspection module
        if not has_prompt(prompt_name):
            self.stderr.write(self.style.ERROR(f"Prompt '{prompt_name}' not found"))
            return

        # Run the prompt
        try:
            if asyncio.iscoroutinefunction(mcp_server.invoke_prompt):
                result = asyncio.run(mcp_server.invoke_prompt(prompt_name, args, context))
            else:
                result = mcp_server.invoke_prompt(prompt_name, args, context)

            self.stdout.write(self.style.SUCCESS("Result:"))
            # Prompts return strings
            self.stdout.write(str(result))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error invoking prompt: {e!s}"))
