#!/usr/bin/env python3
"""
Test script for sending Discord notifications.

Usage:
    DISCORD_WEBHOOK_URL='your_webhook_url' python3 test_discord_webhook.py
"""

import asyncio
import os
import sys
from notifiers import DiscordNotifier


async def main():
    """Main test function."""
    # Get webhook URL from environment
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

    if not webhook_url:
        print("❌ Error: DISCORD_WEBHOOK_URL environment variable not set")
        print("\nUsage:")
        print("  DISCORD_WEBHOOK_URL='your_url' python3 test_discord_webhook.py")
        print("\nTo get a webhook URL:")
        print("  1. Go to your Discord server settings")
        print("  2. Navigate to Integrations > Webhooks")
        print("  3. Click 'New Webhook'")
        print("  4. Copy the webhook URL")
        sys.exit(1)

    print("Testing Discord webhook...")
    print(f"Webhook URL: {webhook_url[:50]}...")

    # Create notifier
    notifier = DiscordNotifier(webhook_url)

    # Sample FR divergence data
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
        },
        {
            'symbol': 'SOL-USD',
            'exchange_a': 'Extended',
            'fr_a': -0.0001,
            'exchange_b': 'Lighter',
            'fr_b': 0.0003,
            'fr_diff': 0.0004,
            'volume_24h': 2000000.0
        }
    ]

    # Sample low OI ratio data
    low_oi_ratio = [
        {
            'symbol': 'AVAX-USD',
            'volume_24h': 25000000.0,
            'open_interest': 6000000.0,
            'oi_volume_ratio': 0.24,
            'funding_rate': 0.0001
        },
        {
            'symbol': 'LINK-USD',
            'volume_24h': 20000000.0,
            'open_interest': 8000000.0,
            'oi_volume_ratio': 0.40,
            'funding_rate': 0.0002
        },
        {
            'symbol': 'UNI-USD',
            'volume_24h': 15000000.0,
            'open_interest': 9000000.0,
            'oi_volume_ratio': 0.60,
            'funding_rate': 0.00015
        }
    ]

    # Send market alert
    print("\nSending market alert...")
    success = await notifier.send_market_alert(fr_divergence, low_oi_ratio)

    if success:
        print("✅ Successfully sent market alert to Discord!")
        print("   Check your Discord channel to see the message.")
    else:
        print("❌ Failed to send market alert")
        print("   Check the logs above for error details")
        sys.exit(1)

    # Wait a bit
    await asyncio.sleep(2)

    # Send error message test
    print("\nSending test error message...")
    success = await notifier.send_error("This is a test error message from the bot")

    if success:
        print("✅ Successfully sent error message to Discord!")
    else:
        print("❌ Failed to send error message")

    print("\n✅ All tests completed successfully!")


if __name__ == '__main__':
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(main())
