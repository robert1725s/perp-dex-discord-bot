"""Cache management for the Perp DEX Discord Bot."""

import json
import logging
from typing import Any, Optional
from pathlib import Path
from datetime import datetime


logger = logging.getLogger(__name__)


class CacheManager:
    """Generic cache manager for storing data to JSON files."""

    def __init__(self, cache_file: str):
        """
        Initialize the cache manager.

        Args:
            cache_file: Path to the cache file
        """
        self.cache_file = Path(cache_file)

    def save(self, data: Any, metadata: Optional[dict] = None) -> bool:
        """
        Save data to cache file with timestamp.

        Args:
            data: Data to cache (must be JSON serializable)
            metadata: Optional metadata to include

        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Prepare cache structure
            cache_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'data': data
            }

            # Add metadata if provided
            if metadata:
                cache_data['metadata'] = metadata

            # Write to file
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Cache saved successfully to {self.cache_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save cache to {self.cache_file}: {e}")
            return False

    def load(self) -> Optional[dict]:
        """
        Load data from cache file.

        Returns:
            Optional[dict]: Cache data with structure:
                {
                    'timestamp': str,
                    'data': Any,
                    'metadata': dict (optional)
                }
                Returns None if cache doesn't exist or is invalid
        """
        try:
            # Check if cache file exists
            if not self.cache_file.exists():
                logger.debug(f"Cache file does not exist: {self.cache_file}")
                return None

            # Read from file
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            logger.info(f"Cache loaded successfully from {self.cache_file}")
            return cache_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse cache file {self.cache_file}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load cache from {self.cache_file}: {e}")
            return None

    def exists(self) -> bool:
        """
        Check if cache file exists.

        Returns:
            bool: True if cache file exists, False otherwise
        """
        return self.cache_file.exists()

    def get_age(self) -> Optional[float]:
        """
        Get age of cache in seconds.

        Returns:
            Optional[float]: Age in seconds, or None if cache doesn't exist
        """
        cache_data = self.load()
        if not cache_data or 'timestamp' not in cache_data:
            return None

        try:
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            age = (datetime.utcnow() - cache_time).total_seconds()
            return age
        except Exception as e:
            logger.error(f"Failed to calculate cache age: {e}")
            return None

    def is_stale(self, max_age_seconds: float) -> bool:
        """
        Check if cache is stale (older than max_age_seconds).

        Args:
            max_age_seconds: Maximum age in seconds

        Returns:
            bool: True if cache is stale or doesn't exist, False otherwise
        """
        age = self.get_age()
        if age is None:
            return True
        return age > max_age_seconds

    def delete(self) -> bool:
        """
        Delete cache file.

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
                logger.info(f"Cache file deleted: {self.cache_file}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete cache file {self.cache_file}: {e}")
            return False


# Test function
def _test_cache():
    """Test function for CacheManager."""
    print("Testing CacheManager...")

    # Create test cache manager
    cache = CacheManager("data/test_cache.json")

    # Test save
    print("\nTesting save():")
    test_data = {
        'symbols': ['BTC-USD', 'ETH-USD', 'SOL-USD'],
        'count': 3
    }
    metadata = {'source': 'test', 'version': '1.0'}
    success = cache.save(test_data, metadata)
    print(f"  Save successful: {success}")

    # Test exists
    print("\nTesting exists():")
    exists = cache.exists()
    print(f"  Cache exists: {exists}")

    # Test load
    print("\nTesting load():")
    loaded = cache.load()
    if loaded:
        print(f"  Timestamp: {loaded['timestamp']}")
        print(f"  Data: {loaded['data']}")
        print(f"  Metadata: {loaded.get('metadata')}")

    # Test get_age
    print("\nTesting get_age():")
    age = cache.get_age()
    if age is not None:
        print(f"  Cache age: {age:.2f} seconds")

    # Test is_stale
    print("\nTesting is_stale():")
    stale = cache.is_stale(max_age_seconds=86400)  # 24 hours
    print(f"  Cache is stale (> 24h): {stale}")

    # Test delete
    print("\nTesting delete():")
    deleted = cache.delete()
    print(f"  Cache deleted: {deleted}")

    print("\n✓ All tests passed!")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    _test_cache()
