# ✨ Django-MCP 🔮

<div align="center">

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-9D00FF.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Django 4.0+](https://img.shields.io/badge/django-4.0+-FF00FF.svg?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-Apache--2.0-FF00FF.svg?style=for-the-badge&logo=apache&logoColor=white)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-FF3366.svg?style=for-the-badge&logo=statuspage&logoColor=white)](docs/plan.md)
[![Style](https://img.shields.io/badge/code_style-ruff-00FFFF.svg?style=for-the-badge&logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)
[![Types](https://img.shields.io/badge/type_checker-mypy-00FF88.svg?style=for-the-badge&logo=python&logoColor=white)](https://mypy-lang.org/)

**Supercharge your Django apps with AI assistant capabilities**

</div>

Django-MCP bridges the gap between Django applications and AI assistants by implementing the [Model Context Protocol (MCP)](https://docs.anthropic.com/claude/docs/model-context-protocol-mcp). With a few simple decorators, you can expose your app's data and functionality to AI assistants, creating richer, more capable AI interactions.

Want AI to help users explore your data, perform admin tasks, or create content? Django-MCP makes it magical! ✨💫🧙‍♀️

## 🌟 Features

- 🔮 **Seamless Integration** - Add MCP to your Django project with minimal configuration
- 🧩 **Decorator-Based API** - Intuitive decorators to expose functions, models, and views
- 📊 **Django ORM Integration** - First-class support for Django models and querysets
- 🛡️ **Admin Integration** - Expose admin actions and panels to AI assistants
- 🌐 **DRF Compatibility** - Works with Django REST Framework viewsets and serializers
- 🔍 **Auto-Discovery** - Automatically finds and registers MCP components in your apps
- 🚀 **ASGI Support** - Built-in ASGI server for SSE-based MCP communication
- ⚙️ **Flexible Configuration** - Configure through familiar Django settings
- 🔒 **Security-Focused** - Safe by default with clear permission controls
- 📝 **Contextual Awareness** - MCP server understands Django request context

## 🚀 Installation

```bash
# Install with pip
pip install django-mcp

# Or with UV
uv add django-mcp
```

## ⚡ Quick Start

### 1. Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    # ... your other apps ...
    'django_mcp',
]

# MCP Configuration (optional)
DJANGO_MCP_SERVER_NAME = "My Awesome Django App"
DJANGO_MCP_INSTRUCTIONS = "This server provides access to my Django app."
```

### 2. Update your ASGI configuration

```python
# asgi.py
from django_mcp.asgi import get_asgi_application

application = get_asgi_application()
```

### 3. Include MCP URLs

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    # ... your other URLs ...
    path('', include('django_mcp.urls')),
]
```

### 4. Create your first MCP tool

```python
# myapp/mcp_tools.py - automatically discovered!
from django_mcp.decorators import mcp_tool
from django_mcp.context import Context
from myapp.models import Product

@mcp_tool()
def search_products(context: Context, query: str) -> list:
    """Search for products by name"""
    products = Product.objects.filter(name__icontains=query)[:10]
    return [
        {
            "id": p.id,
            "name": p.name,
            "price": str(p.price),
            "description": p.description,
        }
        for p in products
    ]
```

### 5. Expose a Django model

```python
# myapp/models.py
from django.db import models
from django_mcp.decorators import mcp_model_tool, mcp_model_resource

class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()

    def __str__(self):
        return self.name

# Expose CRUD operations for Product model
@mcp_model_tool(Product)
def product_tools():
    pass

# Expose Product instances as resources
@mcp_model_resource(Product)
def product_resource():
    pass
```

### 6. Connect your AI assistant

Point your MCP-compatible AI assistant (like Claude) to:

```
http://yourdomain.com/mcp/
```

Now your AI assistant can use your Django app's functionality!

## 🧙‍♀️ Using with AI Assistants

1. Start your Django server with Django-MCP installed
2. Connect your AI assistant using the MCP protocol URI
3. The AI can now invoke your tools and access your resources!

Example conversation with an AI:

```
User: "How many products do we have in our database priced under $20?"

AI: *uses the search_products tool to find this information*
"I found 15 products under $20. The most popular ones are Product A ($15.99),
Product B ($19.50), and Product C ($12.75). Would you like to see more details
about any of these products?"
```

## 💫 Examples

### Admin Integration

```python
from django_mcp.admin_tools import register_admin_tools
from myapp.admin import ProductAdmin
from myapp.models import Product

# Register all admin actions for Product
register_admin_tools(ProductAdmin, Product)
```

### DRF Integration

```python
from django_mcp.drf_tools import register_drf_viewset
from myapp.api.viewsets import ProductViewSet

# Expose all viewset actions as tools
register_drf_viewset(ProductViewSet)
```

### Creating Resources

```python
from django_mcp.decorators import mcp_resource
from myapp.models import Category

@mcp_resource("category://{slug}")
def get_category(slug: str) -> str:
    """Get information about a product category"""
    category = Category.objects.get(slug=slug)
    products = category.product_set.all()

    return f"""# Category: {category.name}

{category.description}

## Products in this category

{', '.join(p.name for p in products[:10])}

Total products: {products.count()}
"""
```

## 🛠️ Advanced Configuration

Django-MCP offers advanced configuration options through Django settings:

```python
# settings.py

# Core settings
DJANGO_MCP_SERVER_NAME = "My Django App"
DJANGO_MCP_URL_PREFIX = "mcp"  # URL prefix for MCP endpoints
DJANGO_MCP_INSTRUCTIONS = "This server provides access to my Django app."
DJANGO_MCP_DEPENDENCIES = []  # MCP dependencies

# Discovery settings
DJANGO_MCP_AUTO_DISCOVER = True  # Auto-discover MCP components
DJANGO_MCP_EXPOSE_MODELS = True  # Auto-expose Django models
DJANGO_MCP_EXPOSE_ADMIN = True  # Auto-expose Django admin
DJANGO_MCP_EXPOSE_DRF = True  # Auto-expose DRF ViewSets

# Security settings
DJANGO_MCP_ALLOWED_ORIGINS = []  # CORS allowed origins for SSE endpoint
```

## 📊 Dashboard

Django-MCP includes a built-in dashboard at `/mcp/dashboard/` that shows all registered tools, resources, and prompts.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📝 License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

---

<div align="center">

Created by [Stefanie Jane 🌠](https://github.com/hyperb1iss)

If you find Django-MCP useful, [buy me a Monster Ultra Violet ⚡️](https://ko-fi.com/hyperb1iss)

</div>
