"""
Management command to run the MCP server.

This command starts a standalone MCP server without the full Django server.
"""

import signal
import sys
import threading
import time

from django.core.management.base import BaseCommand

from django_mcp.server import get_mcp_server, initialize_mcp_server
from django_mcp.settings import get_mcp_setting, validate_settings


class Command(BaseCommand):
    """Django management command to run an MCP server."""

    help = "Run MCP server"

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument("--host", default=None, help="Host to bind server to (default: from settings)")
        parser.add_argument("--port", type=int, default=None, help="Port to bind server to (default: from settings)")
        parser.add_argument("--no-discovery", action="store_true", help="Disable auto-discovery of MCP components")
        parser.add_argument("--reload", action="store_true", help="Auto-reload server on code changes")

    def handle(self, **options):
        """Execute the command."""
        # Validate settings
        warnings = validate_settings()
        if warnings:
            for warning in warnings:
                self.stdout.write(self.style.WARNING(warning))

            if self.style.WARNING("Continue anyway? [y/N] "):
                user_input = input()
                if user_input.lower() != "y":
                    self.stdout.write(self.style.ERROR("Aborted."))
                    return

        # Get server options
        host = options.get("host") or get_mcp_setting("DJANGO_MCP_SERVER_HOST")
        port = options.get("port") or get_mcp_setting("DJANGO_MCP_SERVER_PORT")
        discovery = not options.get("no_discovery")
        reload = options.get("reload")

        # Initialize server
        try:
            initialize_mcp_server(auto_discovery=discovery, host=host, port=port)
            mcp_server = get_mcp_server()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to initialize MCP server: {e!s}"))
            return

        if not mcp_server:
            self.stderr.write(self.style.ERROR("MCP server not initialized"))
            return

        # Setup signal handling for graceful shutdown
        def signal_handler(*_):
            """Handle termination signals gracefully.

            Args:
                *_: Captures and ignores all signal handler arguments
            """
            self.stdout.write(self.style.WARNING("\nShutting down MCP server..."))
            mcp_server.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start server in a separate thread
        server_thread = threading.Thread(target=mcp_server.run)
        server_thread.daemon = True
        server_thread.start()

        self.stdout.write(self.style.SUCCESS(f"MCP server running at http://{host}:{port}"))
        self.stdout.write(self.style.SUCCESS("Press Ctrl+C to stop"))

        if reload:
            try:
                from django.utils import autoreload

                self.stdout.write(self.style.SUCCESS("Auto-reload enabled"))
                # Django's autoreload will restart the entire process when code changes
                autoreload.main(self._restart_server, args=(host, port, discovery))
            except ImportError:
                self.stderr.write(self.style.WARNING("Auto-reload not available"))
                # Just keep the main thread alive
                while True:
                    time.sleep(1)
        else:
            # Keep the main thread alive
            while True:
                time.sleep(1)

    def _restart_server(self, host, port, discovery):
        """Restart the MCP server (used for auto-reload)."""
        try:
            initialize_mcp_server(auto_discovery=discovery, host=host, port=port)
            mcp_server = get_mcp_server()

            if not mcp_server:
                self.stderr.write(self.style.ERROR("MCP server not initialized"))
                return

            # Start server in a separate thread
            server_thread = threading.Thread(target=mcp_server.run)
            server_thread.daemon = True
            server_thread.start()

            self.stdout.write(self.style.SUCCESS(f"MCP server restarted at http://{host}:{port}"))

            # Keep the main thread alive
            while True:
                time.sleep(1)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to restart MCP server: {e!s}"))
            return
