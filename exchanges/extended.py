"""Extended Exchange implementation for the Perp DEX Discord Bot."""

import asyncio
import logging
from typing import List, Dict, Optional
import aiohttp
from .base import BaseExchange


logger = logging.getLogger(__name__)


class ExtendedExchange(BaseExchange):
    """Extended Exchange (Starknet) implementation."""

    def __init__(self, config: Dict):
        """
        Initialize Extended Exchange.

        Args:
            config: Exchange configuration dictionary
        """
        super().__init__(config)
        self.rate_limit = self.config.get('rate_limit', 1000)
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.max_retries = 3
        self.retry_delay = 1  # Initial retry delay in seconds

    async def get_markets(self) -> List[Dict]:
        """
        Fetch all market information from Extended Exchange.

        Returns:
            List[Dict]: List of market data dictionaries
            [
                {
                    'symbol': 'BTC-USD',
                    'volume_24h': 1500000.0,
                    'funding_rate': 0.0001,
                    'open_interest': 50000000.0
                },
                ...
            ]
        """
        url = f"{self.api_base_url}/info/markets"

        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        data = await response.json()

                        # Validate response status (case-insensitive)
                        status = data.get('status', '').lower()
                        if status not in ['ok', 'success']:
                            logger.warning(f"Extended API returned non-ok status: {data.get('status')}")
                            return []

                        # Parse markets
                        markets = []
                        for market in data.get('data', []):
                            try:
                                parsed_market = self._parse_market(market)
                                if parsed_market:
                                    markets.append(parsed_market)
                            except Exception as e:
                                logger.warning(f"Failed to parse market {market.get('name')}: {e}")
                                continue

                        logger.info(f"Successfully fetched {len(markets)} markets from Extended")
                        return markets

            except aiohttp.ClientError as e:
                logger.warning(f"Extended API request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Extended API request failed after {self.max_retries} attempts")
                    return []
            except Exception as e:
                logger.error(f"Unexpected error fetching Extended markets: {e}")
                return []

        return []

    def _parse_market(self, market: Dict) -> Optional[Dict]:
        """
        Parse a single market from Extended API response.

        Args:
            market: Raw market data from API

        Returns:
            Optional[Dict]: Parsed market data or None if invalid
        """
        try:
            name = market.get('name')
            market_stats = market.get('marketStats', {})

            # Extract and validate required fields
            daily_volume = market_stats.get('dailyVolume')
            funding_rate = market_stats.get('fundingRate')
            open_interest = market_stats.get('openInterest')
            last_price = market_stats.get('lastPrice')

            # Check for missing data
            if not all([name, daily_volume, funding_rate, open_interest, last_price]):
                logger.debug(f"Skipping market {name} due to missing data")
                return None

            # Convert strings to floats
            volume_24h = float(daily_volume)
            fr = float(funding_rate)
            oi_quantity = float(open_interest)
            price = float(last_price)

            # Calculate Open Interest in USD
            # Extended returns OI as quantity, so multiply by last price
            oi_usd = oi_quantity * price

            # Validate values
            if volume_24h < 0 or oi_usd < 0:
                logger.debug(f"Skipping market {name} due to invalid values")
                return None

            # Normalize symbol
            normalized_symbol = self.normalize_symbol(name)

            return {
                'symbol': normalized_symbol,
                'volume_24h': volume_24h,
                'funding_rate': fr,
                'open_interest': oi_usd,
                'last_price': price
            }

        except (ValueError, TypeError) as e:
            logger.debug(f"Error parsing market data: {e}")
            return None

    def normalize_symbol(self, raw_symbol: str) -> str:
        """
        Normalize Extended symbol format.

        Extended uses the format "BTC-USD" which is already the standard format.

        Args:
            raw_symbol: Extended symbol (e.g., "BTC-USD")

        Returns:
            str: Normalized symbol (e.g., "BTC-USD")
        """
        # Extended already uses the standard format
        return raw_symbol.upper()


# Test stub function
async def _test_extended():
    """Test function for Extended Exchange."""
    print("Testing Extended Exchange...")

    # Test configuration
    config = {
        'name': 'Extended',
        'api_base_url': 'https://api.starknet.extended.exchange/api/v1',
        'config': {
            'rate_limit': 1000
        }
    }

    # Create exchange instance
    exchange = ExtendedExchange(config)

    # Test normalize_symbol
    print("\nTesting normalize_symbol():")
    test_symbols = ["BTC-USD", "eth-usd", "SOL-USD"]
    for symbol in test_symbols:
        normalized = exchange.normalize_symbol(symbol)
        print(f"  {symbol} -> {normalized}")

    # Test get_markets
    print("\nTesting get_markets():")
    try:
        markets = await exchange.get_markets()
        print(f"  Fetched {len(markets)} markets")

        # Display first 3 markets
        if markets:
            print("\nFirst 3 markets:")
            for market in markets[:3]:
                print(f"  Symbol: {market['symbol']}")
                print(f"    Volume 24h: ${market['volume_24h']:,.2f}")
                print(f"    Funding Rate: {market['funding_rate']:.4%}")
                print(f"    Open Interest: ${market['open_interest']:,.2f}")
                if 'last_price' in market:
                    print(f"    Last Price: ${market['last_price']:,.2f}")
                print()
    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run test
    asyncio.run(_test_extended())
