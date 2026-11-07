# main.py
# Master orchestrator for Job, Internship, and Hackathon Hunter.
# Usage:
#   python src/main.py            -> Standard hunt (fetch, score, verify health, and alert)
#   python src/main.py --dry-run  -> Fetch & score without sending Telegram messages
#   python src/main.py --force    -> Force alert all top matches, ignoring history

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Set

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fetch_hackathons import fetch_all_hackathons
from fetch_jobs import fetch_all_jobs
from match_and_score import match_and_score_all, load_profile
import telegram_notify

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hunter")

HISTORY_FILE = "data/history.json"


def load_history() -> Dict[str, Any]:
    """Loads history of previously alerted opportunity IDs to avoid duplicate notifications."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Could not read %s, starting fresh: %s", HISTORY_FILE, e)
    return {"notified_ids": [], "last_run": None}


def save_history(history: Dict[str, Any]) -> None:
    """Saves updated history to disk."""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def run_hunter_pipeline(dry_run: bool = False, force: bool = False) -> bool:
    """
    Executes the end-to-end hunting pipeline.
    Returns True if execution was successful.
    """
    print("=" * 65)
    print(" 🚀 AUTOMATED JOB, INTERNSHIP & HACKATHON HUNTER")
    print("=" * 65)

    # 1. Verify Profile
    profile = load_profile()
    if not profile:
        print("[ERROR] Profile not found. Please run 'python src/parse_resume.py' first.")
        if not dry_run:
            telegram_notify.send_health_failure_alert("Profile data not found at data/users/devojit/profile.json")
        return False

    candidate_name = profile.get("name", "Devojit")
    print(f"[*] Candidate: {candidate_name} ({profile.get('education', {}).get('branch', 'ECE')})")

    # 2. Fetch Data with Health Verification
    print("\n[1/4] Fetching latest hackathons from Devfolio, Unstop, Devpost & Google Search...")
    hackathons, hackathon_health = fetch_all_hackathons()

    print("\n[2/4] Fetching active internships & jobs from Unstop, Jobicy, Arbeitnow & Google Search...")
    jobs, job_health = fetch_all_jobs()

    total_scanned = len(jobs) + len(hackathons)
    print(f"\n[*] Health Check: Total {total_scanned} opportunities retrieved across all sources.")

    # Verification: Did the scrapers fail completely?
    if total_scanned == 0:
        error_msg = "All opportunity platforms returned 0 results. Network down or scrapers blocked."
        logger.error(error_msg)
        print(f"[CRITICAL] {error_msg}")
        if not dry_run:
            telegram_notify.send_health_failure_alert(error_msg)
        return False

    # 3. Match & Score
    print("\n[3/4] Matching and scoring against candidate profile...")
    top_jobs, top_hackathons = match_and_score_all(min_job_threshold=70, min_hackathon_threshold=75)

    print(f"\n[+] Analysis complete:")
    print(f"    - High-Match Internships (>=70%): {len(top_jobs)}")
    print(f"    - High-Match Hackathons  (>=75%): {len(top_hackathons)}")

    # 4. Filter previously alerted items (Deduplication)
    history = load_history()
    seen_ids: Set[str] = set(history.get("notified_ids", []))

    if force:
        new_jobs = top_jobs
        new_hackathons = top_hackathons
        print("\n[*] Force mode enabled: Alerting all top matches.")
    else:
        new_jobs = [j for j in top_jobs if j.get("id") not in seen_ids]
        new_hackathons = [h for h in top_hackathons if h.get("id") not in seen_ids]
        print(f"\n[*] Newly discovered opportunities:")
        print(f"    - New Internships to alert: {len(new_jobs)}")
        print(f"    - New Hackathons to alert:  {len(new_hackathons)}")

    # 5. Send Telegram Notifications
    if dry_run:
        print("\n[DRY RUN] Notifications skipped.")
        return True

    alerts_sent = 0

    if not new_jobs and not new_hackathons:
        print("\n[OK] No new opportunities found today. Sending verified status update...")
        telegram_notify.send_nothing_found_message(job_health, hackathon_health, total_scanned)
    else:
        print("\n[4/4] Sending Telegram alerts with resume tweaks & hackathon plans...")
        # Send new jobs (up to 4 highest matches)
        for job in new_jobs[:4]:
            card = telegram_notify.format_job_alert(job, profile=profile)
            if telegram_notify.send_message(card):
                alerts_sent += 1

        # Send new hackathons (up to 3 highest matches)
        for hackathon in new_hackathons[:3]:
            card = telegram_notify.format_hackathon_alert(hackathon, profile=profile)
            if telegram_notify.send_message(card):
                alerts_sent += 1

    # 6. Update History
    for item in new_jobs + new_hackathons:
        item_id = item.get("id")
        if item_id:
            seen_ids.add(item_id)

    history["notified_ids"] = list(seen_ids)
    history["last_run"] = datetime.now(timezone.utc).isoformat()
    history["health_last_run"] = {
        "total_scanned": total_scanned,
        "job_health": job_health,
        "hackathon_health": hackathon_health
    }
    save_history(history)

    print(f"\n[SUCCESS] Pipeline finished. Dispatched notifications to Telegram!")
    print("=" * 65)
    return True


def main():
    parser = argparse.ArgumentParser(description="Automated Job, Internship & Hackathon Hunter")
    parser.add_argument("--dry-run", action="store_true", help="Run without sending Telegram messages")
    parser.add_argument("--force", action="store_true", help="Send alerts even if previously notified")
    args = parser.parse_args()

    run_hunter_pipeline(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
