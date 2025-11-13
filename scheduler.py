"""Scheduler for the Perp DEX Discord Bot."""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config_loader import ConfigLoader
from exchanges.factory import ExchangeFactory
from core.common_pairs import CommonPairsManager
from core.analyzer import MarketAnalyzer
from core.types import MarketData
from notifiers.discord import DiscordNotifier


logger = logging.getLogger(__name__)


class BotScheduler:
    """Scheduler for managing periodic tasks."""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the bot scheduler.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = None
        self.scheduler = None
        self.exchanges = []
        self.common_pairs_manager = None
        self.analyzer = None
        self.notifier = None
        self.shutdown_event = asyncio.Event()

    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing bot scheduler...")

        # Load configuration
        loader = ConfigLoader(self.config_path)
        self.config = loader.load()

        # Initialize components
        self.common_pairs_manager = CommonPairsManager(
            self.config['storage']['cache_file']
        )
        self.analyzer = MarketAnalyzer()
        self.notifier = DiscordNotifier(
            self.config['discord']['webhook_url']
        )

        # Create exchange instances
        enabled_exchanges = loader.get_enabled_exchanges()
        for exchange_config in enabled_exchanges:
            try:
                exchange = ExchangeFactory.create(exchange_config)
                self.exchanges.append(exchange)
                logger.info(f"Initialized exchange: {exchange.name}")
            except Exception as e:
                logger.error(f"Failed to initialize exchange {exchange_config.get('name')}: {e}")

        if not self.exchanges:
            raise RuntimeError("No exchanges initialized. Check your configuration.")

        logger.info(f"Initialized {len(self.exchanges)} exchanges")

        # Setup scheduler
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()

        logger.info("Bot scheduler initialized successfully")

    def _setup_jobs(self):
        """Setup scheduled jobs."""
        schedule_config = self.config['schedule']

        # Job 1: Common pairs update
        common_pairs_update = schedule_config.get('common_pairs_update', 'daily')

        if common_pairs_update == 'startup':
            # Run once at startup
            logger.info("Common pairs update: startup only")
            self.scheduler.add_job(
                self.update_common_pairs_job,
                'date',  # Run once
                run_date=datetime.now(),
                id='common_pairs_startup',
                name='Common Pairs Update (Startup)'
            )
        elif common_pairs_update == 'daily':
            # Run daily at midnight
            logger.info("Common pairs update: daily at 00:00")
            self.scheduler.add_job(
                self.update_common_pairs_job,
                CronTrigger(hour=0, minute=0),
                id='common_pairs_daily',
                name='Common Pairs Update (Daily)'
            )
            # Also run at startup
            self.scheduler.add_job(
                self.update_common_pairs_job,
                'date',
                run_date=datetime.now(),
                id='common_pairs_startup',
                name='Common Pairs Update (Startup)'
            )

        # Job 2: Market analysis and notification
        notification_time = schedule_config.get('notification_time', '45 * * * *')

        # Parse cron expression
        # Format: "minute hour day month day_of_week"
        cron_parts = notification_time.split()
        if len(cron_parts) == 5:
            minute, hour, day, month, day_of_week = cron_parts
            logger.info(f"Market analysis notification: {notification_time}")
            self.scheduler.add_job(
                self.market_analysis_job,
                CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week
                ),
                id='market_analysis',
                name='Market Analysis & Notification'
            )
        else:
            logger.error(f"Invalid cron expression: {notification_time}")
            raise ValueError(f"Invalid cron expression: {notification_time}")

    async def update_common_pairs_job(self):
        """Job: Update common trading pairs."""
        logger.info("Starting common pairs update job...")

        try:
            # Fetch markets from all exchanges
            exchanges_data = []

            for exchange in self.exchanges:
                try:
                    logger.info(f"Fetching markets from {exchange.name}...")
                    markets = await exchange.get_markets()

                    exchanges_data.append({
                        'name': exchange.name,
                        'markets': markets
                    })

                    logger.info(f"Fetched {len(markets)} markets from {exchange.name}")

                except Exception as e:
                    logger.error(f"Failed to fetch markets from {exchange.name}: {e}")
                    # Continue with other exchanges

            if not exchanges_data:
                logger.error("No market data fetched from any exchange")
                return

            # Find common pairs
            common_pairs = self.common_pairs_manager.find_common_pairs_from_exchanges(
                exchanges_data
            )

            if not common_pairs:
                logger.warning("No common pairs found")
                return

            # Save to cache
            metadata = {
                'exchanges': [ex['name'] for ex in exchanges_data],
                'exchange_count': len(exchanges_data),
                'total_markets': sum(len(ex['markets']) for ex in exchanges_data)
            }

            success = self.common_pairs_manager.save_to_cache(common_pairs, metadata)

            if success:
                logger.info(f"Successfully updated common pairs: {len(common_pairs)} pairs")
            else:
                logger.error("Failed to save common pairs to cache")

        except Exception as e:
            logger.error(f"Error in common pairs update job: {e}", exc_info=True)
            # Don't re-raise - let scheduler continue

    async def market_analysis_job(self):
        """Job: Analyze markets and send Discord notification."""
        logger.info("Starting market analysis job...")

        try:
            # Load common pairs
            common_pairs = self.common_pairs_manager.load_from_cache()

            if not common_pairs:
                logger.warning("No common pairs in cache. Running update job first...")
                await self.update_common_pairs_job()
                common_pairs = self.common_pairs_manager.load_from_cache()

                if not common_pairs:
                    logger.error("Still no common pairs available. Skipping analysis.")
                    return

            logger.info(f"Using {len(common_pairs)} common pairs for analysis")

            # Fetch current market data from all exchanges
            all_markets_by_exchange = {}

            for exchange in self.exchanges:
                try:
                    logger.info(f"Fetching markets from {exchange.name}...")
                    markets_raw = await exchange.get_markets()

                    # Filter to common pairs only (markets_raw already contains MarketData objects)
                    markets = [
                        market for market in markets_raw
                        if market.symbol in common_pairs
                    ]

                    all_markets_by_exchange[exchange.name] = markets
                    logger.info(f"Fetched {len(markets)} common pair markets from {exchange.name}")

                except Exception as e:
                    logger.error(f"Failed to fetch markets from {exchange.name}: {e}")
                    # Continue with other exchanges

            if len(all_markets_by_exchange) < 2:
                logger.error("Need at least 2 exchanges for analysis")
                return

            # Get analysis parameters
            analysis_config = self.config['analysis']

            # Analysis 1: FR divergence
            fr_divergence = []
            if len(self.exchanges) >= 2:
                exchange_names = list(all_markets_by_exchange.keys())
                markets_a = all_markets_by_exchange[exchange_names[0]]
                markets_b = all_markets_by_exchange[exchange_names[1]]

                fr_config = analysis_config['fr_divergence']
                fr_divergence = self.analyzer.find_top_fr_divergence(
                    markets_a,
                    markets_b,
                    min_volume=fr_config['min_volume_usd'],
                    top_n=fr_config['top_n']
                )

                logger.info(f"Found {len(fr_divergence)} FR divergence opportunities")

            # Analysis 2: Low OI ratio
            oi_config = analysis_config['oi_ratio']
            base_exchange = oi_config['base_exchange']

            if base_exchange in all_markets_by_exchange:
                base_markets = all_markets_by_exchange[base_exchange]
                low_oi_ratio = self.analyzer.find_low_oi_ratio(
                    base_markets,
                    min_volume=oi_config['min_volume_usd'],
                    max_volume=oi_config['max_volume_usd'],
                    top_n=oi_config['top_n'],
                    max_oi_ratio=oi_config.get('max_oi_ratio', 1.0)
                )

                logger.info(f"Found {len(low_oi_ratio)} low OI ratio opportunities")
            else:
                logger.warning(f"Base exchange '{base_exchange}' not found")
                low_oi_ratio = []

            # Send Discord notification
            logger.info("Sending Discord notification...")

            # Get exchange names and base exchange for notification
            exchange_names = [ex.name for ex in self.exchanges]

            success = await self.notifier.send_market_alert(
                fr_divergence,
                low_oi_ratio,
                exchange_names=exchange_names,
                base_exchange=base_exchange
            )

            if success:
                logger.info("Successfully sent Discord notification")
            else:
                logger.error("Failed to send Discord notification")

        except Exception as e:
            logger.error(f"Error in market analysis job: {e}", exc_info=True)
            # Try to send error notification
            try:
                await self.notifier.send_error(f"Market analysis job failed: {str(e)}")
            except:
                pass

    async def start(self):
        """Start the scheduler."""
        logger.info("Starting scheduler...")

        # Initialize components
        await self.initialize()

        # Start scheduler
        self.scheduler.start()
        logger.info("Scheduler started successfully")

        # Print job schedule
        self._print_job_schedule()

        # Wait for shutdown signal
        await self.shutdown_event.wait()

        logger.info("Shutdown signal received")

    async def stop(self):
        """Stop the scheduler gracefully."""
        logger.info("Stopping scheduler...")

        if self.scheduler:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")

        self.shutdown_event.set()

    def _print_job_schedule(self):
        """Print scheduled jobs information."""
        logger.info("=" * 60)
        logger.info("SCHEDULED JOBS:")
        logger.info("=" * 60)

        jobs = self.scheduler.get_jobs()
        for job in jobs:
            logger.info(f"Job: {job.name}")
            logger.info(f"  ID: {job.id}")
            logger.info(f"  Next run: {job.next_run_time}")
            logger.info("-" * 60)

        logger.info("=" * 60)


async def main():
    """Main function."""
    # Setup logging
    log_config = {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    }

    logging.basicConfig(**log_config)

    # Create scheduler
    bot = BotScheduler()

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(bot.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await bot.stop()


if __name__ == '__main__':
    asyncio.run(main())
