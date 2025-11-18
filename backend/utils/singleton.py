"""
Singleton Pattern Utility

Provides a reusable singleton decorator to eliminate boilerplate code
across Phase 3 services.

Usage:
    from utils.singleton import singleton

    @singleton
    class MyService:
        def __init__(self, config: str = "default"):
            self.config = config

    # Get instance (creates on first call)
    service = MyService.get_instance(config="production")

    # Subsequent calls return same instance
    same_service = MyService.get_instance()
"""

from typing import TypeVar, Generic, Optional, Callable, Any, Dict
from threading import Lock

T = TypeVar('T')


class SingletonMeta(type, Generic[T]):
    """
    Thread-safe singleton metaclass.

    This metaclass ensures that only one instance of a class exists.
    It's thread-safe through the use of double-checked locking.
    """

    _instances: Dict[type, Any] = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        """Control instance creation."""
        # Double-checked locking for thread safety
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance

        return cls._instances[cls]

    @classmethod
    def reset_instance(mcs, cls: type) -> None:
        """Reset singleton instance (useful for testing)."""
        with mcs._lock:
            if cls in mcs._instances:
                del mcs._instances[cls]


def singleton(cls: type[T]) -> type[T]:
    """
    Singleton decorator that adds a get_instance() class method.

    This decorator makes a class a singleton and adds a convenient
    get_instance() method that's consistent with the existing codebase pattern.

    Args:
        cls: Class to make a singleton

    Returns:
        Modified class with singleton behavior

    Example:
        @singleton
        class DatabaseConnection:
            def __init__(self, url: str = "default"):
                self.url = url
                self.connected = False

            def connect(self):
                self.connected = True

        # Usage
        db = DatabaseConnection.get_instance(url="postgresql://...")
        db.connect()

        # Same instance returned
        same_db = DatabaseConnection.get_instance()
        assert same_db is db
    """

    # Create metaclass-based singleton
    singleton_cls = SingletonMeta(cls.__name__, (cls,), dict(cls.__dict__))

    # Add get_instance class method for API consistency
    @classmethod
    def get_instance(singleton_cls, *args, **kwargs) -> T:
        """Get or create the singleton instance.

        Args:
            *args: Positional arguments for __init__ (only used on first call)
            **kwargs: Keyword arguments for __init__ (only used on first call)

        Returns:
            Singleton instance
        """
        return singleton_cls(*args, **kwargs)

    # Add reset method for testing
    @classmethod
    def reset_instance(singleton_cls) -> None:
        """Reset the singleton instance (useful for testing).

        After calling this, the next get_instance() call will create a new instance.
        """
        SingletonMeta.reset_instance(singleton_cls)

    # Attach methods to the class
    setattr(singleton_cls, 'get_instance', get_instance)
    setattr(singleton_cls, 'reset_instance', reset_instance)

    return singleton_cls


# Alternative: Simple function-based singleton for backwards compatibility
_global_instances: Dict[str, Any] = {}
_global_lock = Lock()


def get_or_create_singleton(
    name: str,
    factory: Callable[[], T],
    reset: bool = False
) -> T:
    """
    Get or create a global singleton instance by name.

    This function provides the same pattern as the existing Phase 3 code
    (global variables with get_X functions) but centralized.

    Args:
        name: Unique name for this singleton
        factory: Function that creates the instance
        reset: If True, force recreation of instance

    Returns:
        Singleton instance

    Example:
        from services.gemini_client import GeminiClient

        def get_gemini_client() -> GeminiClient:
            return get_or_create_singleton(
                name="gemini_client",
                factory=lambda: GeminiClient()
            )
    """
    global _global_instances

    if reset or name not in _global_instances:
        with _global_lock:
            if reset or name not in _global_instances:
                _global_instances[name] = factory()

    return _global_instances[name]
