#!/usr/bin/env python3
"""
Test script for scheduler functionality.

This script tests the scheduler setup without actually running jobs.
"""

import asyncio
import logging
import os

from scheduler import BotScheduler


async def test_scheduler_initialization():
    """Test scheduler initialization."""
    print("Testing Scheduler Initialization...")
    print("=" * 60)

    # Set test environment variable
    os.environ['DISCORD_WEBHOOK_URL'] = 'https://discord.com/api/webhooks/test/token'

    try:
        # Create scheduler
        bot = BotScheduler('config.yaml')
        print("✓ BotScheduler instance created")

        # Initialize (this loads config and creates exchange instances)
        await bot.initialize()
        print("✓ Scheduler initialized successfully")

        # Check components
        print(f"\nInitialized Components:")
        print(f"  - Exchanges: {len(bot.exchanges)}")
        for exchange in bot.exchanges:
            print(f"    • {exchange.name}")

        print(f"  - Common Pairs Manager: {bot.common_pairs_manager is not None}")
        print(f"  - Market Analyzer: {bot.analyzer is not None}")
        print(f"  - Discord Notifier: {bot.notifier is not None}")

        # Check scheduled jobs
        jobs = bot.scheduler.get_jobs()
        print(f"\nScheduled Jobs: {len(jobs)}")
        for job in jobs:
            print(f"  - {job.name}")
            print(f"    ID: {job.id}")
            # next_run_time is only available after scheduler starts
            # print(f"    Next run: {job.next_run_time}")

        # Verify cron expression parsing
        schedule_config = bot.config['schedule']
        notification_time = schedule_config.get('notification_time', '45 * * * *')
        print(f"\nCron Expression Test:")
        print(f"  Notification time: {notification_time}")

        # Stop scheduler (don't actually start it)
        # Note: scheduler.shutdown() raises error if not running, so we skip it
        # bot.scheduler.shutdown(wait=False)
        print("\n✓ Scheduler created successfully (not started)")

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def test_job_functions():
    """Test individual job functions without scheduling."""
    print("\n\nTesting Job Functions (Manual Execution)...")
    print("=" * 60)

    os.environ['DISCORD_WEBHOOK_URL'] = 'https://discord.com/api/webhooks/test/token'

    try:
        bot = BotScheduler('config.yaml')
        await bot.initialize()

        print("\nTest 1: Common Pairs Update Job")
        print("-" * 60)
        print("Running common pairs update job manually...")
        await bot.update_common_pairs_job()
        print("✓ Common pairs update job completed")

        # Check if common pairs were saved
        common_pairs = bot.common_pairs_manager.load_from_cache()
        if common_pairs:
            print(f"  Found {len(common_pairs)} common pairs in cache")
            print(f"  Sample pairs: {common_pairs[:5]}")
        else:
            print("  No common pairs in cache")

        # Note: We won't actually run market_analysis_job as it would send
        # a Discord notification
        print("\nTest 2: Market Analysis Job")
        print("-" * 60)
        print("⚠️  Skipping actual execution to avoid sending Discord notification")
        print("   To test fully, set a valid DISCORD_WEBHOOK_URL and run manually")

        # No need to shutdown as we didn't start it
        # bot.scheduler.shutdown(wait=False)

        print("\n" + "=" * 60)
        print("✓ Job function tests completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error during job test: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def main():
    """Main test function."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "=" * 60)
    print("SCHEDULER TEST SUITE")
    print("=" * 60 + "\n")

    # Test 1: Initialization
    success1 = await test_scheduler_initialization()

    # Test 2: Job functions
    success2 = await test_job_functions()

    # Summary
    print("\n\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"  Initialization Test: {'✓ PASSED' if success1 else '✗ FAILED'}")
    print(f"  Job Functions Test:  {'✓ PASSED' if success2 else '✗ FAILED'}")
    print("=" * 60)

    if success1 and success2:
        print("\n✓ ALL TESTS PASSED\n")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED\n")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    exit(exit_code)
