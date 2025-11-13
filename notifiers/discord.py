"""Discord notification for the Perp DEX Discord Bot."""

import asyncio
import logging
from typing import List, Dict
import aiohttp
from .formatter import MessageFormatter


logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Discord notification class for sending market alerts via webhook."""

    def __init__(self, webhook_url: str):
        """
        Initialize Discord notifier.

        Args:
            webhook_url: Discord webhook URL
        """
        self.webhook_url = webhook_url
        self.timeout = aiohttp.ClientTimeout(total=10)
        self.max_retries = 2  # Maximum 2 retries as per SPECIFICATION
        self.retry_delay = 1  # Initial retry delay in seconds

    async def send_market_alert(
        self,
        fr_divergence: List[Dict],
        low_oi_ratio: List[Dict],
        exchange_names: List[str] = None,
        base_exchange: str = None
    ) -> bool:
        """
        Send market alert to Discord.

        Args:
            fr_divergence: FR divergence ranking
            low_oi_ratio: Low OI ratio ranking
            exchange_names: List of enabled exchange names (for description)
            base_exchange: Base exchange name for OI analysis (optional)

        Returns:
            bool: True if sent successfully, False otherwise
        """
        # Format message
        embed = MessageFormatter.format_market_alert(
            fr_divergence,
            low_oi_ratio,
            exchange_names,
            base_exchange
        )

        # Send to Discord
        return await self._send_embed(embed)

    async def send_error(self, error_message: str) -> bool:
        """
        Send error message to Discord.

        Args:
            error_message: Error message to send

        Returns:
            bool: True if sent successfully, False otherwise
        """
        embed = MessageFormatter.format_error_message(error_message)
        return await self._send_embed(embed)

    async def _send_embed(self, embed: Dict) -> bool:
        """
        Send embed to Discord webhook with retry logic.

        Args:
            embed: Discord embed structure

        Returns:
            bool: True if sent successfully, False otherwise
        """
        payload = {
            "embeds": [embed]
        }

        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.post(
                        self.webhook_url,
                        json=payload
                    ) as response:
                        # Discord webhook returns 204 on success
                        if response.status == 204:
                            logger.info("Successfully sent message to Discord")
                            return True
                        else:
                            error_text = await response.text()
                            logger.warning(
                                f"Discord webhook returned status {response.status}: {error_text}"
                            )

                            # Don't retry on client errors (4xx)
                            if 400 <= response.status < 500:
                                logger.error(f"Client error, not retrying: {response.status}")
                                return False

            except aiohttp.ClientError as e:
                logger.warning(
                    f"Discord webhook request failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                )

            except Exception as e:
                logger.error(f"Unexpected error sending to Discord: {e}")
                return False

            # Retry logic
            if attempt < self.max_retries:
                delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Failed to send to Discord after {self.max_retries + 1} attempts")
                return False

        return False


# Test function
async def _test_discord():
    """Test function for DiscordNotifier."""
    print("Testing DiscordNotifier...")
    print("\nNOTE: This test requires a valid Discord webhook URL.")
    print("Set DISCORD_WEBHOOK_URL environment variable or edit the code.")

    import os

    # Get webhook URL from environment
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

    if not webhook_url:
        print("\n⚠️  DISCORD_WEBHOOK_URL not set. Using dummy URL for testing.")
        print("To actually send messages, set DISCORD_WEBHOOK_URL environment variable.")
        webhook_url = "https://discord.com/api/webhooks/dummy/test"

    notifier = DiscordNotifier(webhook_url)

    # Test data
    fr_divergence = [
        {
            'symbol': 'BTC-USD',
            'exchange_a': 'Extended',
            'fr_a': 0.0001,
            'exchange_b': 'Lighter',
            'fr_b': 0.0005,
            'fr_diff': 0.0004,
            'volume_24h': 5000000.0
        },
        {
            'symbol': 'ETH-USD',
            'exchange_a': 'Extended',
            'fr_a': 0.0002,
            'exchange_b': 'Lighter',
            'fr_b': 0.00021,
            'fr_diff': 0.00001,
            'volume_24h': 3000000.0
        }
    ]

    low_oi_ratio = [
        {
            'symbol': 'SOL-USD',
            'volume_24h': 25000000.0,
            'open_interest': 15000000.0,
            'oi_volume_ratio': 0.6,
            'funding_rate': 0.0002
        },
        {
            'symbol': 'AVAX-USD',
            'volume_24h': 20000000.0,
            'open_interest': 5000000.0,
            'oi_volume_ratio': 0.25,
            'funding_rate': 0.0001
        }
    ]

    # Test market alert
    print("\nTest 1: Send market alert")
    success = await notifier.send_market_alert(fr_divergence, low_oi_ratio)
    if success:
        print("  ✓ Market alert sent successfully!")
    else:
        print("  ✗ Failed to send market alert (this is expected with dummy URL)")

    # Test error message
    print("\nTest 2: Send error message")
    success = await notifier.send_error("This is a test error message")
    if success:
        print("  ✓ Error message sent successfully!")
    else:
        print("  ✗ Failed to send error message (this is expected with dummy URL)")

    # Test with empty data
    print("\nTest 3: Send with empty data")
    success = await notifier.send_market_alert([], [])
    if success:
        print("  ✓ Empty alert sent successfully!")
    else:
        print("  ✗ Failed to send empty alert (this is expected with dummy URL)")

    print("\n✓ Tests completed!")
    print("\nTo test with actual Discord:")
    print("1. Create a Discord webhook in your server")
    print("2. Set DISCORD_WEBHOOK_URL environment variable")
    print("3. Run: DISCORD_WEBHOOK_URL='your_url' python3 -m notifiers.discord")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(_test_discord())
