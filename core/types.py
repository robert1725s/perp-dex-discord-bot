"""Data type definitions for the Perp DEX Discord Bot."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class MarketData:
    """Market data representation."""
    symbol: str               # Normalized symbol (e.g., 'BTC-USD')
    exchange: str             # Exchange name
    volume_24h: float         # 24-hour trading volume (USD)
    funding_rate: float       # Funding rate
    open_interest: float      # Open interest (USD)
    last_price: Optional[float] = None  # Last price


@dataclass
class FRDivergence:
    """Funding rate divergence analysis result."""
    symbol: str
    exchange_a: str
    fr_a: float
    exchange_b: str
    fr_b: float
    fr_diff: float
    volume_24h: float


@dataclass
class LowOIRatio:
    """Low OI ratio analysis result."""
    symbol: str
    volume_24h: float
    open_interest: float
    oi_volume_ratio: float
    funding_rate: float
