"""
Management command to inspect MCP components.

This command shows all registered MCP tools, resources, and prompts.
"""

from django.core.management.base import BaseCommand

from django_mcp.server import get_mcp_server


class Command(BaseCommand):
    """Django management command to inspect MCP components."""

    help = "Inspect MCP components"

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format (default: text)")

        parser.add_argument(
            "--type",
            choices=["all", "tools", "resources", "prompts"],
            default="all",
            help="Component type to inspect (default: all)",
        )

    def handle(self, *args, **options):
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
            self._inspect_tools(mcp_server, output_format)

        if component_type in ["all", "resources"]:
            self._inspect_resources(mcp_server, output_format)

        if component_type in ["all", "prompts"]:
            self._inspect_prompts(mcp_server, output_format)

    def _inspect_tools(self, mcp_server, output_format):
        """Inspect MCP tools."""
        # Access private managers - this is safe as we know the implementation
        # In a normal application we'd use public APIs, but FastMCP doesn't expose these
        tools = list(mcp_server._tool_manager.tools.values())

        if output_format == "json":
            import json

            # Convert tools to serializable format
            tools_data = []
            for tool in tools:
                tools_data.append(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                        "is_async": tool.is_async,
                    }
                )
            self.stdout.write(json.dumps(tools_data, indent=2))
            return

        # Text format
        self.stdout.write(self.style.SUCCESS(f"Tools ({len(tools)}):"))
        for tool in tools:
            self.stdout.write(f"  - {tool.name}: {tool.description}")
            if tool.parameters:
                self.stdout.write("    Parameters:")
                for param in tool.parameters:
                    required = "(required)" if param.get("required", False) else "(optional)"
                    self.stdout.write(
                        f"      - {param['name']} ({param.get('type', 'any')}) {required}: {param.get('description', '')}"
                    )

    def _inspect_resources(self, mcp_server, output_format):
        """Inspect MCP resources."""
        # Access private managers - this is safe as we know the implementation
        resources = list(mcp_server._resource_manager.resources.values())

        if output_format == "json":
            import json

            # Convert resources to serializable format
            resources_data = []
            for resource in resources:
                resources_data.append(
                    {
                        "uri_template": resource.uri_template,
                        "description": resource.description,
                        "is_async": resource.is_async,
                    }
                )
            self.stdout.write(json.dumps(resources_data, indent=2))
            return

        # Text format
        self.stdout.write(self.style.SUCCESS(f"Resources ({len(resources)}):"))
        for resource in resources:
            self.stdout.write(f"  - {resource.uri_template}: {resource.description}")

    def _inspect_prompts(self, mcp_server, output_format):
        """Inspect MCP prompts."""
        # Access private managers - this is safe as we know the implementation
        prompts = list(mcp_server._prompt_manager.prompts.values())

        if output_format == "json":
            import json

            # Convert prompts to serializable format
            prompts_data = []
            for prompt in prompts:
                prompts_data.append(
                    {
                        "name": prompt.name,
                        "description": prompt.description,
                        "arguments": prompt.arguments,
                        "is_async": prompt.is_async,
                    }
                )
            self.stdout.write(json.dumps(prompts_data, indent=2))
            return

        # Text format
        self.stdout.write(self.style.SUCCESS(f"Prompts ({len(prompts)}):"))
        for prompt in prompts:
            self.stdout.write(f"  - {prompt.name}: {prompt.description}")
            if prompt.arguments:
                self.stdout.write("    Arguments:")
                for arg in prompt.arguments:
                    required = "(required)" if arg.get("required", False) else "(optional)"
                    self.stdout.write(f"      - {arg['name']} {required}: {arg.get('description', '')}")
