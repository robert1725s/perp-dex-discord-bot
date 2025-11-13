#!/usr/bin/env python3
"""
Perp DEX Discord Bot - Main Entry Point

This bot monitors multiple Perpetual DEX exchanges and sends market alerts to Discord.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from scheduler import BotScheduler


def setup_logging(config: dict):
    """
    Setup logging configuration.

    Args:
        config: Configuration dictionary with logging settings
    """
    log_config = config.get('logging', {})
    log_level = log_config.get('level', 'INFO').upper()
    log_file = log_config.get('file', 'logs/bot.log')

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Configure logging
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized: level={log_level}, file={log_file}")


async def run_once(config_path: str):
    """
    Run market analysis once without scheduling (test mode).

    Args:
        config_path: Path to configuration file
    """
    logger = logging.getLogger(__name__)
    logger.info("Running in --once mode (single execution)")

    try:
        # Create scheduler instance
        bot = BotScheduler(config_path)

        # Initialize without starting scheduler
        await bot.initialize()

        logger.info("=" * 60)
        logger.info("RUNNING JOBS ONCE (TEST MODE)")
        logger.info("=" * 60)

        # Run common pairs update job
        logger.info("\n1. Updating common pairs...")
        await bot.update_common_pairs_job()

        # Run market analysis job
        logger.info("\n2. Running market analysis and notification...")
        await bot.market_analysis_job()

        logger.info("=" * 60)
        logger.info("✓ Single execution completed successfully")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error in --once mode: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Clean up HTTP sessions
        if 'bot' in locals() and bot.exchanges:
            logger.info("Cleaning up exchange connections...")
            for exchange in bot.exchanges:
                if hasattr(exchange, 'close'):
                    try:
                        await exchange.close()
                    except Exception as e:
                        logger.warning(f"Error closing {exchange.name}: {e}")


async def run_scheduled(config_path: str):
    """
    Run scheduler in continuous mode.

    Args:
        config_path: Path to configuration file
    """
    logger = logging.getLogger(__name__)
    logger.info("Running in scheduled mode")

    try:
        # Create and start scheduler
        bot = BotScheduler(config_path)
        await bot.start()

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Perp DEX Discord Bot - Monitor multiple exchanges and send alerts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in scheduled mode (default)
  python main.py

  # Run once for testing
  python main.py --once

  # Use custom config file
  python main.py --config my_config.yaml

  # Run once with custom config
  python main.py --once --config my_config.yaml

Environment Variables:
  DISCORD_WEBHOOK_URL    Discord webhook URL (required)
  CONFIG_FILE            Path to config file (optional)
        """
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )

    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (test mode, no scheduling)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='Perp DEX Discord Bot v1.0.0'
    )

    return parser.parse_args()


def validate_config_file(config_path: str):
    """
    Validate that config file exists.

    Args:
        config_path: Path to configuration file

    Raises:
        SystemExit: If config file doesn't exist
    """
    if not Path(config_path).exists():
        print(f"❌ Error: Configuration file not found: {config_path}")
        print("\nPlease create a configuration file:")
        print("  1. Copy config.yaml.example to config.yaml")
        print("  2. Edit config.yaml with your settings")
        print("  3. Set DISCORD_WEBHOOK_URL in .env file")
        sys.exit(1)


async def main():
    """Main function."""
    # Parse arguments
    args = parse_arguments()

    # Validate config file
    validate_config_file(args.config)

    # Setup basic logging first (will be reconfigured after loading config)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)

    # Print banner
    print("=" * 60)
    print("  Perp DEX Discord Bot")
    print("  v1.0.0")
    print("=" * 60)
    print(f"Configuration: {args.config}")
    print(f"Mode: {'Test (--once)' if args.once else 'Scheduled'}")
    print("=" * 60)

    try:
        # Load config to setup proper logging
        from config_loader import ConfigLoader
        loader = ConfigLoader(args.config)
        config = loader.load()

        # Reconfigure logging with settings from config
        setup_logging(config)

        logger.info(f"Starting Perp DEX Discord Bot")
        logger.info(f"Config file: {args.config}")
        logger.info(f"Mode: {'once' if args.once else 'scheduled'}")

        # Run in appropriate mode
        if args.once:
            await run_once(args.config)
        else:
            await run_scheduled(args.config)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
