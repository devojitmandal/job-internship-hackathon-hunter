# scheduler.py
# Runs the Opportunity Hunter continuously every day at EXACTLY 8:00 PM IST (20:00).
# After completing the daily run, it automatically reschedules and waits for the next 8:00 PM.
#
# Usage:
#   python src/scheduler.py            -> Waits until 8:00 PM IST and runs daily
#   python src/scheduler.py --run-now  -> Runs once immediately, then continues on daily 8:00 PM schedule

import os
import sys
import time
import logging
from datetime import datetime, timedelta, timezone

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from main import run_hunter_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scheduler")

TARGET_HOUR = 20    # 8:00 PM
TARGET_MINUTE = 0   # 00 mins
TARGET_SECOND = 0


def get_seconds_until_next_8pm() -> float:
    """Calculates exact seconds remaining until the next 8:00 PM local time."""
    now = datetime.now()
    target = now.replace(hour=TARGET_HOUR, minute=TARGET_MINUTE, second=TARGET_SECOND, microsecond=0)
    
    # If 8:00 PM has already passed today, target tomorrow's 8:00 PM
    if now >= target:
        target += timedelta(days=1)
        
    wait_seconds = (target - now).total_seconds()
    return wait_seconds, target


def run_continuous_daily_loop(run_now: bool = False):
    """Continuously executes the hunt pipeline at 8:00 PM every single day."""
    print("=" * 65)
    print(" ⏰ CONTINUOUS 8:00 PM OPPORTUNITY HUNTER SCHEDULER")
    print("=" * 65)

    if run_now:
        print("[*] Running immediate initial hunt as requested...")
        run_hunter_pipeline()
        print("[*] Initial hunt complete. Now entering daily 8:00 PM schedule.\n")

    while True:
        wait_seconds, next_target = get_seconds_until_next_8pm()
        hours = int(wait_seconds // 3600)
        minutes = int((wait_seconds % 3600) // 60)
        seconds = int(wait_seconds % 60)

        print(f"\n[STANDBY] Hunter active & listening.")
        print(f"          Next daily run scheduled for: {next_target.strftime('%A, %d %B %Y at %I:%M:%S %p')}")
        print(f"          Time remaining: {hours}h {minutes}m {seconds}s")
        print("          (Press Ctrl+C to stop scheduler)\n")

        # Sleep until 8:00 PM
        time.sleep(wait_seconds)

        print("\n" + "=" * 65)
        print(f" [ALARM] It is 8:00 PM! Launching daily opportunity hunt...")
        print("=" * 65)

        try:
            run_hunter_pipeline()
        except Exception as e:
            logger.error("Error during scheduled run: %s", e)

        print("\n[DONE] Daily hunt finished. Sleeping 60s before calculating next target...")
        time.sleep(60)


if __name__ == "__main__":
    run_now_flag = "--run-now" in sys.argv
    try:
        run_continuous_daily_loop(run_now=run_now_flag)
    except KeyboardInterrupt:
        print("\n[EXIT] Scheduler stopped by user.")
