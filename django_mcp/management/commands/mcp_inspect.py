"""
Django management command for inspecting MCP components.

This command allows you to see details about registered tools, resources, and prompts.
"""
# pylint: disable=duplicate-code

from argparse import ArgumentParser
import json
from typing import Any

from django.core.management.base import BaseCommand

from django_mcp.inspection import get_prompts, get_resources, get_tools
from django_mcp.server import get_mcp_server


class Command(BaseCommand):
    """Django management command to inspect MCP components."""

    help = "Inspect MCP components"

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add command line arguments."""
        parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format (default: text)")

        parser.add_argument(
            "--type",
            choices=["all", "tools", "resources", "prompts"],
            default="all",
            help="Component type to inspect (default: all)",
        )

    def handle(self, **options: Any) -> None:
        """Execute the command."""
        # Get format option
        output_format = options["format"]
        component_type = options["type"]

        try:
            mcp_server = get_mcp_server()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"MCP server not initialized: {e!s}"))
            return

        if not mcp_server:
            self.stderr.write(self.style.ERROR("MCP server not initialized"))
            return

        # Get MCP components
        if component_type in ["all", "tools"]:
            self._inspect_tools(output_format)

        if component_type in ["all", "resources"]:
            self._inspect_resources(output_format)

        if component_type in ["all", "prompts"]:
            self._inspect_prompts(output_format)

    def _inspect_tools(self, output_format: str) -> None:
        """Inspect MCP tools."""
        # Use the inspection module instead of accessing private members
        tools = get_tools()

        if output_format == "json":
            # Convert tools to serializable format
            tools_data: list[dict[str, Any]] = []
            for tool in tools:
                tool_dict = tool
                tools_data.append(
                    {
                        "name": tool_dict.get("name", ""),
                        "description": tool_dict.get("description", ""),
                        "parameters": tool_dict.get("parameters", {}),
                        "is_async": tool_dict.get("is_async", False),
                    }
                )
            self.stdout.write(json.dumps(tools_data, indent=2))
            return

        # Text format
        self.stdout.write(self.style.SUCCESS(f"Tools ({len(tools)}):"))
        for tool in tools:
            tool_dict = tool
            name = tool_dict.get("name", "")
            description = tool_dict.get("description", "")
            self.stdout.write(f"  - {name}: {description}")

            parameters = tool_dict.get("parameters", [])
            if parameters:
                self.stdout.write("    Parameters:")
                for param in parameters:
                    required = "(required)" if param.get("required", False) else "(optional)"
                    self.stdout.write(
                        f"      - {param['name']} ({param.get('type', 'any')}) {required}: "
                        f"{param.get('description', '')}"
                    )

    def _inspect_resources(self, output_format: str) -> None:
        """Inspect MCP resources."""
        # Use the inspection module instead of accessing private members
        resources = get_resources()

        if output_format == "json":
            # Convert resources to serializable format
            resources_data: list[dict[str, Any]] = []
            for resource in resources:
                resource_dict = resource
                resources_data.append(
                    {
                        "uri_template": resource_dict.get("uri_template", ""),
                        "description": resource_dict.get("description", ""),
                        "is_async": resource_dict.get("is_async", False),
                    }
                )
            self.stdout.write(json.dumps(resources_data, indent=2))
            return

        # Text format
        self.stdout.write(self.style.SUCCESS(f"Resources ({len(resources)}):"))
        for resource in resources:
            resource_dict = resource
            uri_template = resource_dict.get("uri_template", "")
            description = resource_dict.get("description", "")
            self.stdout.write(f"  - {uri_template}: {description}")

    def _inspect_prompts(self, output_format: str) -> None:
        """Inspect MCP prompts."""
        # Use the inspection module instead of accessing private members
        prompts = get_prompts()

        if output_format == "json":
            # Convert prompts to serializable format
            prompts_data: list[dict[str, Any]] = []
            for prompt in prompts:
                prompt_dict = prompt
                prompts_data.append(
                    {
                        "name": prompt_dict.get("name", ""),
                        "description": prompt_dict.get("description", ""),
                        "arguments": prompt_dict.get("arguments", {}),
                        "is_async": prompt_dict.get("is_async", False),
                    }
                )
            self.stdout.write(json.dumps(prompts_data, indent=2))
            return

        # Text format
        self.stdout.write(self.style.SUCCESS(f"Prompts ({len(prompts)}):"))
        for prompt in prompts:
            prompt_dict = prompt
            name = prompt_dict.get("name", "")
            description = prompt_dict.get("description", "")
            self.stdout.write(f"  - {name}: {description}")

            arguments = prompt_dict.get("arguments", [])
            if arguments:
                self.stdout.write("    Arguments:")
                for arg in arguments:
                    required = "(required)" if arg.get("required", False) else "(optional)"
                    self.stdout.write(f"      - {arg['name']} {required}: {arg.get('description', '')}")
