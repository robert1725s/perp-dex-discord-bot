"""Market data analysis for the Perp DEX Discord Bot."""

import logging
from typing import List, Dict
from .types import MarketData


logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """Market data analysis class for analyzing funding rates and OI ratios."""

    def find_top_fr_divergence(
        self,
        markets_a: List[MarketData],
        markets_b: List[MarketData],
        min_volume: float = 1_000_000,
        top_n: int = 5
    ) -> List[Dict]:
        """
        Find pairs with the largest funding rate divergence.

        Args:
            markets_a: Market data from exchange A
            markets_b: Market data from exchange B
            min_volume: Minimum 24h volume in USD (default: 1M USD)
            top_n: Number of top results to return (default: 5)

        Returns:
            List[Dict]: Pairs sorted by FR divergence (descending)
            [
                {
                    'symbol': 'BTC-USD',
                    'exchange_a': 'Extended',
                    'fr_a': 0.0001,
                    'exchange_b': 'Lighter',
                    'fr_b': 0.0005,
                    'fr_diff': 0.0004,
                    'volume_24h': 5000000.0
                },
                ...
            ]
        """
        # Build symbol-indexed maps for both exchanges
        markets_a_map = {m.symbol: m for m in markets_a}
        markets_b_map = {m.symbol: m for m in markets_b}

        # Find common symbols
        common_symbols = set(markets_a_map.keys()) & set(markets_b_map.keys())

        divergences = []

        for symbol in common_symbols:
            market_a = markets_a_map[symbol]
            market_b = markets_b_map[symbol]

            # Filter by minimum volume (use average of both exchanges)
            avg_volume = (market_a.volume_24h + market_b.volume_24h) / 2
            if avg_volume < min_volume:
                continue

            # Calculate FR difference (absolute value)
            fr_diff = abs(market_a.funding_rate - market_b.funding_rate)

            divergences.append({
                'symbol': symbol,
                'exchange_a': market_a.exchange,
                'fr_a': market_a.funding_rate,
                'exchange_b': market_b.exchange,
                'fr_b': market_b.funding_rate,
                'fr_diff': fr_diff,
                'volume_24h': avg_volume
            })

        # Sort by FR difference (descending)
        divergences.sort(key=lambda x: x['fr_diff'], reverse=True)

        # Return top N
        result = divergences[:top_n]

        logger.info(
            f"Found {len(result)} FR divergence pairs "
            f"(filtered from {len(divergences)} common pairs)"
        )

        return result

    def find_low_oi_ratio(
        self,
        markets: List[MarketData],
        min_volume: float = 10_000_000,
        max_volume: float = 30_000_000,
        top_n: int = 3,
        max_oi_ratio: float = 1.0
    ) -> List[Dict]:
        """
        Find pairs with low OI ratio (OI / Volume).

        Args:
            markets: Market data
            min_volume: Minimum 24h volume in USD (default: 10M USD)
            max_volume: Maximum 24h volume in USD (default: 30M USD)
            top_n: Number of top results to return (default: 3)
            max_oi_ratio: Maximum OI/Volume ratio (default: 1.0)

        Returns:
            List[Dict]: Pairs sorted by OI ratio (ascending)
            [
                {
                    'symbol': 'ETH-USD',
                    'volume_24h': 25000000.0,
                    'open_interest': 15000000.0,
                    'oi_volume_ratio': 0.6,
                    'funding_rate': 0.0002
                },
                ...
            ]
        """
        candidates = []

        for market in markets:
            # Filter by volume range
            if market.volume_24h < min_volume or market.volume_24h > max_volume:
                continue

            # Calculate OI / Volume ratio
            # Avoid division by zero
            if market.volume_24h == 0:
                continue

            oi_volume_ratio = market.open_interest / market.volume_24h

            # Filter by OI ratio
            if oi_volume_ratio > max_oi_ratio:
                continue

            candidates.append({
                'symbol': market.symbol,
                'volume_24h': market.volume_24h,
                'open_interest': market.open_interest,
                'oi_volume_ratio': oi_volume_ratio,
                'funding_rate': market.funding_rate
            })

        # Sort by OI ratio (ascending - lowest first)
        candidates.sort(key=lambda x: x['oi_volume_ratio'])

        # Return top N
        result = candidates[:top_n]

        logger.info(
            f"Found {len(result)} low OI ratio pairs "
            f"(filtered from {len(candidates)} candidates)"
        )

        return result


# Test function
def _test_analyzer():
    """Test function for MarketAnalyzer."""
    print("Testing MarketAnalyzer...")

    analyzer = MarketAnalyzer()

    # Create test data for FR divergence
    print("\nTest 1: find_top_fr_divergence()")

    markets_extended = [
        MarketData(
            symbol='BTC-USD',
            exchange='Extended',
            volume_24h=5_000_000,
            funding_rate=0.0001,
            open_interest=50_000_000
        ),
        MarketData(
            symbol='ETH-USD',
            exchange='Extended',
            volume_24h=3_000_000,
            funding_rate=0.0002,
            open_interest=30_000_000
        ),
        MarketData(
            symbol='SOL-USD',
            exchange='Extended',
            volume_24h=500_000,  # Below min_volume
            funding_rate=0.0003,
            open_interest=5_000_000
        ),
    ]

    markets_lighter = [
        MarketData(
            symbol='BTC-USD',
            exchange='Lighter',
            volume_24h=4_500_000,
            funding_rate=0.0005,  # Large difference: 0.0004
            open_interest=45_000_000
        ),
        MarketData(
            symbol='ETH-USD',
            exchange='Lighter',
            volume_24h=2_800_000,
            funding_rate=0.00021,  # Small difference: 0.00001
            open_interest=28_000_000
        ),
        MarketData(
            symbol='DOGE-USD',
            exchange='Lighter',
            volume_24h=2_000_000,
            funding_rate=0.0001,
            open_interest=20_000_000
        ),
    ]

    fr_results = analyzer.find_top_fr_divergence(
        markets_extended,
        markets_lighter,
        min_volume=1_000_000,
        top_n=5
    )

    print(f"  Found {len(fr_results)} FR divergence pairs:")
    for i, result in enumerate(fr_results, 1):
        print(f"  {i}. {result['symbol']}")
        print(f"     {result['exchange_a']}: FR={result['fr_a']:.4%}")
        print(f"     {result['exchange_b']}: FR={result['fr_b']:.4%}")
        print(f"     Difference: {result['fr_diff']:.4%}")
        print(f"     Avg Volume: ${result['volume_24h']:,.0f}")

    # Validate results
    assert len(fr_results) == 2, f"Expected 2 results, got {len(fr_results)}"
    assert fr_results[0]['symbol'] == 'BTC-USD', "BTC-USD should be first (largest diff)"
    assert fr_results[1]['symbol'] == 'ETH-USD', "ETH-USD should be second"
    print("  ✓ Test passed")

    # Create test data for low OI ratio
    print("\nTest 2: find_low_oi_ratio()")

    markets_for_oi = [
        MarketData(
            symbol='BTC-USD',
            exchange='Extended',
            volume_24h=25_000_000,
            funding_rate=0.0001,
            open_interest=15_000_000  # OI ratio: 0.6
        ),
        MarketData(
            symbol='ETH-USD',
            exchange='Extended',
            volume_24h=20_000_000,
            funding_rate=0.0002,
            open_interest=5_000_000  # OI ratio: 0.25 (lowest)
        ),
        MarketData(
            symbol='SOL-USD',
            exchange='Extended',
            volume_24h=15_000_000,
            funding_rate=0.0003,
            open_interest=10_000_000  # OI ratio: 0.67
        ),
        MarketData(
            symbol='DOGE-USD',
            exchange='Extended',
            volume_24h=5_000_000,  # Below min_volume
            funding_rate=0.0001,
            open_interest=1_000_000
        ),
        MarketData(
            symbol='AVAX-USD',
            exchange='Extended',
            volume_24h=35_000_000,  # Above max_volume
            funding_rate=0.0002,
            open_interest=10_000_000
        ),
    ]

    oi_results = analyzer.find_low_oi_ratio(
        markets_for_oi,
        min_volume=10_000_000,
        max_volume=30_000_000,
        top_n=3
    )

    print(f"  Found {len(oi_results)} low OI ratio pairs:")
    for i, result in enumerate(oi_results, 1):
        print(f"  {i}. {result['symbol']}")
        print(f"     Volume: ${result['volume_24h']:,.0f}")
        print(f"     Open Interest: ${result['open_interest']:,.0f}")
        print(f"     OI/Volume Ratio: {result['oi_volume_ratio']:.2f}")
        print(f"     Funding Rate: {result['funding_rate']:.4%}")

    # Validate results
    assert len(oi_results) == 3, f"Expected 3 results, got {len(oi_results)}"
    assert oi_results[0]['symbol'] == 'ETH-USD', "ETH-USD should be first (lowest ratio)"
    assert oi_results[0]['oi_volume_ratio'] < oi_results[1]['oi_volume_ratio'], \
        "Results should be sorted by ratio (ascending)"
    print("  ✓ Test passed")

    # Test edge cases
    print("\nTest 3: Edge cases")

    # Empty lists
    empty_result = analyzer.find_top_fr_divergence([], [], min_volume=1_000_000)
    assert empty_result == [], "Empty input should return empty result"
    print("  ✓ Empty input handled correctly")

    # No common symbols
    markets_1 = [MarketData('BTC-USD', 'Ex1', 1_000_000, 0.0001, 10_000_000)]
    markets_2 = [MarketData('ETH-USD', 'Ex2', 1_000_000, 0.0001, 10_000_000)]
    no_common_result = analyzer.find_top_fr_divergence(markets_1, markets_2)
    assert no_common_result == [], "No common symbols should return empty result"
    print("  ✓ No common symbols handled correctly")

    # All filtered by volume
    low_volume_markets = [
        MarketData('BTC-USD', 'Ex', 100_000, 0.0001, 1_000_000)
    ]
    filtered_result = analyzer.find_low_oi_ratio(
        low_volume_markets,
        min_volume=10_000_000
    )
    assert filtered_result == [], "All filtered by volume should return empty result"
    print("  ✓ Volume filtering handled correctly")

    print("\n✓ All tests passed!")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    _test_analyzer()
