"""Lighter Exchange implementation for the Perp DEX Discord Bot."""

import asyncio
import logging
from typing import List, Dict, Optional
import aiohttp
from .base import BaseExchange


logger = logging.getLogger(__name__)


class LighterExchange(BaseExchange):
    """Lighter Exchange (zkSync) implementation."""

    def __init__(self, config: Dict):
        """
        Initialize Lighter Exchange.

        Args:
            config: Exchange configuration dictionary
        """
        super().__init__(config)
        self.rate_limit = self.config.get('rate_limit', 500)
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.max_retries = 3
        self.retry_delay = 1  # Initial retry delay in seconds

    async def get_markets(self) -> List[Dict]:
        """
        Fetch all market information from Lighter Exchange.

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
        # Fetch order book details (includes volume, OI, price)
        order_book_details = await self._fetch_order_book_details()
        if not order_book_details:
            return []

        # Fetch funding rates
        funding_rates = await self._fetch_funding_rates()

        # Merge data
        markets = []
        for details in order_book_details:
            try:
                parsed_market = self._parse_market(details, funding_rates)
                if parsed_market:
                    markets.append(parsed_market)
            except Exception as e:
                logger.warning(f"Failed to parse market {details.get('symbol')}: {e}")
                continue

        logger.info(f"Successfully fetched {len(markets)} markets from Lighter")
        return markets

    async def _fetch_order_book_details(self) -> List[Dict]:
        """
        Fetch order book details from Lighter API.

        Returns:
            List[Dict]: List of order book details
        """
        url = f"{self.api_base_url}/orderBookDetails"

        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        data = await response.json()

                        # Validate response code
                        if data.get('code') != 200:
                            logger.warning(f"Lighter API returned non-200 code: {data.get('code')}")
                            return []

                        return data.get('order_book_details', [])

            except aiohttp.ClientError as e:
                logger.warning(f"Lighter orderBookDetails request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Lighter orderBookDetails request failed after {self.max_retries} attempts")
                    return []
            except Exception as e:
                logger.error(f"Unexpected error fetching Lighter order book details: {e}")
                return []

        return []

    async def _fetch_funding_rates(self) -> Dict[int, float]:
        """
        Fetch funding rates from Lighter API.

        Returns:
            Dict[int, float]: Mapping of market_id to funding rate
        """
        url = f"{self.api_base_url}/funding-rates"

        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        data = await response.json()

                        # Validate response code
                        if data.get('code') != 200:
                            logger.warning(f"Lighter funding-rates API returned non-200 code: {data.get('code')}")
                            return {}

                        # Build market_id -> funding_rate mapping
                        funding_map = {}
                        for fr_data in data.get('funding_rates', []):
                            market_id = fr_data.get('market_id')
                            rate = fr_data.get('rate')
                            if market_id is not None and rate is not None:
                                funding_map[market_id] = float(rate)

                        return funding_map

            except aiohttp.ClientError as e:
                logger.warning(f"Lighter funding-rates request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Lighter funding-rates request failed after {self.max_retries} attempts")
                    return {}
            except Exception as e:
                logger.error(f"Unexpected error fetching Lighter funding rates: {e}")
                return {}

        return {}

    def _parse_market(self, details: Dict, funding_rates: Dict[int, float]) -> Optional[Dict]:
        """
        Parse a single market from Lighter API response.

        Args:
            details: Order book details from API
            funding_rates: Mapping of market_id to funding rate

        Returns:
            Optional[Dict]: Parsed market data or None if invalid
        """
        try:
            symbol = details.get('symbol')
            market_id = details.get('market_id')
            status = details.get('status')

            # Only include active markets
            if status != 'active':
                logger.debug(f"Skipping inactive market {symbol}")
                return None

            # Extract required fields
            daily_quote_volume = details.get('daily_quote_token_volume')
            open_interest = details.get('open_interest')
            last_trade_price = details.get('last_trade_price')

            # Check for missing data
            if not all([symbol, market_id is not None, daily_quote_volume, open_interest, last_trade_price]):
                logger.debug(f"Skipping market {symbol} due to missing data")
                return None

            # Convert to floats
            volume_24h = float(daily_quote_volume)
            oi_quantity = float(open_interest)
            price = float(last_trade_price)

            # Calculate Open Interest in USD
            # Lighter returns OI as quantity, so multiply by last price
            oi_usd = oi_quantity * price

            # Get funding rate (default to 0 if not available)
            funding_rate = funding_rates.get(market_id, 0.0)

            # Validate values
            if volume_24h < 0 or oi_usd < 0:
                logger.debug(f"Skipping market {symbol} due to invalid values")
                return None

            # Normalize symbol
            normalized_symbol = self.normalize_symbol(symbol)

            return {
                'symbol': normalized_symbol,
                'volume_24h': volume_24h,
                'funding_rate': funding_rate,
                'open_interest': oi_usd,
                'last_price': price
            }

        except (ValueError, TypeError) as e:
            logger.debug(f"Error parsing market data: {e}")
            return None

    def normalize_symbol(self, raw_symbol: str) -> str:
        """
        Normalize Lighter symbol format.

        Lighter uses the format "BTC" (base token only), which needs to be
        converted to "BTC-USD" format.

        Args:
            raw_symbol: Lighter symbol (e.g., "BTC", "ETH")

        Returns:
            str: Normalized symbol (e.g., "BTC-USD", "ETH-USD")
        """
        # Lighter uses base token only, append -USD for standardization
        raw_symbol = raw_symbol.upper()

        # Handle special cases for forex pairs that already include quote currency
        if raw_symbol in ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCAD', 'USDCHF']:
            # These are already in the right format, just add hyphen
            # EURUSD -> EUR-USD
            return f"{raw_symbol[:3]}-{raw_symbol[3:]}"

        # For crypto pairs, append -USD
        return f"{raw_symbol}-USD"


# Test stub function
async def _test_lighter():
    """Test function for Lighter Exchange."""
    print("Testing Lighter Exchange...")

    # Test configuration
    config = {
        'name': 'Lighter',
        'api_base_url': 'https://mainnet.zklighter.elliot.ai/api/v1',
        'config': {
            'rate_limit': 500
        }
    }

    # Create exchange instance
    exchange = LighterExchange(config)

    # Test normalize_symbol
    print("\nTesting normalize_symbol():")
    test_symbols = ["BTC", "eth", "SOL", "EURUSD", "GBPUSD"]
    for symbol in test_symbols:
        normalized = exchange.normalize_symbol(symbol)
        print(f"  {symbol} -> {normalized}")

    # Test get_markets
    print("\nTesting get_markets():")
    try:
        markets = await exchange.get_markets()
        print(f"  Fetched {len(markets)} markets")

        # Display first 5 markets
        if markets:
            print("\nFirst 5 markets:")
            for market in markets[:5]:
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
    asyncio.run(_test_lighter())
