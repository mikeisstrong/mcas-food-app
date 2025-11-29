#!/usr/bin/env python3
"""
Schedule automated daily tasks for prediction updates.

Tasks:
- 3:00 AM EST: Sync games from API
- 3:30 AM EST: Calculate metrics
- 4:00 AM EST: Generate predictions
- 4:30 AM EST: Generate daily report

Setup:
    1. Install schedule: pip install schedule
    2. Run: python schedule_daily_tasks.py
    3. Keep running in background (use nohup or screen)

Usage:
    python schedule_daily_tasks.py
    nohup python schedule_daily_tasks.py > scheduler.log 2>&1 &
    screen -S nba_scheduler -d -m python schedule_daily_tasks.py
"""

import sys
import os
import subprocess
import time
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

try:
    import schedule
except ImportError:
    print("schedule module not found. Install with: pip install schedule")
    sys.exit(1)

from loguru import logger


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<level>{level: <8}</level> | {time:YYYY-MM-DD HH:mm:ss} | <level>{message}</level>",
        level="INFO",
    )
    os.makedirs("logs", exist_ok=True)
    logger.add(
        "logs/scheduler.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG",
        rotation="00:00",  # Rotate daily at midnight
    )


def run_job(script_name, job_name):
    """
    Run a script as a scheduled job.

    Args:
        script_name: Name of script in scripts/ directory
        job_name: Friendly name for logging
    """
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    logger.info(f"Starting scheduled task: {job_name}")

    try:
        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minute timeout
        )

        if result.returncode == 0:
            logger.info(f"✓ Completed: {job_name}")
            # Log last line of output
            lines = result.stdout.strip().split('\n')
            if lines:
                logger.debug(f"  Output: {lines[-1]}")
        else:
            logger.error(f"✗ Failed: {job_name}")
            logger.error(f"  STDERR: {result.stderr[:200]}")

    except subprocess.TimeoutExpired:
        logger.error(f"✗ Timeout: {job_name} (exceeded 30 minutes)")
    except Exception as e:
        logger.error(f"✗ Error running {job_name}: {str(e)}")


def schedule_tasks():
    """Schedule all daily tasks."""

    # 3:00 AM EST: Sync games from API
    schedule.every().day.at("03:00").do(
        run_job,
        "reload_clean_from_api.py",
        "API Sync"
    )

    # 3:30 AM EST: Calculate metrics
    schedule.every().day.at("03:30").do(
        run_job,
        "calculate_metrics.py",
        "Metrics Calculation"
    )

    # 4:00 AM EST: Generate predictions
    schedule.every().day.at("04:00").do(
        run_job,
        "generate_game_predictions.py",
        "Prediction Generation"
    )

    # 4:30 AM EST: Generate daily report
    schedule.every().day.at("04:30").do(
        run_job,
        "generate_daily_report.py",
        "Daily Report"
    )

    logger.info("=" * 80)
    logger.info("NBA PREDICTION SCHEDULER STARTED")
    logger.info("=" * 80)
    logger.info("Scheduled tasks:")
    logger.info("  03:00 - API Sync")
    logger.info("  03:30 - Metrics Calculation")
    logger.info("  04:00 - Prediction Generation")
    logger.info("  04:30 - Daily Report")
    logger.info("=" * 80)


def main():
    """Main scheduler loop."""
    setup_logging()
    schedule_tasks()

    logger.info(f"Scheduler ready. Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Main loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute if a task is due

    except KeyboardInterrupt:
        logger.info("Scheduler shutting down (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Scheduler error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
