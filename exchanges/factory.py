"""Exchange factory for the Perp DEX Discord Bot."""

from typing import Dict, Type
from .base import BaseExchange
from .extended import ExtendedExchange
from .lighter import LighterExchange


class ExchangeFactory:
    """Factory class for creating exchange instances."""

    _registry: Dict[str, Type[BaseExchange]] = {
        'extended': ExtendedExchange,
        'lighter': LighterExchange,
        # New exchanges can be added here
    }

    @classmethod
    def create(cls, config: Dict) -> BaseExchange:
        """
        Create an exchange instance from configuration.

        Args:
            config: Exchange configuration dictionary
                Required keys:
                - type: Exchange type identifier (e.g., 'extended', 'lighter')
                - name: Exchange name
                - api_base_url: Base URL for the API
                Optional keys:
                - config: Exchange-specific configuration

        Returns:
            BaseExchange: Exchange instance

        Raises:
            ValueError: If exchange type is not registered
            KeyError: If required config keys are missing
        """
        # Validate required fields
        if 'type' not in config:
            raise KeyError("Config missing required field: 'type'")

        exchange_type = config['type']

        # Check if exchange type is registered
        if exchange_type not in cls._registry:
            available_types = ', '.join(cls._registry.keys())
            raise ValueError(
                f"Unknown exchange type: '{exchange_type}'. "
                f"Available types: {available_types}"
            )

        # Get the exchange class and create instance
        exchange_class = cls._registry[exchange_type]
        return exchange_class(config)

    @classmethod
    def register(cls, exchange_type: str, exchange_class: Type[BaseExchange]):
        """
        Register a new exchange class.

        This allows dynamic registration of new exchanges without modifying
        the factory code.

        Args:
            exchange_type: Exchange type identifier
            exchange_class: Exchange implementation class (must inherit from BaseExchange)

        Raises:
            TypeError: If exchange_class does not inherit from BaseExchange
        """
        # Validate that exchange_class inherits from BaseExchange
        if not issubclass(exchange_class, BaseExchange):
            raise TypeError(
                f"Exchange class must inherit from BaseExchange, "
                f"got {exchange_class.__name__}"
            )

        cls._registry[exchange_type] = exchange_class

    @classmethod
    def get_registered_types(cls) -> list:
        """
        Get list of registered exchange types.

        Returns:
            list: List of registered exchange type identifiers
        """
        return list(cls._registry.keys())


# Test function
def _test_factory():
    """Test function for ExchangeFactory."""
    print("Testing ExchangeFactory...")

    # Test get_registered_types
    print("\nRegistered exchange types:")
    types = ExchangeFactory.get_registered_types()
    for exchange_type in types:
        print(f"  - {exchange_type}")

    # Test create Extended exchange
    print("\nTesting create() for Extended:")
    config_ext = {
        'type': 'extended',
        'name': 'Extended',
        'api_base_url': 'https://api.starknet.extended.exchange/api/v1',
        'config': {
            'rate_limit': 1000
        }
    }
    exchange_ext = ExchangeFactory.create(config_ext)
    print(f"  Created: {exchange_ext.name} ({type(exchange_ext).__name__})")

    # Test create Lighter exchange
    print("\nTesting create() for Lighter:")
    config_lighter = {
        'type': 'lighter',
        'name': 'Lighter',
        'api_base_url': 'https://mainnet.zklighter.elliot.ai/api/v1',
        'config': {
            'rate_limit': 500
        }
    }
    exchange_lighter = ExchangeFactory.create(config_lighter)
    print(f"  Created: {exchange_lighter.name} ({type(exchange_lighter).__name__})")

    # Test error handling - unknown type
    print("\nTesting error handling (unknown type):")
    try:
        config_invalid = {
            'type': 'unknown',
            'name': 'Unknown',
            'api_base_url': 'https://example.com'
        }
        ExchangeFactory.create(config_invalid)
        print("  ERROR: Should have raised ValueError")
    except ValueError as e:
        print(f"  ✓ Correctly raised ValueError: {e}")

    # Test error handling - missing type
    print("\nTesting error handling (missing type):")
    try:
        config_no_type = {
            'name': 'NoType',
            'api_base_url': 'https://example.com'
        }
        ExchangeFactory.create(config_no_type)
        print("  ERROR: Should have raised KeyError")
    except KeyError as e:
        print(f"  ✓ Correctly raised KeyError: {e}")

    # Test register() - mock exchange
    print("\nTesting register() with mock exchange:")

    class MockExchange(BaseExchange):
        """Mock exchange for testing."""

        async def get_markets(self):
            return []

        def normalize_symbol(self, raw_symbol: str) -> str:
            return raw_symbol.upper()

    ExchangeFactory.register('mock', MockExchange)
    print(f"  Registered types: {ExchangeFactory.get_registered_types()}")

    config_mock = {
        'type': 'mock',
        'name': 'MockExchange',
        'api_base_url': 'https://mock.example.com'
    }
    exchange_mock = ExchangeFactory.create(config_mock)
    print(f"  Created: {exchange_mock.name} ({type(exchange_mock).__name__})")

    # Test register() error handling
    print("\nTesting register() error handling (invalid class):")
    try:
        class InvalidExchange:
            """Not a BaseExchange."""
            pass

        ExchangeFactory.register('invalid', InvalidExchange)
        print("  ERROR: Should have raised TypeError")
    except TypeError as e:
        print(f"  ✓ Correctly raised TypeError: {e}")

    print("\n✓ All tests passed!")


if __name__ == '__main__':
    _test_factory()
