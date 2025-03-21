
# Django-MCP: Seamless Integration of Model Context Protocol with Django

## Overview

Django-MCP is a Django application that provides seamless integration between Django applications and the Model Context Protocol (MCP). It leverages FastMCP for easy tool/resource/prompt creation and integrates with Django's ORM, admin, views, and other components to create a powerful AI-ready integration layer.

The library will make it trivially easy for developers to expose Django functionality to AI assistants by:

1. Adding a few lines to settings.py
2. Using decorator-based annotations on models, views, and functions
3. Automatically discovering and registering MCP components

## Core Architecture

The library will consist of:

1. **Django App Configuration**: A Django app that can be added to INSTALLED_APPS
2. **AppConfig with Auto-Discovery**: Using Django's app registry for discovery
3. **ASGI Integration**: Mounting the MCP SSE server in Django's ASGI application
4. **Decorator System**: Simple decorators to expose Django features
5. **DRF Integration**: Optional integration with Django REST Framework
6. **Admin Integration**: Exposing Django admin functionality as MCP tools
7. **Settings System**: Configurable settings in Django's settings.py

## Implementation Plan

### 1. Package Structure

```
django_mcp/
├── __init__.py
├── apps.py                    # Django AppConfig
├── decorators.py              # MCP decorators (mcp_tool, mcp_resource, etc.)
├── server.py                  # MCP server initialization and management
├── asgi.py                    # ASGI mounting helpers
├── discovery.py               # Auto-discovery of MCP components
├── middleware.py              # Django middleware for MCP
├── settings.py                # Settings definitions
├── models.py                  # Empty for Django app
├── views.py                   # MCP views for SSE endpoint
├── model_tools.py             # Model-specific integration
├── admin_tools.py             # Admin-specific integration
├── drf_tools.py               # DRF-specific integration
├── utils/
│   ├── __init__.py
│   ├── async_utils.py         # Utilities for async/sync bridging
│   ├── django_context.py      # Django context for MCP requests
│   └── request_utils.py       # Request utilities
├── management/
│   └── commands/
│       ├── __init__.py
│       ├── mcp_inspect.py     # Command to inspect MCP components
│       └── mcp_run.py         # Command to run MCP server
└── templates/
    └── django_mcp/
        └── dashboard.html     # MCP dashboard template
```

### 2. Core Components

#### 2.1. AppConfig Implementation

The AppConfig class will be responsible for initializing the MCP server and discovering MCP components:

```python
# django_mcp/apps.py
from django.apps import AppConfig
from django.utils.module_loading import module_has_submodule

class DjangoMCPConfig(AppConfig):
    name = 'django_mcp'
    verbose_name = 'Django MCP Integration'
    
    def ready(self):
        """
        Initialize MCP server when Django app is ready.
        This runs after all apps are loaded, so we can use auto-discovery.
        """
        # Skip initialization on all Django management commands except runserver
        import sys
        if 'runserver' not in sys.argv and 'uvicorn' not in sys.argv:
            return
            
        # Avoid duplicate initialization in development with auto-reload
        import os
        if os.environ.get('RUN_MAIN') == 'true' or os.environ.get('RUN_MAIN') is None:
            self.initialize_mcp_server()
            self.auto_discover_mcp_components()
    
    def initialize_mcp_server(self):
        """Initialize the MCP server with settings from Django"""
        from django.conf import settings
        from django_mcp.server import get_mcp_server
        
        # Get or create MCP server
        mcp_server = get_mcp_server()
        
        # Register the server instance in app registry for later use
        self.mcp_server = mcp_server
    
    def auto_discover_mcp_components(self):
        """Discover all MCP tools, resources, prompts in installed apps"""
        from django.apps import apps
        from importlib import import_module
        
        # Look for mcp_tools.py module in all installed apps
        for app_config in apps.get_app_configs():
            # Skip apps that don't have modules
            if not hasattr(app_config, 'module'):
                continue
                
            # Try to import mcp_tools.py from each app
            if module_has_submodule(app_config.module, 'mcp_tools'):
                import_module(f"{app_config.name}.mcp_tools")
                
            # Also look for MCP annotations in models.py
            if module_has_submodule(app_config.module, 'models'):
                import_module(f"{app_config.name}.models")
```

#### 2.2. Server Management

The server module will manage the MCP server instance:

```python
# django_mcp/server.py
from django.conf import settings
from mcp.server.fastmcp import FastMCP
from typing import Optional
import threading

# Global MCP server instance
_mcp_server = None
_mcp_server_lock = threading.Lock()

def get_mcp_server() -> FastMCP:
    """
    Get or create the MCP server instance.
    This ensures we have a single instance across the application.
    """
    global _mcp_server
    
    if _mcp_server is None:
        with _mcp_server_lock:
            if _mcp_server is None:
                # Get server name from settings or use default
                server_name = getattr(settings, 'DJANGO_MCP_SERVER_NAME', 
                                     f"{settings.ROOT_URLCONF.split('.')[0]} MCP Server")
                
                # Get additional settings from Django settings
                instructions = getattr(settings, 'DJANGO_MCP_INSTRUCTIONS', None)
                dependencies = getattr(settings, 'DJANGO_MCP_DEPENDENCIES', [])
                lifespan = getattr(settings, 'DJANGO_MCP_LIFESPAN', None)
                
                # Create the MCP server
                _mcp_server = FastMCP(
                    name=server_name,
                    instructions=instructions,
                    dependencies=dependencies,
                    lifespan=lifespan
                )
                
    return _mcp_server

def get_sse_app():
    """
    Get the ASGI application for the SSE endpoint.
    This is used for mounting in Django's ASGI application.
    """
    mcp_server = get_mcp_server()
    return mcp_server.sse_app()
```

#### 2.3. ASGI Integration

To integrate with Django's ASGI application, we'll create an asgi.py module:

```python
# django_mcp/asgi.py
from django.urls import re_path

def get_asgi_application():
    """
    Get Django's ASGI application with MCP mounted.
    This serves as a replacement for Django's get_asgi_application.
    """
    from django.core.asgi import get_asgi_application as django_get_asgi_application
    from django_mcp.server import get_sse_app
    
    # Get Django's ASGI application
    django_application = django_get_asgi_application()
    
    # Get MCP's SSE application
    mcp_sse_app = get_sse_app()
    
    async def application(scope, receive, send):
        """
        ASGI application that routes MCP SSE requests to the MCP server
        and all other requests to Django.
        """
        from django.conf import settings
        
        # Get MCP URL prefix from settings (default to /mcp)
        mcp_prefix = getattr(settings, 'DJANGO_MCP_URL_PREFIX', 'mcp')
        
        # Check if this is an MCP SSE request
        path = scope.get('path', '')
        
        if path.startswith(f'/{mcp_prefix}'):
            # Route to MCP SSE app
            return await mcp_sse_app(scope, receive, send)
        
        # Route to Django
        return await django_application(scope, receive, send)
    
    return application

def mount_mcp_in_starlette_app(app):
    """
    Mount MCP in a Starlette app.
    This is useful for manually mounting MCP in a Starlette app.
    """
    from django.conf import settings
    from starlette.routing import Mount
    from django_mcp.server import get_sse_app
    
    mcp_prefix = getattr(settings, 'DJANGO_MCP_URL_PREFIX', 'mcp')
    sse_app = get_sse_app()
    
    app.routes.append(Mount(f'/{mcp_prefix}', app=sse_app))
    
    return app
```

#### 2.4. Decorator System

The decorator system will provide a simple way to expose Django functionality as MCP components:

```python
# django_mcp/decorators.py
from django.db.models import Model
from django_mcp.server import get_mcp_server
from functools import wraps
from typing import Optional, Any, Callable, Dict, List, Type, Union

def mcp_tool(description: Optional[str] = None, **kwargs):
    """
    Decorator to expose a function as an MCP tool.
    
    Args:
        description: Optional description of the tool
        **kwargs: Additional kwargs for FastMCP.tool
    """
    def decorator(func):
        # Get MCP server
        mcp_server = get_mcp_server()
        
        if mcp_server:
            # Register with FastMCP
            return mcp_server.tool(description=description, **kwargs)(func)
        
        # Return the original function if server isn't ready
        return func
    
    return decorator

def mcp_resource(uri_template: str, description: Optional[str] = None, **kwargs):
    """
    Decorator to expose a function as an MCP resource.
    
    Args:
        uri_template: URI template for the resource
        description: Optional description of the resource
        **kwargs: Additional kwargs for FastMCP.resource
    """
    def decorator(func):
        # Get MCP server
        mcp_server = get_mcp_server()
        
        if mcp_server:
            # Register with FastMCP
            return mcp_server.resource(uri_template, description=description, **kwargs)(func)
        
        # Return the original function if server isn't ready
        return func
    
    return decorator

def mcp_prompt(name: Optional[str] = None, description: Optional[str] = None, **kwargs):
    """
    Decorator to expose a function as an MCP prompt.
    
    Args:
        name: Optional name for the prompt
        description: Optional description of the prompt
        **kwargs: Additional kwargs for FastMCP.prompt
    """
    def decorator(func):
        # Get MCP server
        mcp_server = get_mcp_server()
        
        if mcp_server:
            # Register with FastMCP
            return mcp_server.prompt(name=name, description=description, **kwargs)(func)
        
        # Return the original function if server isn't ready
        return func
    
    return decorator

def mcp_model_tool(model: Type[Model], **kwargs):
    """
    Decorator to expose a Django model as MCP tools.
    This will create CRUD tools for the model.
    
    Args:
        model: Django model class
        **kwargs: Additional kwargs for tool registration
    """
    from django_mcp.model_tools import register_model_tools
    
    def decorator(func=None):
        # If no function is provided, register default tools
        if func is None:
            register_model_tools(model, **kwargs)
            return lambda: None
        
        # Otherwise, register and return the function
        register_model_tools(model, **kwargs)
        return func
    
    return decorator

def mcp_model_resource(model: Type[Model], lookup: str = 'pk', fields: Optional[List[str]] = None, **kwargs):
    """
    Decorator to expose a Django model as an MCP resource.
    
    Args:
        model: Django model class
        lookup: Field to use for lookup (default: 'pk')
        fields: Optional list of fields to include
        **kwargs: Additional kwargs for resource registration
    """
    from django_mcp.model_tools import register_model_resource
    
    def decorator(func=None):
        # If no function is provided, register default resource
        if func is None:
            register_model_resource(model, lookup, fields, **kwargs)
            return lambda: None
        
        # Otherwise, register and return the function
        register_model_resource(model, lookup, fields, **kwargs)
        return func
    
    return decorator
```

#### 2.5. Model Integration

The model_tools.py module will provide model-specific integration:

```python
# django_mcp/model_tools.py
from django.db import models
from django.db.models import Model, Q
from django.core.exceptions import ValidationError
from django_mcp.server import get_mcp_server
from typing import Optional, List, Type, Dict, Any

def register_model_tools(model: Type[Model], **kwargs):
    """
    Register standard CRUD tools for a Django model.
    
    Args:
        model: Django model class
        **kwargs: Additional kwargs for tool registration
    """
    mcp_server = get_mcp_server()
    if not mcp_server:
        return
    
    model_name = model._meta.model_name
    verbose_name = model._meta.verbose_name
    
    # Create tool to get a model instance
    @mcp_server.tool(description=f"Get a {verbose_name} by ID")
    def get_model_instance(id: int) -> dict:
        """
        Get a single instance of {verbose_name} by ID.
        
        Args:
            id: The primary key of the {verbose_name} to retrieve
        """
        try:
            instance = model.objects.get(pk=id)
            return _instance_to_dict(instance)
        except model.DoesNotExist:
            return {"error": f"{verbose_name.title()} with ID {id} not found"}
    
    # Create tool to list model instances
    @mcp_server.tool(description=f"List {verbose_name} instances")
    def list_model_instances(limit: int = 10, offset: int = 0) -> list:
        """
        List instances of {verbose_name}.
        
        Args:
            limit: Maximum number of instances to return
            offset: Number of instances to skip
        """
        instances = model.objects.all()[offset:offset+limit]
        return [_instance_to_dict(instance) for instance in instances]
    
    # Create tool to search model instances
    @mcp_server.tool(description=f"Search {verbose_name} instances")
    def search_model_instances(query: str, limit: int = 10) -> list:
        """
        Search for {verbose_name} instances by text fields.
        
        Args:
            query: Search query
            limit: Maximum number of instances to return
        """
        # Build Q objects for text fields
        q_objects = Q()
        for field in model._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                q_objects |= Q(**{f"{field.name}__icontains": query})
        
        instances = model.objects.filter(q_objects)[:limit]
        return [_instance_to_dict(instance) for instance in instances]
    
    # If the model has a create permission, add create tool
    @mcp_server.tool(description=f"Create a new {verbose_name}")
    def create_model_instance(**kwargs) -> dict:
        """
        Create a new {verbose_name}.
        
        Args:
            **kwargs: Field values for the new {verbose_name}
        """
        try:
            instance = model(**kwargs)
            instance.full_clean()
            instance.save()
            return {"success": True, "id": instance.pk, "instance": _instance_to_dict(instance)}
        except ValidationError as e:
            return {"success": False, "errors": e.message_dict}
        except Exception as e:
            return {"success": False, "error": str(e)}

def register_model_resource(model: Type[Model], lookup: str = 'pk', fields: Optional[List[str]] = None, **kwargs):
    """
    Register a Django model as an MCP resource.
    
    Args:
        model: Django model class
        lookup: Field to use for lookup (default: 'pk')
        fields: Optional list of fields to include
        **kwargs: Additional kwargs for resource registration
    """
    mcp_server = get_mcp_server()
    if not mcp_server:
        return
    
    app_label = model._meta.app_label
    model_name = model._meta.model_name
    
    uri_template = f"{app_label}://{model_name}/{{{lookup}}}"
    
    @mcp_server.resource(uri_template)
    def get_model_resource(**kwargs):
        """Get a {model._meta.verbose_name} as a resource"""
        lookup_value = kwargs.get(lookup)
        
        try:
            instance = model.objects.get(**{lookup: lookup_value})
            
            # Format as Markdown for better LLM consumption
            result = [f"# {model._meta.verbose_name.title()}: {instance}"]
            
            # Add fields
            field_list = fields if fields else [f.name for f in model._meta.fields]
            for field_name in field_list:
                if hasattr(instance, field_name):
                    result.append(f"- **{field_name}**: {getattr(instance, field_name)}")
            
            # Add relations if available
            for field in model._meta.related_objects:
                related_name = field.get_accessor_name()
                if hasattr(instance, related_name):
                    related_manager = getattr(instance, related_name)
                    if hasattr(related_manager, 'all'):
                        related_items = list(related_manager.all()[:5])
                        if related_items:
                            result.append(f"\n## {field.name.title()} ({len(related_items)})")
                            for item in related_items:
                                result.append(f"- {item}")
            
            return "\n".join(result)
            
        except model.DoesNotExist:
            return f"{model._meta.verbose_name.title()} with {lookup}={lookup_value} not found"

def _instance_to_dict(instance: Model) -> Dict[str, Any]:
    """
    Convert a model instance to a dictionary.
    """
    result = {}
    
    # Add regular fields
    for field in instance._meta.fields:
        result[field.name] = str(getattr(instance, field.name))
    
    return result
```

#### 2.6. Admin Integration

The admin_tools.py module will provide admin-specific integration:

```python
# django_mcp/admin_tools.py
from django.contrib.admin.sites import site
from django_mcp.server import get_mcp_server

def register_admin_tools():
    """
    Register tools for Django admin actions.
    """
    mcp_server = get_mcp_server()
    if not mcp_server:
        return
    
    # Register tool for each admin action
    for model, admin_class in site._registry.items():
        model_name = model._meta.model_name
        app_label = model._meta.app_label
        verbose_name = model._meta.verbose_name
        
        # Register standard admin actions
        for action_name in admin_class.actions:
            if action_name == 'delete_selected':
                continue  # Skip delete action for safety
                
            action = getattr(admin_class, action_name)
            description = getattr(action, 'short_description', action_name.replace('_', ' ').title())
            
            @mcp_server.tool(description=f"Admin action: {description} for {verbose_name}")
            def admin_action_tool(action_name=action_name, model=model, admin_class=admin_class):
                """
                Execute admin action on selected objects.
                
                Args:
                    ids: List of object IDs to act upon
                """
                # Get the action
                action = getattr(admin_class, action_name)
                
                # Get QuerySet of objects
                queryset = model.objects.filter(pk__in=ids)
                
                # Execute the action
                result = action(admin_class, None, queryset)
                
                return {
                    "success": True,
                    "action": action_name,
                    "affected_count": queryset.count(),
                    "result": str(result) if result else "Action executed successfully"
                }
```

#### 2.7. DRF Integration

The drf_tools.py module will provide DRF-specific integration:

```python
# django_mcp/drf_tools.py
from django.conf import settings
from django_mcp.server import get_mcp_server
from typing import Type, List, Dict, Any, Optional

def register_drf_viewset(viewset_class, **kwargs):
    """
    Register tools for a DRF ViewSet.
    
    Args:
        viewset_class: ViewSet class
        **kwargs: Additional kwargs for tool registration
    """
    # Skip if DRF is not installed
    try:
        from rest_framework.viewsets import ViewSet
        from rest_framework.response import Response
    except ImportError:
        return
    
    mcp_server = get_mcp_server()
    if not mcp_server:
        return
    
    # Skip if viewset_class is not a ViewSet
    if not issubclass(viewset_class, ViewSet):
        return
    
    # Get model name from viewset
    model = getattr(viewset_class, 'queryset', None)
    if model is not None:
        model = model.model
        model_name = model._meta.verbose_name
    else:
        model_name = viewset_class.__name__.replace('ViewSet', '')
    
    # Get actions from viewset
    actions = getattr(viewset_class, 'action_map', {})
    
    # Register a tool for each action
    for method, action in actions.items():
        # Skip options and head
        if method in ('options', 'head'):
            continue
        
        @mcp_server.tool(description=f"API action: {action} {model_name}")
        def drf_action_tool(method=method, action=action, viewset_class=viewset_class, **params):
            """
            Execute a DRF ViewSet action.
            
            Args:
                **params: Parameters for the action
            """
            # Instantiate the viewset
            viewset = viewset_class()
            
            # Set action and request
            viewset.action = action
            
            # Execute the action
            action_method = getattr(viewset, action)
            result = action_method(None, **params)
            
            # Handle Response object
            if isinstance(result, Response):
                return result.data
            
            return result
```

#### 2.8. Views and URL Patterns

The views.py module will provide Django views for the MCP endpoints:

```python
# django_mcp/views.py
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from django_mcp.server import get_mcp_server

async def mcp_sse_view(request):
    """
    Handle SSE connections for MCP.
    """
    from django_mcp.server import get_sse_app
    
    sse_app = get_sse_app()
    if not sse_app:
        return HttpResponse("MCP server not initialized", status=500)
    
    # Pass control to the FastMCP SSE app
    return await sse_app(request.scope, request.receive, request.send)

@csrf_exempt
@require_http_methods(["POST"])
async def mcp_message_view(request):
    """
    Handle MCP messages.
    """
    from django_mcp.server import get_mcp_server
    
    mcp_server = get_mcp_server()
    if not mcp_server:
        return JsonResponse({"error": "MCP server not initialized"}, status=500)
    
    # Get request body
    body = json.loads(request.body)
    
    # Process the message
    response = await mcp_server.handle_message(body)
    
    return JsonResponse(response)

def mcp_dashboard(request):
    """
    Render the MCP dashboard.
    """
    from django.shortcuts import render
    from django_mcp.server import get_mcp_server
    
    mcp_server = get_mcp_server()
    
    # Get MCP components
    tools = []
    resources = []
    prompts = []
    
    if mcp_server:
        tools = mcp_server._tool_manager.tools
        resources = mcp_server._resource_manager.resources
        prompts = mcp_server._prompt_manager.prompts
    
    return render(request, 'django_mcp/dashboard.html', {
        'tools': tools,
        'resources': resources,
        'prompts': prompts,
    })
```

Create URL patterns in urls.py:

```python
# django_mcp/urls.py
from django.urls import path
from django.conf import settings
from django_mcp import views

app_name = 'django_mcp'

# Get MCP URL prefix from settings (default to /mcp)
mcp_prefix = getattr(settings, 'DJANGO_MCP_URL_PREFIX', 'mcp')

urlpatterns = [
    path(f'{mcp_prefix}/', views.mcp_sse_view, name='mcp_sse'),
    path(f'{mcp_prefix}/message', views.mcp_message_view, name='mcp_message'),
    path(f'{mcp_prefix}/dashboard', views.mcp_dashboard, name='mcp_dashboard'),
]
```

#### 2.9. Settings

Define default settings in settings.py:

```python
# django_mcp/settings.py
from django.conf import settings

# Default settings
DEFAULTS = {
    'DJANGO_MCP_SERVER_NAME': None,  # Default to project name
    'DJANGO_MCP_URL_PREFIX': 'mcp',  # URL prefix for MCP endpoints
    'DJANGO_MCP_INSTRUCTIONS': None,  # Instructions for MCP clients
    'DJANGO_MCP_DEPENDENCIES': [],    # Dependencies for MCP server
    'DJANGO_MCP_AUTO_DISCOVER': True, # Auto-discover MCP components
    'DJANGO_MCP_EXPOSE_MODELS': True, # Auto-expose Django models
    'DJANGO_MCP_EXPOSE_ADMIN': True,  # Auto-expose Django admin
    'DJANGO_MCP_EXPOSE_DRF': True,    # Auto-expose DRF ViewSets
}

# Set defaults for settings that aren't already defined
for key, default in DEFAULTS.items():
    if not hasattr(settings, key):
        setattr(settings, key, default)
```

#### 2.10. Management Commands

Create management commands for running and inspecting the MCP server:

```python
# django_mcp/management/commands/mcp_inspect.py
from django.core.management.base import BaseCommand
from django_mcp.server import get_mcp_server

class Command(BaseCommand):
    help = 'Inspect MCP components'
    
    def handle(self, *args, **options):
        mcp_server = get_mcp_server()
        
        if not mcp_server:
            self.stderr.write(self.style.ERROR('MCP server not initialized'))
            return
        
        # Get MCP components
        tools = mcp_server._tool_manager.tools
        resources = mcp_server._resource_manager.resources
        prompts = mcp_server._prompt_manager.prompts
        
        # Print tools
        self.stdout.write(self.style.SUCCESS(f'Tools ({len(tools)}):'))
        for name, tool in tools.items():
            self.stdout.write(f'  - {name}: {tool.description}')
        
        # Print resources
        self.stdout.write(self.style.SUCCESS(f'Resources ({len(resources)}):'))
        for uri, resource in resources.items():
            self.stdout.write(f'  - {uri}: {resource.description}')
        
        # Print prompts
        self.stdout.write(self.style.SUCCESS(f'Prompts ({len(prompts)}):'))
        for name, prompt in prompts.items():
            self.stdout.write(f'  - {name}: {prompt.description}')
```

```python
# django_mcp/management/commands/mcp_run.py
from django.core.management.base import BaseCommand
from django_mcp.server import get_mcp_server

class Command(BaseCommand):
    help = 'Run MCP server'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--transport',
            choices=['stdio', 'sse'],
            default='stdio',
            help='Transport to use (default: stdio)'
        )
        parser.add_argument(
            '--host',
            default='127.0.0.1',
            help='Host to bind to (SSE only, default: 127.0.0.1)'
        )
        parser.add_argument(
            '--port',
            type=int,
            default=8000,
            help='Port to bind to (SSE only, default: 8000)'
        )
    
    def handle(self, *args, **options):
        mcp_server = get_mcp_server()
        
        if not mcp_server:
            self.stderr.write(self.style.ERROR('MCP server not initialized'))
            return
        
        transport = options['transport']
        
        if transport == 'stdio':
            self.stdout.write(self.style.SUCCESS('Running MCP server (stdio transport)'))
            mcp_server.run('stdio')
        elif transport == 'sse':
            host = options['host']
            port = options['port']
            self.stdout.write(self.style.SUCCESS(f'Running MCP server (SSE transport) on {host