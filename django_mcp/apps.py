from importlib import import_module
import os
import sys

from django.apps import AppConfig
from django.utils.module_loading import module_has_submodule

from django_mcp.server import get_mcp_server


class DjangoMCPConfig(AppConfig):
    """
    Django app configuration for Django-MCP.

    This AppConfig handles initialization of the MCP server and
    discovery of MCP components (tools, resources, prompts).
    """

    name = "django_mcp"
    verbose_name = "Django MCP Integration"

    def ready(self) -> None:
        """
        Initialize MCP server when Django app is ready.

        This runs after all apps are loaded, allowing auto-discovery
        of MCP components from other installed apps.
        """
        # Skip initialization on most management commands
        if self._should_skip_initialization():
            return

        # Initialize the MCP server
        self.initialize_mcp_server()

        # Auto-discover MCP components in installed apps
        if self._should_auto_discover():
            self.auto_discover_mcp_components()

    def initialize_mcp_server(self) -> None:
        """
        Initialize the MCP server with settings from Django.

        This creates or gets the MCP server singleton instance and
        configures it based on Django settings.
        """
        from django.conf import settings

        # Get server name from settings or use default based on project name
        server_name = getattr(settings, "DJANGO_MCP_SERVER_NAME", self._get_default_server_name())

        # Get additional settings
        instructions = getattr(settings, "DJANGO_MCP_INSTRUCTIONS", None)
        dependencies = getattr(settings, "DJANGO_MCP_DEPENDENCIES", [])

        # Get or create the MCP server instance
        mcp_server = get_mcp_server(name=server_name, instructions=instructions, dependencies=dependencies)

        # Register the server instance for later use
        self.mcp_server = mcp_server

    def auto_discover_mcp_components(self) -> None:
        """
        Discover all MCP tools, resources, and prompts in installed apps.

        Looks for special module names in each installed app:
        - mcp_tools.py: Contains tool definitions
        - mcp_resources.py: Contains resource definitions
        - mcp_prompts.py: Contains prompt definitions

        Additionally checks models.py for MCP decorators.
        """

        from django.apps import apps

        # Look for MCP modules in all installed apps
        for app_config in apps.get_app_configs():
            # Skip apps without modules
            if not hasattr(app_config, "module"):
                continue

            # Try to import specific MCP modules
            self._import_mcp_module(app_config, "mcp_tools")
            self._import_mcp_module(app_config, "mcp_resources")
            self._import_mcp_module(app_config, "mcp_prompts")

            # Models might have MCP decorators too
            self._import_mcp_module(app_config, "models")

            # Admin might have MCP integrations
            if self._should_expose_admin():
                self._import_mcp_module(app_config, "admin")

            # Views might have MCP decorators
            self._import_mcp_module(app_config, "views")

    def _import_mcp_module(self, app_config: AppConfig, module_name: str) -> None:
        """
        Import a module from an app if it exists.

        Args:
            app_config: The Django AppConfig to import from
            module_name: The name of the module to import
        """
        try:
            if module_has_submodule(app_config.module, module_name):
                import_module(f"{app_config.name}.{module_name}")
        except ImportError:
            # Log this but don't crash
            import logging

            logging.getLogger("django_mcp").debug("Error importing %s from %s", module_name, app_config.name)

    def _should_skip_initialization(self) -> bool:
        """
        Determine if we should skip MCP initialization.

        We skip initialization in most management commands except:
        - runserver
        - uvicorn
        - test (unless DJANGO_MCP_SKIP_IN_TESTS is True)

        We also avoid duplicate initialization in development with auto-reload.

        Returns:
            bool: True if we should skip initialization
        """
        from django.conf import settings

        # Get arguments
        args = sys.argv

        # List of commands that should initialize MCP
        init_commands = ["runserver", "uvicorn"]

        # Check if we're running tests
        running_tests = "test" in args
        skip_in_tests = getattr(settings, "DJANGO_MCP_SKIP_IN_TESTS", False)

        # Skip if we're not in a supported command and not testing
        if not any(cmd in args for cmd in init_commands) and (not running_tests or skip_in_tests):
            return True

        # In auto-reload environments, only initialize in the main process
        return os.environ.get("RUN_MAIN") == "false"

    def _should_auto_discover(self) -> bool:
        """
        Determine if we should auto-discover MCP components.

        Returns:
            bool: True if we should auto-discover
        """
        from django.conf import settings

        return getattr(settings, "DJANGO_MCP_AUTO_DISCOVER", True)

    def _should_expose_admin(self) -> bool:
        """
        Determine if we should expose Django admin functionality.

        Returns:
            bool: True if we should expose admin
        """
        from django.conf import settings

        return getattr(settings, "DJANGO_MCP_EXPOSE_ADMIN", True)

    def _get_default_server_name(self) -> str:
        """
        Get a default server name based on the project.

        Returns:
            str: Default server name
        """
        from django.conf import settings

        # Try to get a name from ROOT_URLCONF
        # Using hasattr to avoid the mypy error about settings not having ROOT_URLCONF
        if hasattr(settings, "ROOT_URLCONF") and settings.ROOT_URLCONF:  # type: ignore
            project_name = settings.ROOT_URLCONF.split(".")[0]  # type: ignore
            return f"{project_name.title()} MCP Server"

        return "Django MCP Server"
