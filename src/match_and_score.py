# match_and_score.py
# Evaluates and scores jobs and hackathons against the candidate profile.
# Output: Returns scored opportunities with match scores (0-100%) and matching skills.

import os
import json
import logging
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROFILE_PATH = "data/users/devojit/profile.json"
OUTPUT_SCORED_PATH = "data/scored_opportunities.json"

# Strict non-tech exclusion list to avoid false positives
NON_TECH_TERMS = [
    "sales", "marketing", "telecall", "finance", "accounting", "hr intern",
    "recruiter", "operations", "business development", "content writing",
    "social media", "reel", "graphic design", "video edit"
]


def load_profile(path: str = PROFILE_PATH) -> Dict[str, Any]:
    """Loads the user's parsed profile JSON."""
    if not os.path.exists(path):
        logger.error("Profile not found at %s. Please run parse_resume.py first.", path)
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_heuristic_score(item: Dict[str, Any], profile: Dict[str, Any], is_hackathon: bool = False) -> Tuple[int, List[str]]:
    """
    High-accuracy rule-based scoring calibrated for ECE, RTL, Embedded, Hardware, and Web.
    """
    score = 0
    matching_skills = []

    title = (item.get("title") or item.get("name", "")).lower()
    desc = (item.get("description", "") + " " + item.get("tagline", "")).lower()
    combined_text = f"{title} {desc}"

    user_skills = profile.get("skills", [])
    target_roles = profile.get("target_roles", [])

    if not is_hackathon:
        # Penalize non-technical listings heavily
        if any(bad in title for bad in NON_TECH_TERMS):
            return 10, []

        # 1. Target role alignment (Jobs)
        role_matches = {
            "hardware": ["hardware", "circuit", "pcb", "electronics", "ece"],
            "rtl": ["rtl", "verilog", "fpga", "xilinx", "vivado", "vlsi", "asic", "digital logic", "digital design"],
            "embedded": ["embedded", "firmware", "microcontroller", "esp32", "arduino", "i2c", "spi", "sensors"],
            "firmware": ["firmware", "device driver", "rtos", "bare-metal"],
            "iot": ["iot", "robotics", "connected devices", "smart"],
            "frontend": ["frontend", "front-end", "react", "ui", "web developer", "full stack"]
        }

        matched_a_role = False
        for domain, keywords in role_matches.items():
            if any(k in title for k in keywords):
                score += 45
                matching_skills.append(domain.upper())
                matched_a_role = True
                break
            elif any(k in desc for k in keywords):
                score += 20
                matching_skills.append(domain.upper())
                matched_a_role = True
                break

        # 2. Key technology keyword overlap
        for skill in user_skills:
            skill_lower = skill.lower()
            if len(skill_lower) <= 2 and skill_lower not in ["c"]:
                continue
            if skill_lower == "c":
                if " c " in f" {combined_text} " or " c," in combined_text or "c/" in combined_text or "c++" in combined_text:
                    matching_skills.append("C / C++")
                    score += 15
                continue

            if skill_lower in combined_text:
                matching_skills.append(skill)
                score += 15

        # 3. Student/Intern bonus
        if any(term in title for term in ["intern", "internship", "trainee", "fresher", "apprentice"]):
            score += 25
        if any(term in title for term in ["senior", "lead", "principal", "staff"]):
            score -= 50

        # Location bonus (Bengaluru / India / Remote)
        if any(loc in combined_text or loc in item.get("location", "").lower() for loc in ["bengaluru", "bangalore", "remote"]):
            score += 10

    else:
        # Hackathon scoring
        score += 40
        platform = item.get("platform", "").lower()
        if "devfolio" in platform or "unstop" in platform:
            score += 15

        # Matching themes
        for kw in ["ai", "iot", "hardware", "robotics", "web", "hack", "code", "innovat"]:
            if kw in combined_text:
                score += 10
                matching_skills.append(kw.upper())

        # Proximity bonus (Acharya Institute / Bengaluru)
        location = (item.get("location", "") + " " + item.get("description", "")).lower()
        if any(loc in location for loc in ["acharya", "bengaluru", "bangalore"]):
            score += 30
            matching_skills.append("Acharya Campus / Bengaluru")

    # Cap score between 0 and 99
    score = max(0, min(99, score))
    clean_skills = list(dict.fromkeys(matching_skills))[:5]
    return score, clean_skills


def score_items(items: List[Dict[str, Any]], profile: Dict[str, Any], is_hackathon: bool = False) -> List[Dict[str, Any]]:
    """
    Scores a list of items (jobs or hackathons) against the candidate profile.
    """
    scored = []
    for item in items:
        h_score, h_skills = calculate_heuristic_score(item, profile, is_hackathon=is_hackathon)
        item_copy = dict(item)
        item_copy["match_score"] = h_score
        item_copy["matching_skills"] = h_skills
        scored.append(item_copy)

    # Sort descending by match score
    scored.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return scored


def match_and_score_all(min_job_threshold: int = 70, min_hackathon_threshold: int = 70) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Main evaluation pipeline. Scores all fetched jobs and hackathons.
    Returns (top_jobs, top_hackathons).
    """
    profile = load_profile()
    if not profile:
        return [], []

    # Load raw jobs
    jobs = []
    if os.path.exists("data/jobs.json"):
        with open("data/jobs.json", "r", encoding="utf-8") as f:
            jobs = json.load(f)

    # Load raw hackathons
    hackathons = []
    if os.path.exists("data/hackathons.json"):
        with open("data/hackathons.json", "r", encoding="utf-8") as f:
            hackathons = json.load(f)

    logger.info("Scoring %d jobs and %d hackathons...", len(jobs), len(hackathons))
    scored_jobs = score_items(jobs, profile, is_hackathon=False)
    scored_hackathons = score_items(hackathons, profile, is_hackathon=True)

    # Filter by minimum threshold
    top_jobs = [j for j in scored_jobs if j.get("match_score", 0) >= min_job_threshold]
    top_hackathons = [h for h in scored_hackathons if h.get("match_score", 0) >= min_hackathon_threshold]

    results_payload = {
        "candidate": profile.get("name", "Candidate"),
        "top_jobs": top_jobs,
        "top_hackathons": top_hackathons,
        "all_scored_jobs_count": len(scored_jobs),
        "all_scored_hackathons_count": len(scored_hackathons)
    }
    with open(OUTPUT_SCORED_PATH, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2, ensure_ascii=False)

    logger.info("Scoring complete. Found %d top jobs (>= %d%%) and %d top hackathons (>= %d%%)",
                len(top_jobs), min_job_threshold, len(top_hackathons), min_hackathon_threshold)
    return top_jobs, top_hackathons


if __name__ == "__main__":
    top_j, top_h = match_and_score_all(min_job_threshold=70, min_hackathon_threshold=70)
    print(f"\n--- TOP MATCHED JOBS ({len(top_j)}) ---")
    for j in top_j[:6]:
        print(f"[{j['match_score']}%] {j['title']} at {j['company']} | Skills: {j.get('matching_skills')} ({j.get('deadline')})")
        print(f"       -> {j['url']}")
    print(f"\n--- TOP MATCHED HACKATHONS ({len(top_h)}) ---")
    for h in top_h[:5]:
        print(f"[{h['match_score']}%] {h['name']} ({h['platform']}) | Location: {h.get('location')}")
        print(f"       -> {h['url']}")
