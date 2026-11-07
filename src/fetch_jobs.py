# fetch_jobs.py
# Fetches active internship and entry-level opportunities tailored to ECE, Embedded, RTL, and Frontend.
# Sources: Internshala, Unstop API, Jobicy API, Arbeitnow API, and Google Custom Search API (CX1 and CX2).
# Output: Returns a list of standardized job dictionaries, and records health stats.

import os
import sys
import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_FILE = "data/jobs.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

INTERNSHALA_CATEGORIES = [
    "embedded-systems",
    "vlsi",
    "electronics",
    "iot",
    "robotics"
]

SEARCH_TERMS = [
    "embedded",
    "electronics",
    "hardware",
    "iot",
    "robotics",
    "developer",
    "engineer",
    "react",
    "python",
    "frontend",
    "web"
]

GOOGLE_SEARCH_API_KEY = os.environ.get("GOOGLE_SEARCH_API_KEY")
GOOGLE_SEARCH_ENGINE_ID = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
GOOGLE_SEARCH_ENGINE_ID_JOBS = os.environ.get("GOOGLE_SEARCH_ENGINE_ID_JOBS")


def make_id(title: str, company: str, url: str) -> str:
    """Generates a stable unique hash ID for a job."""
    raw = f"{title.lower()}_{company.lower()}_{url.lower()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def fetch_internshala_internships(categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Scrapes active core ECE, VLSI, Embedded Systems, and IoT internships from Internshala.
    """
    cats = categories or INTERNSHALA_CATEGORIES
    jobs = []
    seen_urls = set()

    for cat in cats:
        url = f"https://internshala.com/internships/{cat}-internship/"
        try:
            res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=12)
            if res.status_code != 200:
                continue

            soup = BeautifulSoup(res.text, "html.parser")
            cards = soup.find_all("div", class_="individual_internship")

            for card in cards[:15]:
                title_elem = card.find("a", class_="job-title-href")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                relative_link = title_elem.get("href", "")
                apply_url = f"https://internshala.com{relative_link}" if relative_link.startswith("/") else relative_link

                if not apply_url or apply_url in seen_urls:
                    continue
                seen_urls.add(apply_url)

                comp_elem = card.find("p", class_="company-name") or card.find("div", class_="company_name")
                company = comp_elem.get_text(strip=True) if comp_elem else "Company Partner"

                loc_elem = card.find("a", class_="location_link") or card.find("div", class_="row-1-item")
                location = loc_elem.get_text(strip=True) if loc_elem else "India / Remote"

                jobs.append({
                    "id": f"internshala_{make_id(title, company, apply_url)}",
                    "title": title,
                    "company": company,
                    "location": location,
                    "description": f"Core ECE opportunity in {cat.replace('-', ' ').title()} listed on Internshala",
                    "skills_hint": [cat.replace("-", " ")],
                    "deadline": "Active / Apply on Internshala",
                    "url": apply_url,
                    "source": "Internshala ECE",
                    "fetched_at": datetime.now(timezone.utc).isoformat()
                })
        except Exception as e:
            logger.error("Error scraping Internshala category '%s': %s", cat, e)

    return jobs


def fetch_unstop_internships(terms: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Fetches student internships from Unstop matching technical keywords."""
    keywords = terms or SEARCH_TERMS
    jobs = []
    seen_ids = set()

    for term in keywords:
        url = f"https://unstop.com/api/public/opportunity/search-result?opportunity=internships&searchTerm={term}&per_page=15"
        try:
            res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
            if res.status_code != 200:
                continue

            data = res.json().get("data", {}).get("data", [])
            for item in data:
                opp_id = item.get("id") or item.get("regnRequirements", {}).get("opportunity_id")
                if not opp_id or opp_id in seen_ids:
                    continue

                regn = item.get("regnRequirements", {}) or {}
                remain = str(regn.get("remain_days", ""))
                reg_status = str(regn.get("reg_status", "")).lower()

                if "ended" in remain.lower() or "expired" in reg_status or "closed" in reg_status:
                    continue

                seen_ids.add(opp_id)
                org = item.get("organisation", {})
                company_name = org.get("name", "Industry Partner") if isinstance(org, dict) else "Company"
                title = item.get("title", "Internship Opportunity")
                apply_url = item.get("seo_url") or f"https://unstop.com/internships/{opp_id}"

                location_type = regn.get("work_location_type", "City / Remote")
                end_dt = regn.get("end_regn_dt", "")
                deadline_str = f"{end_dt[:10]} ({remain})" if end_dt else remain

                jobs.append({
                    "id": f"unstop_{opp_id}",
                    "title": title,
                    "company": company_name,
                    "location": f"India ({location_type.capitalize()})",
                    "description": item.get("seo_title", "") or f"Internship at {company_name}",
                    "skills_hint": [term],
                    "deadline": deadline_str,
                    "url": apply_url,
                    "source": "Unstop Internships",
                    "fetched_at": datetime.now(timezone.utc).isoformat()
                })
        except Exception as e:
            logger.error("Error fetching Unstop internships for term '%s': %s", term, e)

    return jobs


def fetch_jobicy_internships() -> List[Dict[str, Any]]:
    """Fetches relevant engineering & developer opportunities from Jobicy."""
    jobs = []
    url = "https://jobicy.com/api/v2/remote-jobs?count=25&industry=engineering"
    try:
        res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        if res.status_code != 200:
            return jobs

        data = res.json().get("jobs", [])
        for item in data:
            title = item.get("jobTitle", "")
            lower_title = title.lower()
            is_relevant = any(k in lower_title for k in ["intern", "junior", "trainee", "associate", "frontend", "embedded", "c++", "python", "developer", "engineer"])
            if not is_relevant:
                continue

            company = item.get("companyName", "Tech Company")
            link = item.get("url", "https://jobicy.com")
            jobs.append({
                "id": f"jobicy_{item.get('id', make_id(title, company, link))}",
                "title": title,
                "company": company,
                "location": item.get("jobGeo", "Remote"),
                "description": item.get("jobExcerpt", ""),
                "skills_hint": item.get("jobSkills", []),
                "deadline": "Rolling / Active",
                "url": link,
                "source": "Jobicy Remote",
                "fetched_at": datetime.now(timezone.utc).isoformat()
            })
    except Exception as e:
        logger.error("Error fetching Jobicy jobs: %s", e)

    return jobs


def fetch_arbeitnow_jobs() -> List[Dict[str, Any]]:
    """Fetches tech and engineering roles from Arbeitnow."""
    jobs = []
    url = "https://www.arbeitnow.com/api/job-board-api"
    try:
        res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        if res.status_code != 200:
            return jobs

        data = res.json().get("data", [])
        for item in data:
            title = item.get("title", "")
            lower_title = title.lower()
            tags = [t.lower() for t in item.get("tags", [])]
            
            is_intern = any(k in lower_title for k in ["intern", "junior", "working student", "trainee", "entry"])
            is_tech = any(k in lower_title or any(k in t for t in tags) for k in ["react", "python", "embedded", "hardware", "c++", "frontend", "electronics", "iot"])
            
            if not (is_intern or is_tech):
                continue

            company = item.get("company_name", "Tech Company")
            url_link = item.get("url", "")

            jobs.append({
                "id": f"arbeitnow_{make_id(title, company, url_link)}",
                "title": title,
                "company": company,
                "location": item.get("location", "Remote / Global"),
                "description": ", ".join(item.get("tags", [])),
                "skills_hint": item.get("tags", []),
                "deadline": "Rolling / Open",
                "url": url_link,
                "source": "Arbeitnow",
                "fetched_at": datetime.now(timezone.utc).isoformat()
            })
    except Exception as e:
        logger.error("Error fetching Arbeitnow jobs: %s", e)

    return jobs


def fetch_google_search_jobs(cx_id: Optional[str] = None, queries: Optional[List[str]] = None) -> Tuple[List[Dict[str, Any]], str]:
    """
    Executes search queries against Google Custom Search API.
    Returns (results, status_message).
    """
    engine_id = cx_id or GOOGLE_SEARCH_ENGINE_ID_JOBS or GOOGLE_SEARCH_ENGINE_ID
    if not GOOGLE_SEARCH_API_KEY:
        return [], "GOOGLE_SEARCH_API_KEY not configured"
    if not engine_id:
        return [], "Google Search Engine ID (CX) not configured"

    jobs = []
    default_queries = [
        '("RTL Design" OR "Embedded" OR "Firmware") ("intern" OR "trainee") Bengaluru',
        '("embedded" OR "hardware" OR "electronics") internship India',
        '("frontend" OR "react") ("intern" OR "fresher")'
    ]
    target_queries = queries or default_queries
    api_status = "OK"

    for query in target_queries:
        endpoint = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": GOOGLE_SEARCH_API_KEY,
            "cx": engine_id,
            "q": query,
            "num": 5
        }
        try:
            res = requests.get(endpoint, params=params, timeout=10)
            if res.status_code == 403:
                api_status = "Google API 403: Custom Search API must be enabled in Google Cloud Console"
                logger.warning(api_status)
                break
            elif res.status_code != 200:
                api_status = f"Google API HTTP {res.status_code}"
                logger.warning("Google search returned %s: %s", res.status_code, res.text[:150])
                continue

            items = res.json().get("items", [])
            for item in items:
                title = item.get("title", "")
                link = item.get("link", "")
                snippet = item.get("snippet", "")
                jobs.append({
                    "id": f"gsearch_{make_id(title, 'Google Search', link)}",
                    "title": title,
                    "company": "Live Portal (Google Search)",
                    "location": "Bengaluru / India / Remote",
                    "description": snippet,
                    "skills_hint": [],
                    "deadline": "Recent Posting",
                    "url": link,
                    "source": "Google Custom Search",
                    "fetched_at": datetime.now(timezone.utc).isoformat()
                })
        except Exception as e:
            api_status = f"Google Search Exception: {e}"
            logger.error(api_status)

    return jobs, api_status


def fetch_all_jobs() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Aggregates active internship and job listings from all available sources.
    Returns (unique_jobs, health_stats).
    """
    logger.info("Fetching active jobs & internships from Internshala, Unstop, Jobicy, Arbeitnow, and Google Search...")
    internshala_jobs = fetch_internshala_internships()
    unstop_jobs = fetch_unstop_internships()
    jobicy_jobs = fetch_jobicy_internships()
    arbeitnow_jobs = fetch_arbeitnow_jobs()
    
    # Query Google Search using CX_JOBS and CX_INTERNSHIPS
    google_jobs_1, g_status_1 = fetch_google_search_jobs(cx_id=GOOGLE_SEARCH_ENGINE_ID_JOBS)
    google_jobs_2, g_status_2 = fetch_google_search_jobs(cx_id=GOOGLE_SEARCH_ENGINE_ID)
    google_jobs = google_jobs_1 + google_jobs_2

    health_stats = {
        "internshala_ece_jobs": len(internshala_jobs),
        "unstop_internships": len(unstop_jobs),
        "jobicy_jobs": len(jobicy_jobs),
        "arbeitnow_jobs": len(arbeitnow_jobs),
        "google_search_jobs": len(google_jobs),
        "google_search_status": g_status_1 if g_status_1 != "OK" else g_status_2
    }

    all_raw = internshala_jobs + unstop_jobs + jobicy_jobs + arbeitnow_jobs + google_jobs
    logger.info("Fetched %d raw jobs. Health: %s", len(all_raw), health_stats)

    seen = set()
    unique_jobs = []
    for j in all_raw:
        uid = j.get("id") or j.get("url")
        if uid not in seen:
            seen.add(uid)
            unique_jobs.append(j)

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(unique_jobs, f, indent=2, ensure_ascii=False)

    logger.info("Saved %d active unique jobs to %s", len(unique_jobs), DATA_FILE)
    return unique_jobs, health_stats


if __name__ == "__main__":
    jobs, health = fetch_all_jobs()
    print(f"\nFetched {len(jobs)} ACTIVE jobs/internships. Health: {health}")
    for j in jobs[:6]:
        print(f" - [{j['source']}] {j['title']} at {j['company']} ({j.get('location')}) -> {j['url']}")
