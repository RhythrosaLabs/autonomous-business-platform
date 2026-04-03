"""
Dependency Injection Container

Provides centralized dependency management using the dependency_injector pattern.
This makes services easy to test, mock, and swap implementations.
"""

import logging
from functools import lru_cache
from typing import Optional

try:
    from dependency_injector import containers, providers
except ImportError:
    containers = None
    providers = None

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


if containers is not None:

    class Container(containers.DeclarativeContainer):
        """
        Main dependency injection container.

        Provides singleton instances of services and manages their dependencies.
        """

        # Configuration
        config = providers.Singleton(get_settings)

        # Logging
        logger = providers.Singleton(logging.getLogger, "autonomous_business_platform")

        # Core Services (to be added as we refactor)
        # session_manager = providers.Singleton(
        #     UnifiedSessionManager
        # )

        # API Services (examples - to be expanded)
        # replicate_api = providers.Factory(
        #     ReplicateAPI,
        #     api_key=config.provided.ai_models.replicate_api_token
        # )

else:
    Container = None


@lru_cache()
def get_container():
    """
    Get the global container instance.

    Returns:
        Container or None if dependency_injector is not installed
    """
    if Container is None:
        logger.warning("⚠️ dependency_injector not installed - container not available")
        return None
    container = Container()
    container.wire(modules=[__name__])
    logger.info("✅ Dependency injection container initialized")
    return container


def setup_dependencies():
    """
    Set up and configure all dependencies.

    Returns:
        Container or None if dependency_injector is not installed
    """
    container = get_container()

    # Additional setup can go here
    # For example, registering dynamic services

    return container
