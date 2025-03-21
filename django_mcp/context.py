"""
Context utilities for Django-MCP.

This module provides context classes and utilities for working with
MCP context in Django applications.
"""

from collections.abc import Awaitable, Callable
from functools import wraps
import inspect
from typing import Any, ParamSpec, TypeVar, cast

from django.contrib.auth.models import AbstractUser, AnonymousUser
from django.http import HttpRequest

P = ParamSpec("P")
R = TypeVar("R")


class DjangoRequestContext:
    """
    Context class for MCP operations in Django.

    This provides access to the MCP request context, including user,
    request, and other contextual information.
    """

    def __init__(
        self,
        request: HttpRequest | None = None,
        user: AbstractUser | AnonymousUser | None = None,
        mcp_context: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize context.

        Args:
            request: Optional Django request
            user: Optional Django user
            mcp_context: Optional MCP context
        """
        self.request = request
        self.user = user or (request.user if request and hasattr(request, "user") else None)
        self._mcp_context = mcp_context or {}
        self.meta = getattr(request, "META", {}) if request else {}

    @property
    def is_authenticated(self) -> bool:
        """
        Check if the user is authenticated.

        Returns:
            True if the user is authenticated
        """
        if self.user:
            # Don't cast here as it's redundant
            return bool(self.user.is_authenticated)
        return False

    async def report_progress(self, current: int, total: int) -> None:
        """
        Report progress for a long-running operation.

        Args:
            current: Current progress
            total: Total progress
        """
        if not self._mcp_context or "progress_callback" not in self._mcp_context:
            # If no progress callback, just log
            self.info(f"Progress: {current}/{total}")
            return

        # Call progress callback if available
        progress_callback = self._mcp_context.get("progress_callback")
        if callable(progress_callback):
            await progress_callback(current, total)

    def info(self, message: str) -> None:
        """
        Log an informational message.

        Args:
            message: Message to log
        """
        if not self._mcp_context or "log_callback" not in self._mcp_context:
            # If no log callback, use Django logger
            import logging

            logging.getLogger("django_mcp").info(message)
            return

        # Call log callback if available
        log_callback = self._mcp_context.get("log_callback")
        if callable(log_callback):
            log_callback("info", message)

    def warning(self, message: str) -> None:
        """
        Log a warning message.

        Args:
            message: Message to log
        """
        if not self._mcp_context or "log_callback" not in self._mcp_context:
            # If no log callback, use Django logger
            import logging

            logging.getLogger("django_mcp").warning(message)
            return

        # Call log callback if available
        log_callback = self._mcp_context.get("log_callback")
        if callable(log_callback):
            log_callback("warning", message)

    def error(self, message: str) -> None:
        """
        Log an error message.

        Args:
            message: Message to log
        """
        if not self._mcp_context or "log_callback" not in self._mcp_context:
            # If no log callback, use Django logger
            import logging

            logging.getLogger("django_mcp").error(message)
            return

        # Call log callback if available
        log_callback = self._mcp_context.get("log_callback")
        if callable(log_callback):
            log_callback("error", message)

    async def read_resource(self, uri: str) -> tuple[str, str]:
        """
        Read a resource by URI.

        Args:
            uri: Resource URI

        Returns:
            Tuple of (content, mime_type)
        """
        if not self._mcp_context or "resource_callback" not in self._mcp_context:
            # If no resource callback, raise error
            raise ValueError("Resource reading not available in this context")

        # Call resource callback if available
        resource_callback = self._mcp_context.get("resource_callback")
        if callable(resource_callback):
            return cast(tuple[str, str], await resource_callback(uri))

        raise ValueError("Resource reading not available in this context")


def get_django_context(
    context: DjangoRequestContext | dict[str, Any] | Any | None = None,
) -> DjangoRequestContext | None:
    """
    Get or create Django context from various sources.

    Args:
        context: Context object, dictionary with request, or None

    Returns:
        DjangoRequestContext object or None if no valid context
    """
    if context is None:
        return None

    # If already a DjangoRequestContext, return it
    if isinstance(context, DjangoRequestContext):
        return context

    # If a dict with request, create from request
    if isinstance(context, dict) and "request" in context and context["request"] is not None:
        return DjangoRequestContext(request=cast(HttpRequest, context["request"]))

    # If a request object directly, create from it
    if hasattr(context, "META") and hasattr(context, "method"):
        return DjangoRequestContext(request=cast(HttpRequest, context))

    # Otherwise, can't create context
    return None


def with_django_context(func: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator to add Django context to function calls.

    This decorator will convert a context parameter to a DjangoRequestContext
    if not already converted.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    sig = inspect.signature(func)
    has_context_param = "context" in sig.parameters
    is_async = inspect.iscoroutinefunction(func)

    if is_async:
        # Define async wrapper with the same type as the original function
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> R:
            if has_context_param and "context" in kwargs:
                kwargs["context"] = get_django_context(kwargs["context"])
            # For async functions, we need to pass through the Awaitable
            return await cast(Awaitable[R], func(*args, **kwargs))

        return async_wrapper  # type: ignore

    # Define sync wrapper with the same type as the original function
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> R:
        if has_context_param and "context" in kwargs:
            kwargs["context"] = get_django_context(kwargs["context"])
        return func(*args, **kwargs)

    return wrapper
