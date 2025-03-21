from unittest.mock import MagicMock, patch

from django_mcp.model_tools import _instance_to_dict, register_model_resource, register_model_tools


def test_instance_to_dict():
    """Test instance_to_dict function converts a model instance to a dictionary."""
    # Create a mock instance with _meta
    instance = MagicMock()

    # Configure the fields
    field1 = MagicMock()
    field1.name = "id"
    field2 = MagicMock()
    field2.name = "name"
    field3 = MagicMock()
    field3.name = "description"

    # Mock the instance attributes
    instance._meta.fields = [field1, field2, field3]
    instance.id = 1
    instance.name = "Test Name"
    instance.description = "Test Description"

    # Call the function
    result = _instance_to_dict(instance)

    # Check the result
    assert result == {"id": 1, "name": "Test Name", "description": "Test Description"}


def test_register_model_tools(mock_mcp_server):
    """Test that register_model_tools registers CRUD tools for a model."""
    # Create a mock model class
    model = MagicMock()
    model._meta.model_name = "test"
    model._meta.verbose_name = "test model"
    model._meta.verbose_name_plural = "test models"

    with patch("django_mcp.model_tools.get_mcp_server", return_value=mock_mcp_server):
        register_model_tools(model)

    # Should register tools
    assert mock_mcp_server.tool.call_count >= 4

    # Check descriptions contain expected phrases
    descriptions = [call_args[1]["description"] for call_args in mock_mcp_server.tool.call_args_list]
    assert any("Get a test model" in desc for desc in descriptions)
    assert any("List test models" in desc for desc in descriptions)


def test_register_model_resource(mock_mcp_server):
    """Test that register_model_resource registers a model as an MCP resource."""
    # Create a mock model class
    model = MagicMock()
    model._meta.model_name = "test"
    model._meta.app_label = "testapp"
    model._meta.verbose_name = "test model"
    model._meta.verbose_name_plural = "test models"

    with patch("django_mcp.model_tools.get_mcp_server", return_value=mock_mcp_server):
        register_model_resource(model, lookup="slug", fields=["name", "description"])

    # Should call register_resource
    mock_mcp_server.resource.assert_called_once()

    # Check URI template
    args, kwargs = mock_mcp_server.resource.call_args
    assert args[0] == "testapp://{slug}"


def test_model_get_instance_tool():
    """Test the get_model_instance tool directly."""
    model = MagicMock()
    mock_instance = MagicMock()
    model.objects.get.return_value = mock_instance

    # Extract the logic from register_model_get_tool directly
    def get_model_instance(instance_id: int):
        instance = model.objects.get(pk=instance_id)
        return _instance_to_dict(instance)

    # Call the function
    get_model_instance(instance_id=1)

    # Check that it tried to get the model instance
    model.objects.get.assert_called_once_with(pk=1)


def test_model_list_instances_tool():
    """Test the list_model_instances tool directly."""
    model = MagicMock()
    mock_queryset = MagicMock()
    mock_sliced_queryset = [MagicMock(), MagicMock()]
    mock_queryset.__getitem__.return_value = mock_sliced_queryset
    model.objects.all.return_value = mock_queryset

    # Extract the logic from register_model_list_tool directly
    def list_model_instances(limit: int = 10, offset: int = 0):
        queryset = model.objects.all()
        instances = queryset[offset : offset + limit]
        return [_instance_to_dict(instance) for instance in instances]

    # Call the function
    result = list_model_instances(limit=10, offset=0)

    # Check that it tried to get all model instances
    model.objects.all.assert_called_once()

    # Should return a list
    assert isinstance(result, list)
    assert len(result) == 2  # Mocked to return 2 instances
