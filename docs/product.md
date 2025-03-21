# ✨ Django-MCP Product Document

> _Supercharge your Django apps with AI assistant capabilities through MCP_

![Django-MCP Logo](https://via.placeholder.com/800x200?text=Django-MCP)

## 🌈 Vision

Django-MCP enables developers to seamlessly integrate their Django applications with AI assistants by implementing the Model Context Protocol (MCP). With minimal code changes, you can expose your app's data and functionality to AI assistants, creating richer, more capable AI interactions.

## 🎯 Goals

1. Provide a **seamless integration layer** between Django and MCP
2. Make exposing Django functionality to AI assistants **incredibly simple**
3. Leverage Django's **existing patterns** for a familiar developer experience
4. Support both **simple use cases** and **advanced scenarios**
5. Balance **ease of use** with **customization options**

## 🏗️ Architecture

Django-MCP is designed as a standard Django application that can be added to any Django project. It leverages Django's app configuration system, middleware, and ASGI capabilities to provide a seamless MCP server within your application.

### Core Components

- **Django App**: Standard Django application installable via pip/pyproject.toml
- **ASGI Integration**: SSE server for MCP communication
- **Auto-Discovery**: Automatic detection of MCP components in your Django apps
- **Decorator System**: Simple decorators to expose Django functionality
- **Settings Module**: Configuration through Django's settings.py
- **Management Commands**: Easy server management and inspection

### Architectural Diagram

```
┌─────────────────────────────────────────────┐
│                Django Project                │
│                                             │
│  ┌─────────────┐    ┌─────────────────────┐ │
│  │  Your Apps  │    │    Django-MCP App   │ │
│  │             │◄──►│                     │ │
│  │ @mcp_tool   │    │  • Auto-Discovery   │ │
│  │ @mcp_resource    │  • Decorator System │ │
│  │             │    │  • ASGI Mounting    │ │
│  └─────────────┘    └─────────────────────┘ │
│          ▲                     ▲            │
└──────────┼─────────────────────┼────────────┘
           │                     │
┌──────────┼─────────────────────┼────────────┐
│          │                     ▼            │
│  ┌───────▼───────┐    ┌─────────────────┐   │
│  │  Django ORM   │    │   MCP Server    │   │
│  └───────────────┘    └─────────────────┘   │
│                              ▲               │
└──────────────────────────────┼───────────────┘
                               │
                      ┌────────▼─────────┐
                      │  AI Assistants   │
                      │  (Claude, etc.)  │
                      └──────────────────┘
```

## 💫 Features

### 1. Decorator-Based API

Expose Django functionality with simple, intuitive decorators:

```python
from django_mcp.decorators import mcp_tool, mcp_resource

@mcp_tool()
def calculate_stats(dataset_id: int) -> dict:
    """Calculate statistics for a dataset"""
    dataset = Dataset.objects.get(id=dataset_id)
    return {"mean": dataset.mean(), "median": dataset.median()}

@mcp_resource("datasets://{dataset_id}")
def get_dataset(dataset_id: int) -> str:
    """Get dataset information"""
    dataset = Dataset.objects.get(id=dataset_id)
    return f"# Dataset: {dataset.name}\n\n{dataset.description}"
```

### 2. Model Integration

First-class support for Django models:

```python
from django_mcp.decorators import mcp_model_tool, mcp_model_resource
from myapp.models import Product

# Expose CRUD operations for Product model
@mcp_model_tool(Product)
def product_tools():
    pass

# Expose Product instances as resources
@mcp_model_resource(Product, lookup="slug")
def product_resource():
    pass
```

### 3. Admin Integration

Expose Django admin functionality:

```python
from django_mcp.admin import register_admin_tools
from myapp.admin import ProductAdmin
from myapp.models import Product

# Register all admin actions for Product
register_admin_tools(ProductAdmin, Product)
```

### 4. DRF Integration

Seamless integration with Django REST Framework:

```python
from django_mcp.drf import register_viewset
from myapp.api.viewsets import ProductViewSet

# Expose all viewset actions as tools
register_viewset(ProductViewSet)
```

### 5. Auto-Discovery

Automatic detection of MCP components:

```python
# myapp/mcp_tools.py - automatically discovered!

from django_mcp.decorators import mcp_tool

@mcp_tool()
def my_tool():
    """This tool is automatically discovered"""
    return "Hello from my_tool!"
```

### 6. Easy Configuration

Simple configuration in settings.py:

```python
# settings.py

INSTALLED_APPS = [
    # ...
    'django_mcp',
    # ...
]

# MCP configuration
DJANGO_MCP_SERVER_NAME = "My Django App"
DJANGO_MCP_URL_PREFIX = "mcp"  # URL prefix for MCP endpoints
DJANGO_MCP_INSTRUCTIONS = "This server provides access to my Django app."
```

### 7. ASGI Integration

Simple ASGI integration:

```python
# asgi.py

from django_mcp.asgi import get_asgi_application

application = get_asgi_application()
```

## 👥 Target Users

1. **Django Developers**: Who want to add AI assistant capabilities to their applications
2. **AI Application Developers**: Who want to leverage Django app data and functionality
3. **Enterprise Development Teams**: Building internal tools with AI capabilities
4. **API Developers**: Who want to expose their APIs to AI assistants

## 🚀 Use Cases

1. **AI-Enhanced Admin Dashboards**: Enable AI assistants to help with admin tasks
2. **Data Exploration**: Allow AI assistants to query and analyze your application data
3. **Content Management**: AI-assisted content creation and management
4. **Customer Support**: AI assistants that can access customer data and perform actions
5. **Internal Tools**: AI-powered tools for employee productivity

## 📦 Deliverables

1. **Django-MCP Package**: Available on PyPI
2. **Documentation**: Comprehensive guides, API reference, and examples
3. **Example Projects**: Demonstrating key use cases
4. **Tests**: Comprehensive test suite

## 🛣️ Roadmap

### Version 0.1.0 (Alpha)

- Core framework and basic functionality
- Simple decorator API
- Basic model integration
- ASGI integration

### Version 0.5.0 (Beta)

- Auto-discovery system
- Admin integration
- DRF integration
- More comprehensive model integration

### Version 1.0.0 (Stable)

- Complete feature set
- Production-ready performance
- Comprehensive documentation
- Real-world examples

## 📚 Development Guidelines

1. **Django-First**: Follow Django conventions and patterns
2. **Simplicity**: Minimize boilerplate for common use cases
3. **Flexibility**: Allow customization for advanced use cases
4. **Performance**: Ensure efficient resource usage
5. **Testing**: Comprehensive test coverage
6. **Documentation**: Clear, complete documentation with examples
