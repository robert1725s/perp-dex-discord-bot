"""Common pairs management for the Perp DEX Discord Bot."""

import logging
from typing import List, Set, Optional
from storage.cache import CacheManager


logger = logging.getLogger(__name__)


class CommonPairsManager:
    """Manager for finding and caching common trading pairs across exchanges."""

    def __init__(self, cache_file: str = "data/common_pairs.json"):
        """
        Initialize the common pairs manager.

        Args:
            cache_file: Path to the cache file for storing common pairs
        """
        self.cache_manager = CacheManager(cache_file)

    def find_common_pairs(self, symbol_lists: List[List[str]]) -> List[str]:
        """
        Find common symbols across multiple exchanges.

        Uses set intersection to efficiently find symbols that exist in all exchanges.

        Args:
            symbol_lists: List of symbol lists from different exchanges
                Example: [
                    ['BTC-USD', 'ETH-USD', 'SOL-USD'],  # Exchange 1
                    ['BTC-USD', 'ETH-USD', 'DOGE-USD'], # Exchange 2
                ]

        Returns:
            List[str]: Sorted list of common symbols
                Example: ['BTC-USD', 'ETH-USD']
        """
        # Validate input
        if not symbol_lists:
            logger.warning("No symbol lists provided")
            return []

        if len(symbol_lists) < 2:
            logger.warning("Need at least 2 exchanges to find common pairs")
            if len(symbol_lists) == 1:
                return sorted(symbol_lists[0])
            return []

        # Filter out empty lists
        symbol_lists = [lst for lst in symbol_lists if lst]
        if len(symbol_lists) < 2:
            logger.warning("Not enough non-empty symbol lists")
            return []

        # Convert all lists to sets
        symbol_sets = [set(symbols) for symbols in symbol_lists]

        # Find intersection (common symbols)
        common_symbols = symbol_sets[0]
        for symbol_set in symbol_sets[1:]:
            common_symbols = common_symbols.intersection(symbol_set)

        # Convert to sorted list
        result = sorted(common_symbols)

        logger.info(
            f"Found {len(result)} common pairs across {len(symbol_lists)} exchanges"
        )

        return result

    def find_common_pairs_from_exchanges(self, exchanges_data: List[dict]) -> List[str]:
        """
        Find common pairs from exchange market data.

        Args:
            exchanges_data: List of dictionaries with exchange data
                Example: [
                    {
                        'name': 'Extended',
                        'markets': [
                            {'symbol': 'BTC-USD', ...},
                            {'symbol': 'ETH-USD', ...}
                        ]
                    },
                    ...
                ]

        Returns:
            List[str]: Sorted list of common symbols
        """
        symbol_lists = []

        for exchange_data in exchanges_data:
            exchange_name = exchange_data.get('name', 'Unknown')
            markets = exchange_data.get('markets', [])

            if not markets:
                logger.warning(f"No markets found for exchange: {exchange_name}")
                continue

            # Extract symbols
            # markets is a list of MarketData objects, not dicts
            symbols = [market.symbol for market in markets if hasattr(market, 'symbol')]
            symbol_lists.append(symbols)

            logger.debug(f"{exchange_name}: {len(symbols)} markets")

        return self.find_common_pairs(symbol_lists)

    def save_to_cache(self, common_pairs: List[str], metadata: Optional[dict] = None) -> bool:
        """
        Save common pairs to cache file.

        Args:
            common_pairs: List of common symbols
            metadata: Optional metadata (e.g., exchange names, count)

        Returns:
            bool: True if save was successful, False otherwise
        """
        data = {
            'pairs': common_pairs,
            'count': len(common_pairs)
        }

        return self.cache_manager.save(data, metadata)

    def load_from_cache(self) -> Optional[List[str]]:
        """
        Load common pairs from cache file.

        Returns:
            Optional[List[str]]: List of common pairs, or None if cache doesn't exist
        """
        cache_data = self.cache_manager.load()

        if not cache_data:
            return None

        data = cache_data.get('data', {})
        pairs = data.get('pairs', [])

        logger.info(f"Loaded {len(pairs)} common pairs from cache")
        return pairs

    def get_cache_info(self) -> Optional[dict]:
        """
        Get information about the cache.

        Returns:
            Optional[dict]: Cache information including timestamp, age, etc.
                Returns None if cache doesn't exist
        """
        cache_data = self.cache_manager.load()
        if not cache_data:
            return None

        age = self.cache_manager.get_age()

        return {
            'timestamp': cache_data.get('timestamp'),
            'age_seconds': age,
            'pairs_count': cache_data.get('data', {}).get('count', 0),
            'metadata': cache_data.get('metadata', {})
        }

    def is_cache_stale(self, max_age_seconds: float = 86400) -> bool:
        """
        Check if cache is stale.

        Args:
            max_age_seconds: Maximum age in seconds (default: 86400 = 24 hours)

        Returns:
            bool: True if cache is stale or doesn't exist, False otherwise
        """
        return self.cache_manager.is_stale(max_age_seconds)

    def clear_cache(self) -> bool:
        """
        Delete the cache file.

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        return self.cache_manager.delete()


# Test function
def _test_common_pairs():
    """Test function for CommonPairsManager."""
    print("Testing CommonPairsManager...")

    manager = CommonPairsManager("data/test_common_pairs.json")

    # Test find_common_pairs with simple lists
    print("\nTest 1: Simple symbol lists")
    pairs = manager.find_common_pairs([
        ['BTC-USD', 'ETH-USD', 'SOL-USD'],
        ['BTC-USD', 'SOL-USD', 'DOGE-USD']
    ])
    print(f"  Common pairs: {pairs}")
    assert pairs == ['BTC-USD', 'SOL-USD'], f"Expected ['BTC-USD', 'SOL-USD'], got {pairs}"
    print("  ✓ Test passed")

    # Test with 3 exchanges
    print("\nTest 2: Three exchanges")
    pairs = manager.find_common_pairs([
        ['BTC-USD', 'ETH-USD', 'SOL-USD'],
        ['BTC-USD', 'ETH-USD', 'DOGE-USD'],
        ['BTC-USD', 'ETH-USD', 'AVAX-USD']
    ])
    print(f"  Common pairs: {pairs}")
    assert pairs == ['BTC-USD', 'ETH-USD'], f"Expected ['BTC-USD', 'ETH-USD'], got {pairs}"
    print("  ✓ Test passed")

    # Test with no common pairs
    print("\nTest 3: No common pairs")
    pairs = manager.find_common_pairs([
        ['BTC-USD', 'ETH-USD'],
        ['SOL-USD', 'DOGE-USD']
    ])
    print(f"  Common pairs: {pairs}")
    assert pairs == [], f"Expected [], got {pairs}"
    print("  ✓ Test passed")

    # Test save_to_cache
    print("\nTest 4: Save to cache")
    test_pairs = ['BTC-USD', 'ETH-USD', 'SOL-USD']
    metadata = {
        'exchanges': ['Extended', 'Lighter'],
        'exchange_count': 2
    }
    success = manager.save_to_cache(test_pairs, metadata)
    print(f"  Save successful: {success}")
    assert success, "Save failed"
    print("  ✓ Test passed")

    # Test load_from_cache
    print("\nTest 5: Load from cache")
    loaded_pairs = manager.load_from_cache()
    print(f"  Loaded pairs: {loaded_pairs}")
    assert loaded_pairs == test_pairs, f"Expected {test_pairs}, got {loaded_pairs}"
    print("  ✓ Test passed")

    # Test get_cache_info
    print("\nTest 6: Get cache info")
    info = manager.get_cache_info()
    if info:
        print(f"  Timestamp: {info['timestamp']}")
        print(f"  Age: {info['age_seconds']:.2f} seconds")
        print(f"  Pairs count: {info['pairs_count']}")
        print(f"  Metadata: {info['metadata']}")
    print("  ✓ Test passed")

    # Test is_cache_stale
    print("\nTest 7: Check if cache is stale")
    stale = manager.is_cache_stale(max_age_seconds=86400)
    print(f"  Cache is stale (> 24h): {stale}")
    print("  ✓ Test passed")

    # Test find_common_pairs_from_exchanges
    print("\nTest 8: Find common pairs from exchange data")
    exchanges_data = [
        {
            'name': 'Extended',
            'markets': [
                {'symbol': 'BTC-USD', 'volume_24h': 1000000},
                {'symbol': 'ETH-USD', 'volume_24h': 500000},
                {'symbol': 'SOL-USD', 'volume_24h': 200000}
            ]
        },
        {
            'name': 'Lighter',
            'markets': [
                {'symbol': 'BTC-USD', 'volume_24h': 800000},
                {'symbol': 'ETH-USD', 'volume_24h': 400000},
                {'symbol': 'DOGE-USD', 'volume_24h': 100000}
            ]
        }
    ]
    common = manager.find_common_pairs_from_exchanges(exchanges_data)
    print(f"  Common pairs: {common}")
    assert common == ['BTC-USD', 'ETH-USD'], f"Expected ['BTC-USD', 'ETH-USD'], got {common}"
    print("  ✓ Test passed")

    # Cleanup
    print("\nTest 9: Clear cache")
    cleared = manager.clear_cache()
    print(f"  Cache cleared: {cleared}")
    print("  ✓ Test passed")

    print("\n✓ All tests passed!")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    _test_common_pairs()
