#!/usr/bin/env python3
"""
Automated daily workflow for NBA prediction model.

Process:
1. Sync new games from API
2. Calculate metrics for new games
3. Generate predictions for upcoming games
4. Evaluate accuracy on completed predictions
5. Generate daily report

Usage:
    python daily_workflow.py
    python daily_workflow.py --skip-api  # Skip API sync (testing)
"""

import sys
import os
import subprocess
from datetime import datetime, timedelta
import argparse

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from loguru import logger


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"daily_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG",
    )
    return log_file


def run_script(script_name, skip_this=False):
    """
    Run a Python script and return success/failure status.

    Args:
        script_name: Name of the script in scripts/ directory
        skip_this: If True, skip this step

    Returns:
        (success: bool, output: str, error: str)
    """
    if skip_this:
        logger.info(f"⊘ Skipped: {script_name}")
        return True, "Skipped", ""

    script_path = os.path.join(os.path.dirname(__file__), script_name)
    logger.info(f"Starting: {script_name}")

    try:
        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )

        if result.returncode == 0:
            logger.info(f"✓ Completed: {script_name}")
            return True, result.stdout, result.stderr
        else:
            logger.error(f"✗ Failed: {script_name}")
            logger.error(f"STDOUT:\n{result.stdout}")
            logger.error(f"STDERR:\n{result.stderr}")
            return False, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        error_msg = f"Script timeout (10 minutes): {script_name}"
        logger.error(f"✗ {error_msg}")
        return False, "", error_msg
    except Exception as e:
        error_msg = f"Error running {script_name}: {str(e)}"
        logger.error(f"✗ {error_msg}")
        return False, "", error_msg


def main():
    """Main workflow orchestrator."""
    parser = argparse.ArgumentParser(description="Daily NBA prediction workflow")
    parser.add_argument("--skip-api", action="store_true", help="Skip API sync step")
    parser.add_argument("--skip-metrics", action="store_true", help="Skip metrics calculation")
    parser.add_argument("--skip-predictions", action="store_true", help="Skip prediction generation")
    parser.add_argument("--skip-accuracy", action="store_true", help="Skip accuracy analysis")
    args = parser.parse_args()

    log_file = setup_logging()

    logger.info("=" * 100)
    logger.info(f"DAILY WORKFLOW STARTED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 100)

    # Track results
    results = {
        'sync_games': None,
        'calculate_metrics': None,
        'generate_predictions': None,
        'analyze_accuracy': None,
    }

    start_time = datetime.now()

    # Step 1: Sync games from API
    logger.info("\n" + "=" * 100)
    logger.info("STEP 1: SYNC GAMES FROM API")
    logger.info("=" * 100)
    success, stdout, stderr = run_script("reload_clean_from_api.py", skip_this=args.skip_api)
    results['sync_games'] = success
    if not success and not args.skip_api:
        logger.error("API sync failed - continuing with cached data")

    # Step 2: Calculate metrics for all games
    logger.info("\n" + "=" * 100)
    logger.info("STEP 2: CALCULATE TEAM METRICS")
    logger.info("=" * 100)
    success, stdout, stderr = run_script("calculate_metrics.py", skip_this=args.skip_metrics)
    results['calculate_metrics'] = success
    if not success and not args.skip_metrics:
        logger.error("Metrics calculation failed - predictions may be based on stale metrics")

    # Step 3: Generate predictions
    logger.info("\n" + "=" * 100)
    logger.info("STEP 3: GENERATE PREDICTIONS")
    logger.info("=" * 100)
    success, stdout, stderr = run_script("generate_game_predictions.py", skip_this=args.skip_predictions)
    results['generate_predictions'] = success
    if not success and not args.skip_predictions:
        logger.error("Prediction generation failed")

    # Step 4: Analyze accuracy on completed games
    logger.info("\n" + "=" * 100)
    logger.info("STEP 4: ANALYZE PREDICTION ACCURACY")
    logger.info("=" * 100)
    success, stdout, stderr = run_script("analyze_prediction_accuracy.py", skip_this=args.skip_accuracy)
    results['analyze_accuracy'] = success
    if not success and not args.skip_accuracy:
        logger.warning("Accuracy analysis failed - report may be incomplete")

    # Final summary
    end_time = datetime.now()
    duration = end_time - start_time

    logger.info("\n" + "=" * 100)
    logger.info("WORKFLOW SUMMARY")
    logger.info("=" * 100)

    status_symbols = {
        True: "✓",
        False: "✗",
        None: "⊘",
    }

    for step, success in results.items():
        status = status_symbols.get(success, "?")
        status_text = "PASSED" if success is True else "FAILED" if success is False else "SKIPPED"
        logger.info(f"{status} {step.replace('_', ' ').upper():<40} {status_text}")

    logger.info(f"\nTotal Duration: {duration.total_seconds():.1f} seconds")
    logger.info(f"Log file: {log_file}")

    # Determine overall success
    critical_steps = ['calculate_metrics', 'generate_predictions']
    critical_failures = [step for step in critical_steps if results[step] is False]

    if critical_failures:
        logger.error("\n" + "=" * 100)
        logger.error(f"WORKFLOW FAILED - Critical steps failed: {', '.join(critical_failures)}")
        logger.error("=" * 100)
        sys.exit(1)
    else:
        logger.info("\n" + "=" * 100)
        logger.info("WORKFLOW COMPLETED SUCCESSFULLY")
        logger.info("=" * 100)
        sys.exit(0)


if __name__ == "__main__":
    main()
