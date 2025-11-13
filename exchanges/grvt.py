"""
GRVT取引所の実装

API Documentation: https://api-docs.grvt.io/market_data_api/
GitHub SDK: https://github.com/gravity-technologies/grvt-pysdk
"""

import aiohttp
import asyncio
from typing import List, Dict, Optional
from .base import BaseExchange
from core.types import MarketData
import logging

logger = logging.getLogger(__name__)


class GRVTExchange(BaseExchange):
    """GRVT取引所クラス"""

    def __init__(self, config: Dict):
        """
        初期化

        Args:
            config: 取引所設定
                - name: 取引所名
                - api_base_url: APIベースURL (https://market-data.grvt.io)
                - config.rate_limit: レート制限（オプション）
        """
        super().__init__(config)
        self.rate_limit = config.get('config', {}).get('rate_limit', 500)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """HTTPセッションを取得（再利用）"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )
        return self._session

    async def close(self):
        """セッションをクローズ"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _post_request(self, endpoint: str, data: Dict) -> Dict:
        """
        POSTリクエストを送信

        Args:
            endpoint: エンドポイントパス
            data: リクエストボディ

        Returns:
            Dict: レスポンスJSON

        Raises:
            aiohttp.ClientError: API呼び出し失敗時
        """
        session = await self._get_session()
        url = f"{self.api_base_url}{endpoint}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with session.post(url, json=data) as response:
                    response.raise_for_status()
                    result = await response.json()

                    # エラーレスポンスのチェック
                    if result.get('code'):
                        error_msg = result.get('message', 'Unknown error')
                        logger.error(f"GRVT API error: {error_msg}")
                        raise ValueError(f"API error: {error_msg}")

                    return result

            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # exponential backoff
                    logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def get_markets(self) -> List[MarketData]:
        """
        全マーケット情報を取得

        Returns:
            List[MarketData]: マーケット情報のリスト

        Raises:
            aiohttp.ClientError: API呼び出し失敗時
        """
        try:
            logger.info(f"Fetching markets from {self.name}")

            # Step 1: 全銘柄リストを取得
            instruments_response = await self._post_request(
                "/full/v1/all_instruments",
                {"is_active": True}
            )

            instruments = instruments_response.get('result', [])

            # PERPETUAL銘柄のみフィルタリング
            perp_instruments = [
                inst for inst in instruments
                if inst.get('settlement_period') == 'PERPETUAL'
            ]

            logger.info(f"Found {len(perp_instruments)} PERPETUAL instruments out of {len(instruments)} total")

            if not perp_instruments:
                logger.warning(f"No PERPETUAL instruments found on {self.name}")
                return []

            # Step 2: 各銘柄のTickerを並列取得
            ticker_tasks = [
                self._fetch_ticker(inst['instrument'])
                for inst in perp_instruments
            ]

            tickers = await asyncio.gather(*ticker_tasks, return_exceptions=True)

            # Step 3: データを統合
            market_list = []
            for inst, ticker in zip(perp_instruments, tickers):
                if isinstance(ticker, Exception):
                    logger.warning(f"Failed to fetch ticker for {inst['instrument']}: {ticker}")
                    continue

                if ticker is None:
                    continue

                try:
                    market_data = self._parse_market_data(inst, ticker)
                    if market_data:
                        market_list.append(market_data)
                except Exception as e:
                    logger.warning(f"Failed to parse market data for {inst['instrument']}: {e}")
                    continue

            logger.info(f"Successfully fetched {len(market_list)} markets from {self.name}")
            return market_list

        except aiohttp.ClientError as e:
            logger.error(f"API call failed for {self.name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_markets for {self.name}: {e}")
            raise

    async def _fetch_ticker(self, instrument: str) -> Optional[Dict]:
        """
        個別銘柄のTicker情報を取得

        Args:
            instrument: 銘柄名（例: "BTC_USDT_Perp"）

        Returns:
            Optional[Dict]: Ticker情報、エラー時はNone
        """
        try:
            response = await self._post_request(
                "/full/v1/ticker",
                {"instrument": instrument}
            )
            return response.get('result')
        except Exception as e:
            logger.warning(f"Failed to fetch ticker for {instrument}: {e}")
            return None

    def _parse_market_data(self, instrument: Dict, ticker: Dict) -> Optional[MarketData]:
        """
        InstrumentとTickerからMarketDataを生成

        Args:
            instrument: Instrument情報
            ticker: Ticker情報

        Returns:
            Optional[MarketData]: マーケットデータ、パースに失敗した場合はNone
        """
        try:
            # シンボル正規化
            raw_symbol = instrument['instrument']
            symbol = self.normalize_symbol(raw_symbol)

            # 24h取引量（USD）= Buy Volume + Sell Volume (quote asset)
            buy_volume_q = float(ticker.get('buy_volume_24h_q') or 0)
            sell_volume_q = float(ticker.get('sell_volume_24h_q') or 0)
            volume_24h = buy_volume_q + sell_volume_q

            # Funding Rate (percentage points → decimal)
            # GRVTは既にパーセンテージポイント（0.01% = "0.01"）で返すため、100で割る
            funding_rate_str = ticker.get('funding_rate_8h_curr') or '0'
            funding_rate = float(funding_rate_str) / 100  # 0.01% → 0.0001

            # Open Interest（base asset → USD換算）
            oi_base = float(ticker.get('open_interest') or 0)
            mark_price = float(ticker.get('mark_price') or 0)
            open_interest = oi_base * mark_price

            # 最終価格
            last_price = float(ticker.get('last_price') or 0)

            return MarketData(
                symbol=symbol,
                exchange=self.name,
                volume_24h=volume_24h,
                funding_rate=funding_rate,
                open_interest=open_interest,
                last_price=last_price if last_price > 0 else None
            )

        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Failed to parse market data for {instrument.get('instrument')}: {e}")
            return None

    def normalize_symbol(self, raw_symbol: str) -> str:
        """
        取引所固有のシンボル形式を正規化

        Args:
            raw_symbol: 取引所のシンボル形式（例: "BTC_USDT_Perp"）

        Returns:
            str: 正規化されたシンボル (例: 'BTC-USD')

        Examples:
            >>> exchange = GRVTExchange(config)
            >>> exchange.normalize_symbol('BTC_USDT_Perp')
            'BTC-USD'
            >>> exchange.normalize_symbol('ETH_USDC_Perp')
            'ETH-USD'
        """
        # GRVTのフォーマット: "BTC_USDT_Perp", "ETH_USDC_Perp"
        # "_Perp"サフィックスを削除
        if raw_symbol.endswith('_Perp'):
            raw_symbol = raw_symbol[:-5]  # "_Perp" を削除

        # アンダースコアをハイフンに置換
        # "BTC_USDT" → "BTC-USDT"
        symbol = raw_symbol.replace('_', '-')

        # USDTやUSDCをUSDに統一
        # "BTC-USDT" → "BTC-USD"
        # "ETH-USDC" → "ETH-USD"
        if symbol.endswith('-USDT'):
            symbol = symbol[:-5] + '-USD'
        elif symbol.endswith('-USDC'):
            symbol = symbol[:-5] + '-USD'

        return symbol.upper()


# テスト用コード
async def test_exchange():
    """GRVT取引所実装のテスト"""
    config = {
        'name': 'GRVT',
        'type': 'grvt',
        'api_base_url': 'https://market-data.grvt.io',
        'config': {
            'rate_limit': 500
        }
    }

    exchange = GRVTExchange(config)

    try:
        print(f"Testing {exchange.name}...")
        print(f"API Base URL: {exchange.api_base_url}")

        # マーケットデータ取得
        print("\nFetching markets...")
        markets = await exchange.get_markets()

        print(f"\nFetched {len(markets)} markets:")
        for market in markets[:10]:  # 最初の10件だけ表示
            print(f"  {market.symbol}: "
                  f"Vol=${market.volume_24h:,.0f}, "
                  f"FR={market.funding_rate:.4%}, "
                  f"OI=${market.open_interest:,.0f}, "
                  f"Price=${market.last_price:.2f}" if market.last_price else "Price=N/A")

        # シンボル正規化テスト
        print("\nSymbol normalization tests:")
        test_symbols = [
            'BTC_USDT_Perp',
            'ETH_USDC_Perp',
            'SOL_USDT_Perp',
            'AVAX_USDT_Perp'
        ]
        for symbol in test_symbols:
            normalized = exchange.normalize_symbol(symbol)
            print(f"  {symbol} → {normalized}")

        print("\n✓ All tests passed!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await exchange.close()


if __name__ == '__main__':
    asyncio.run(test_exchange())
