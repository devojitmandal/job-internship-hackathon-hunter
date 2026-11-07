# fetch_hackathons.py
# Fetches active and upcoming hackathons from public platforms (Devfolio, Unstop, Devpost).
# Output: Returns a list of standardized hackathon dictionaries, and records health stats.

import os
import sys
import json
import logging
import re
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_FILE = "data/hackathons.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def make_id(name: str, platform: str, url: str) -> str:
    """Generates a stable unique hash ID for a hackathon."""
    raw = f"{name.lower()}_{platform.lower()}_{url.lower()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def fetch_devfolio_hackathons(limit: int = 15) -> List[Dict[str, Any]]:
    """Fetches open and upcoming hackathons from Devfolio's public API."""
    hackathons = []
    filters = ["application_open", "upcoming"]

    for f in filters:
        url = f"https://api.devfolio.co/api/hackathons?filter={f}&page=1&limit={limit}"
        try:
            res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=12)
            if res.status_code != 200:
                continue

            data = res.json().get("result", [])
            for item in data:
                slug = item.get("slug", "")
                h_url = f"https://{slug}.devfolio.co" if slug else item.get("website", "https://devfolio.co")
                starts_at = item.get("starts_at", "")
                ends_at = item.get("ends_at", "")
                date_str = f"{starts_at[:10]} to {ends_at[:10]}" if starts_at and ends_at else "Upcoming"

                is_online = item.get("is_online", True)
                location = "Online" if is_online else (item.get("location") or "In-Person")

                hackathons.append({
                    "id": f"devfolio_{item.get('uuid') or slug}",
                    "name": item.get("name", "Untitled Hackathon"),
                    "platform": "Devfolio",
                    "tagline": item.get("tagline", "") or item.get("theme", ""),
                    "description": item.get("desc", "") or item.get("tagline", ""),
                    "dates": date_str,
                    "location": location,
                    "is_online": is_online,
                    "prizes": "Prize pool & perks listed on site",
                    "url": h_url,
                    "source": "Devfolio API",
                    "fetched_at": datetime.now(timezone.utc).isoformat()
                })
        except Exception as e:
            logger.error("Error fetching Devfolio hackathons (%s): %s", f, e)

    return hackathons


def fetch_unstop_hackathons(limit: int = 15) -> List[Dict[str, Any]]:
    """Fetches student hackathons from Unstop's public opportunity search."""
    hackathons = []
    url = f"https://unstop.com/api/public/opportunity/search-result?opportunity=hackathons&per_page={limit}"

    try:
        res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=12)
        if res.status_code != 200:
            return hackathons

        data = res.json().get("data", {}).get("data", [])
        for item in data:
            opp_id = item.get("id") or item.get("regnRequirements", {}).get("opportunity_id")
            org = item.get("organisation", {})
            org_name = org.get("name", "Unstop Organizer") if isinstance(org, dict) else "Unstop"
            
            regn = item.get("regnRequirements", {}) or {}
            remain = regn.get("remain_days") or "Open"
            end_dt = regn.get("end_regn_dt", "")
            date_str = f"Deadline: {end_dt[:10]} ({remain})" if end_dt else remain

            prizes = item.get("prizes", "Certificates, Cash Prizes & Mentorship")
            if isinstance(prizes, list):
                prizes = ", ".join([str(p.get("name", "")) for p in prizes if isinstance(p, dict)]) or "Prizes Available"

            hackathons.append({
                "id": f"unstop_{opp_id}",
                "name": item.get("title", "Hackathon"),
                "platform": "Unstop",
                "tagline": f"Organized by {org_name}",
                "description": item.get("seo_title", "") or f"Hackathon hosted by {org_name}",
                "dates": date_str,
                "location": "Online / Campus",
                "is_online": True,
                "prizes": str(prizes),
                "url": item.get("seo_url") or f"https://unstop.com/o/{opp_id}",
                "source": "Unstop API",
                "fetched_at": datetime.now(timezone.utc).isoformat()
            })
    except Exception as e:
        logger.error("Error fetching Unstop hackathons: %s", e)

    return hackathons


def fetch_devpost_hackathons() -> List[Dict[str, Any]]:
    """Fetches global hackathons from Devpost's public API."""
    hackathons = []
    url = "https://devpost.com/api/hackathons?status[]=upcoming&status[]=open"
    try:
        res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=12)
        if res.status_code != 200:
            return hackathons

        data = res.json().get("hackathons", [])
        for item in data:
            h_id = item.get("id") or item.get("title", "")
            raw_prize = item.get("prize_amount", "")
            clean_prize = re.sub(r"<[^>]+>", "", raw_prize).strip() or "Prizes & Recognition"

            themes = [t.get("name") for t in item.get("themes", []) if isinstance(t, dict)]
            theme_str = ", ".join(themes) if themes else "General Tech & AI"

            hackathons.append({
                "id": f"devpost_{h_id}",
                "name": item.get("title", "Devpost Hackathon"),
                "platform": "Devpost",
                "tagline": theme_str,
                "description": f"Themes: {theme_str}",
                "dates": item.get("submission_period_dates", "Active"),
                "location": "Online / Global",
                "is_online": True,
                "prizes": clean_prize,
                "url": item.get("url", "https://devpost.com"),
                "source": "Devpost API",
                "fetched_at": datetime.now(timezone.utc).isoformat()
            })
    except Exception as e:
        logger.error("Error fetching Devpost hackathons: %s", e)

    return hackathons


def fetch_all_hackathons() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Combines hackathon feeds from Devfolio, Unstop, and Devpost.
    Returns (unique_hackathons, health_stats).
    """
    logger.info("Fetching hackathons from Devfolio, Unstop, and Devpost...")
    devfolio_list = fetch_devfolio_hackathons(limit=15)
    unstop_list = fetch_unstop_hackathons(limit=15)
    devpost_list = fetch_devpost_hackathons()

    health_stats = {
        "devfolio_hackathons": len(devfolio_list),
        "unstop_hackathons": len(unstop_list),
        "devpost_hackathons": len(devpost_list)
    }

    all_raw = devfolio_list + unstop_list + devpost_list
    logger.info("Fetched %d raw hackathons across 3 platforms. Health: %s", len(all_raw), health_stats)

    seen = set()
    unique_hackathons = []
    for h in all_raw:
        key = h.get("id") or h.get("name", "").lower().strip()
        if key not in seen:
            seen.add(key)
            unique_hackathons.append(h)

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(unique_hackathons, f, indent=2, ensure_ascii=False)

    logger.info("Saved %d unique hackathons to %s", len(unique_hackathons), DATA_FILE)
    return unique_hackathons, health_stats


if __name__ == "__main__":
    hackathons, health = fetch_all_hackathons()
    print(f"\nFetched {len(hackathons)} hackathons across 3 platforms. Health: {health}")
    for h in hackathons[:4]:
        print(f" - [{h['platform']}] {h['name']} -> {h['url']}")
