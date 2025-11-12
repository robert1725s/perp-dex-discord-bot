"""Base exchange abstract class for the Perp DEX Discord Bot."""

from abc import ABC, abstractmethod
from typing import List, Dict


class BaseExchange(ABC):
    """Abstract base class for all exchange implementations."""

    def __init__(self, config: Dict):
        """
        Initialize the exchange with configuration.

        Args:
            config: Exchange configuration dictionary containing:
                - name: Exchange name
                - api_base_url: Base URL for the API
                - config: Exchange-specific configuration
        """
        self.name = config['name']
        self.api_base_url = config['api_base_url']
        self.config = config.get('config', {})

    @abstractmethod
    async def get_markets(self) -> List[Dict]:
        """
        Fetch all market information from the exchange.

        Returns:
            List[Dict]: List of market information dictionaries
            [
                {
                    'symbol': 'BTC-USD',
                    'volume_24h': 1500000.0,  # USD
                    'funding_rate': 0.0001,    # 0.01%
                    'open_interest': 50000000.0  # USD
                },
                ...
            ]
        """
        pass

    @abstractmethod
    def normalize_symbol(self, raw_symbol: str) -> str:
        """
        Normalize exchange-specific symbol format to a common format.

        Args:
            raw_symbol: Exchange-specific symbol format

        Returns:
            str: Normalized symbol (e.g., 'BTC-USD')
        """
        pass
