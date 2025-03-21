# 🚀 Django-MCP Usage Guide

> _Transform your Django app into an AI assistant powerhouse_

![Django-MCP Usage](https://via.placeholder.com/800x200?text=Django-MCP+Usage)

## 📖 Table of Contents

- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Exposing Functionality](#-exposing-functionality)
  - [Tools](#tools)
  - [Resources](#resources)
  - [Prompts](#prompts)
- [Model Integration](#-model-integration)
- [Admin Integration](#-admin-integration)
- [DRF Integration](#-drf-integration)
- [Advanced Usage](#-advanced-usage)
- [Troubleshooting](#-troubleshooting)

## 💾 Installation

Installing Django-MCP is as simple as adding it to your project:

```bash
# Using pip
pip install django-mcp

# Using poetry
poetry add django-mcp

# Using uv
uv add django-mcp
```

Then add it to your `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'django_mcp',
    # ...
]
```

## 🏃‍♀️ Quick Start

1️⃣ **Install the package**

```bash
pip install django-mcp
```

2️⃣ **Add to INSTALLED_APPS**

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'django_mcp',
    # ...
]
```

3️⃣ **Configure your ASGI application**

```python
# asgi.py
from django_mcp.asgi import get_asgi_application

application = get_asgi_application()
```

4️⃣ **Create your first MCP tool**

```python
# myapp/mcp_tools.py
from django_mcp.decorators import mcp_tool

@mcp_tool()
def hello_world(name: str = "World") -> str:
    """Say hello to someone"""
    return f"Hello, {name}!"
```

5️⃣ **Run your server**

```bash
python manage.py runserver
```

That's it! Your Django app now exposes an MCP server that AI assistants can connect to!

## ⚙️ Configuration

Configure Django-MCP in your `settings.py`:

```python
# Basic configuration
DJANGO_MCP_SERVER_NAME = "My Django App"  # Name of your MCP server
DJANGO_MCP_URL_PREFIX = "mcp"  # URL prefix for MCP endpoints

# MCP protocol configuration
DJANGO_MCP_INSTRUCTIONS = "This server provides access to my Django app."
DJANGO_MCP_DEPENDENCIES = ["pandas", "matplotlib"]  # Optional dependencies

# Feature flags
DJANGO_MCP_AUTO_DISCOVER = True  # Auto-discover MCP components
DJANGO_MCP_EXPOSE_MODELS = True  # Auto-expose Django models
DJANGO_MCP_EXPOSE_ADMIN = True  # Auto-expose Django admin
DJANGO_MCP_EXPOSE_DRF = True  # Auto-expose DRF ViewSets
```

## 🔧 Exposing Functionality

### Tools

Tools let AI assistants take actions in your Django app. Create them with the `@mcp_tool` decorator:

```python
from django_mcp.decorators import mcp_tool
from myapp.models import Order

@mcp_tool()
def get_order_status(order_id: int) -> dict:
    """Get the status of an order"""
    order = Order.objects.get(id=order_id)
    return {
        "id": order.id,
        "status": order.status,
        "created_at": order.created_at.isoformat(),
        "items_count": order.items.count(),
    }

@mcp_tool(description="Cancel an existing order")
def cancel_order(order_id: int, reason: str = "Customer request") -> dict:
    """Cancel an order with the given ID"""
    order = Order.objects.get(id=order_id)
    order.status = "cancelled"
    order.cancellation_reason = reason
    order.save()

    return {"success": True, "message": f"Order {order_id} cancelled"}
```

### Resources

Resources provide data for the AI assistant to reference. Create them with the `@mcp_resource` decorator:

```python
from django_mcp.decorators import mcp_resource
from myapp.models import Product

@mcp_resource("products://{product_id}")
def get_product_resource(product_id: int) -> str:
    """Get information about a product"""
    product = Product.objects.get(id=product_id)

    # Return markdown for better LLM consumption
    return f"""# {product.name}

**Price**: ${product.price}
**Category**: {product.category}
**In Stock**: {"Yes" if product.in_stock else "No"}

## Description

{product.description}

## Specifications

{product.specifications}
"""
```

### Prompts

Prompts provide pre-defined templates for the AI assistant. Create them with the `@mcp_prompt` decorator:

```python
from django_mcp.decorators import mcp_prompt

@mcp_prompt(name="order_summary")
def get_order_summary_prompt(order_id: int) -> str:
    """Generate a prompt for summarizing an order"""
    from myapp.models import Order

    order = Order.objects.get(id=order_id)
    items = order.items.all()

    items_text = "\n".join([f"- {item.quantity}x {item.product.name}" for item in items])

    return f"""Please summarize this order in a friendly, conversational way:

Order #{order.id}
Status: {order.status}
Date: {order.created_at.strftime('%Y-%m-%d')}
Customer: {order.customer.name}

Items:
{items_text}

Total: ${order.total}
"""
```

## 🔄 Model Integration

Django-MCP makes it easy to expose your Django models:

### Automatic CRUD Tools

Create CRUD tools for a model automatically:

```python
from django_mcp.decorators import mcp_model_tool
from myapp.models import Product

@mcp_model_tool(Product)
def product_tools():
    """Create standard CRUD tools for Product model"""
    pass
```

This creates the following tools:

- `get_product_instance` - Get a product by ID
- `list_product_instances` - List products
- `search_product_instances` - Search for products
- `create_product_instance` - Create a new product

### Model Resources

Expose model instances as resources:

```python
from django_mcp.decorators import mcp_model_resource
from myapp.models import Product

@mcp_model_resource(Product, lookup="slug", fields=["name", "price", "description"])
def product_resource():
    """Expose Product instances as resources"""
    pass
```

This creates a resource with URI template `myapp://product/{slug}`.

## 🛡️ Admin Integration

Expose your Django admin functionality:

```python
from django_mcp.admin import register_admin_tools
from myapp.admin import ProductAdmin
from myapp.models import Product

# Register all admin actions for Product
register_admin_tools(ProductAdmin, Product)
```

For the admin site itself:

```python
from django_mcp.admin import register_admin_site
from django.contrib.admin.sites import site

# Register the admin site
register_admin_site(site)
```

## 🌐 DRF Integration

Expose your Django REST Framework ViewSets:

```python
from django_mcp.drf import register_viewset
from myapp.api.viewsets import ProductViewSet

# Expose all viewset actions as tools
register_viewset(ProductViewSet)
```

This creates tools for each action in the viewset (list, retrieve, create, etc.)

## 🔍 Auto-Discovery

Django-MCP automatically discovers MCP components in your Django apps. Just create files with the appropriate naming conventions:

- `mcp_tools.py` - For tools
- `mcp_resources.py` - For resources
- `mcp_prompts.py` - For prompts

Example:

```
myapp/
  __init__.py
  models.py
  views.py
  mcp_tools.py      # Automatically discovered!
  mcp_resources.py  # Automatically discovered!
  mcp_prompts.py    # Automatically discovered!
```

## 🧙‍♀️ Advanced Usage

### Custom Context

Pass context to your tools and resources:

```python
from django_mcp.decorators import mcp_tool
from django_mcp.context import Context

@mcp_tool()
async def process_data(data: str, ctx: Context) -> str:
    """Process data with progress reporting"""
    # Report progress to the client
    await ctx.report_progress(0, 100)

    # Log information
    ctx.info(f"Processing {len(data)} bytes of data")

    # Process the data (simulated)
    await asyncio.sleep(1)
    await ctx.report_progress(50, 100)
    await asyncio.sleep(1)
    await ctx.report_progress(100, 100)

    return f"Processed {len(data)} bytes of data"
```

### Custom Transports

Configure custom transport options:

```python
# settings.py

# Use custom SSE settings
DJANGO_MCP_SSE_KEEPALIVE = 30  # Send keepalive every 30 seconds
DJANGO_MCP_SSE_RETRY = 3000    # Retry connection after 3 seconds
```

### Manual Registration

Manually register components instead of using decorators:

```python
from django_mcp.server import get_mcp_server

# Get the server instance
mcp_server = get_mcp_server()

# Register a tool
mcp_server.register_tool(
    name="my_tool",
    func=my_tool_function,
    description="My custom tool",
    parameters=[
        {"name": "param1", "type": "string", "description": "First parameter"}
    ]
)

# Register a resource
mcp_server.register_resource(
    uri_template="custom://{id}",
    func=my_resource_function,
    description="My custom resource"
)
```

## 🩺 Troubleshooting

### Common Issues

#### MCP Server Not Starting

If the MCP server isn't starting, check:

- Is `django_mcp` in your `INSTALLED_APPS`?
- Are you using the correct ASGI application?
- Is there another server running on the same port?

#### Components Not Discovered

If your components aren't being discovered:

- Check that they're in the correct files (`mcp_tools.py`, etc.)
- Check that your app is in `INSTALLED_APPS`
- Try using the `mcp_inspect` management command

#### Runtime Errors

If you're seeing errors when tools or resources are called:

- Check for exceptions in your tool/resource functions
- Ensure your models exist and are accessible
- Check that the current user has the necessary permissions

### Debugging Tools

Django-MCP includes management commands for debugging:

```bash
# Inspect MCP components
python manage.py mcp_inspect

# Run the MCP server directly (for debugging)
python manage.py mcp_run
```

### Dashboard

Django-MCP includes a dashboard for inspecting your MCP server:

```
http://localhost:8000/mcp/dashboard/
```

The dashboard shows:

- All registered tools
- All registered resources
- All registered prompts
- Connection status
- Configuration

## 🔮 Next Steps

Now that you've got Django-MCP up and running, here are some next steps:

1. **Explore the Examples**: Check out the example projects in the documentation
2. **Add More Tools**: Identify key functionality in your app to expose as tools
3. **Create Resources**: Expose your app's data as rich, structured resources
4. **Integrate with AI Assistants**: Connect your MCP server to Claude or other AI assistants
5. **Contribute**: Join the community and contribute to Django-MCP!
