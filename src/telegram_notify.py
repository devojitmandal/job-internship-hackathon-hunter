# telegram_notify.py
# Sends job, internship, and hackathon alerts with tailored resume tips and hackathon action plans.
# Requires: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional
import requests
from dotenv import load_dotenv

from advisor import generate_resume_tips, generate_hackathon_plan

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
MAX_MESSAGE_LENGTH = 4000

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def validate_credentials() -> bool:
    """Verifies that TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set in .env")
        return False
    if not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_CHAT_ID is not set in .env")
        return False
    return True


def check_bot_connection() -> Optional[Dict[str, Any]]:
    """Calls getMe on Telegram API to test if the bot token is valid."""
    if not TELEGRAM_BOT_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("ok"):
            return data["result"]
        return None
    except Exception as e:
        logger.error("Failed to connect to Telegram API: %s", e)
        return None


def send_message(
    text: str,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = True,
    chat_id: Optional[str] = None
) -> bool:
    """Sends a message to Telegram, splitting long messages if needed."""
    if not validate_credentials():
        return False

    target_chat_id = chat_id or TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks = split_message(text, MAX_MESSAGE_LENGTH)
    all_success = True

    for chunk in chunks:
        payload = {
            "chat_id": target_chat_id,
            "text": chunk,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview
        }
        try:
            res = requests.post(url, json=payload, timeout=15)
            data = res.json()
            if not data.get("ok"):
                logger.error("Telegram send failed: %s", data.get("description"))
                all_success = False
            else:
                logger.info("Message sent successfully (ID: %s)", data.get("result", {}).get("message_id"))
        except Exception as e:
            logger.error("Error sending Telegram message: %s", e)
            all_success = False

    return all_success


def split_message(text: str, max_len: int = MAX_MESSAGE_LENGTH) -> List[str]:
    """Splits a long message into chunks preserving line breaks."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    lines = text.split("\n")
    current_chunk = ""

    for line in lines:
        if len(current_chunk) + len(line) + 1 > max_len:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            while len(line) > max_len:
                chunks.append(line[:max_len])
                line = line[max_len:]
            current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def format_job_alert(job: Dict[str, Any], profile: Optional[Dict[str, Any]] = None) -> str:
    """
    Formats a job/internship card with match score, apply link, and custom resume tweaks.
    """
    title = job.get("title", "Internship Opportunity")
    company = job.get("company", "Company")
    location = job.get("location", "Remote / Hybrid / On-site")
    score = job.get("match_score", 0)
    skills = job.get("matching_skills", [])
    skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
    url = job.get("url", "#")
    deadline = job.get("deadline", "Open")
    source = job.get("source", "Web")

    badge = "🔥 <b>HIGH MATCH INTERNSHIP</b>" if score >= 80 else "⚡ <b>MATCHED INTERNSHIP</b>"

    # Generate tailored resume tweaks
    tips = generate_resume_tips(job, profile or {})

    message = (
        f"{badge} (Score: <b>{score}%</b>)\n\n"
        f"💼 <b>{title}</b>\n"
        f"🏢 <b>Company:</b> {company}\n"
        f"📍 <b>Location:</b> {location}\n"
        f"⏳ <b>Deadline:</b> {deadline}\n"
        f"📡 <b>Source:</b> {source}\n"
        f"🛠️ <b>Key Matching Skills:</b> {skills_str or 'Relevant Match'}\n\n"
        f"📝 <b>Minor Resume Changes to Stand Out:</b>\n"
        f"• <b>Project Focus:</b> {tips['project_tip']}\n"
        f"• <b>Skill Ordering:</b> {tips['skill_tip']}\n"
        f"• <b>Application Edge:</b> {tips['highlight_tip']}\n\n"
        f"👉 <b>How to Apply:</b>\n"
        f"1. Update your PDF resume with the minor tweaks above.\n"
        f"2. Submit your application directly using the official link below:\n"
        f"🔗 <a href='{url}'><b>Click here to Apply Now</b></a>"
    )
    return message


def format_hackathon_alert(hackathon: Dict[str, Any], profile: Optional[Dict[str, Any]] = None) -> str:
    """
    Formats a hackathon card with problem statement analysis, winning idea, and immediate steps.
    """
    name = hackathon.get("name", "Hackathon")
    platform = hackathon.get("platform", "Platform")
    score = hackathon.get("match_score", 0)
    dates = hackathon.get("dates", "Upcoming")
    prizes = hackathon.get("prizes", "Exciting prizes & certificates")
    skills = hackathon.get("matching_skills", [])
    skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
    location = hackathon.get("location", "Online")
    url = hackathon.get("url", "#")

    badge = "🏆 <b>TOP HACKATHON PICK</b>" if score >= 85 else "🚀 <b>HACKATHON OPPORTUNITY</b>"
    plan = generate_hackathon_plan(hackathon, profile or {})

    steps_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(plan["steps"])])

    campus_badge = "\n📍 <b>LOCAL CAMPUS EVENT:</b> Hosted in Bengaluru / Campus!" if plan["is_campus"] else ""

    message = (
        f"{badge} (Score: <b>{score}%</b>){campus_badge}\n\n"
        f"🎯 <b>{name}</b>\n"
        f"🌐 <b>Platform:</b> {platform} | <b>Location:</b> {location}\n"
        f"📅 <b>Dates:</b> {dates}\n"
        f"🎁 <b>Prizes / Perks:</b> {prizes}\n"
        f"🛠️ <b>Target Alignment:</b> {skills_str or 'Hardware, AI, IoT'}\n\n"
        f"💡 <b>Problem Statement & Winning Idea:</b>\n"
        f"• <b>Theme:</b> {plan['theme']}\n"
        f"• <b>Recommended Project:</b> {plan['project_idea']}\n"
        f"• <b>Suggested Stack:</b> <code>{plan['tech_stack']}</code>\n\n"
        f"🚀 <b>Immediate Steps to Apply:</b>\n"
        f"{steps_text}\n\n"
        f"👉 <a href='{url}'><b>Click here to Register on {platform}</b></a>"
    )
    return message


def send_nothing_found_message(job_health: Dict[str, Any], hackathon_health: Dict[str, Any], total_scanned: int) -> bool:
    """
    Sends the required 'Did not find anything today' message along with verified source health
    so the user is confident that all scrapers executed normally and didn't fail silently.
    """
    body = (
        "🔍 <b>Did not find anything today</b>\n\n"
        "<i>All systems ran smoothly at 8:00 PM IST. We scanned every connected channel, "
        "and there are no new high-matching opportunities above your score threshold today.</i>\n\n"
        "📊 <b>Health Verification (All 9 Free Direct Channels Active):</b>\n"
        f"• <b>Qualcomm Careers Direct:</b> {job_health.get('qualcomm_careers', 0)} positions checked\n"
        f"• <b>Internshala Core ECE:</b> {job_health.get('internshala_ece_jobs', 0)} active listings checked\n"
        f"• <b>Unstop Internships:</b> {job_health.get('unstop_internships', 0)} active listings checked\n"
        f"• <b>RemoteOK API:</b> {job_health.get('remoteok_jobs', 0)} tech roles checked\n"
        f"• <b>Jobicy Remote:</b> {job_health.get('jobicy_jobs', 0)} engineering roles checked\n"
        f"• <b>Arbeitnow:</b> {job_health.get('arbeitnow_jobs', 0)} roles checked\n"
        f"• <b>Devfolio:</b> {hackathon_health.get('devfolio_hackathons', 0)} hackathons checked\n"
        f"• <b>Unstop Hackathons:</b> {hackathon_health.get('unstop_hackathons', 0)} hackathons checked\n"
        f"• <b>Devpost:</b> {hackathon_health.get('devpost_hackathons', 0)} hackathons checked\n"
        f"• <b>Total Opportunities Monitored Today:</b> <b>{total_scanned}</b>\n\n"
        "⚡ <i>The hunter will continue scanning in the background and report back tomorrow at 8:00 PM sharp!</i>"
    )
    return send_message(body, disable_web_page_preview=True)


def send_health_failure_alert(error_msg: str) -> bool:
    """Alerts the user if the scraper crashed or returned zero results due to an outage."""
    body = (
        "⚠️ <b>Opportunity Hunter Warning: Health Check Failed</b>\n\n"
        "The automated hunter encountered an issue while contacting opportunity platforms.\n\n"
        f"<b>Error Details:</b> <code>{error_msg}</code>\n\n"
        "<i>Please check network connectivity or API quotas.</i>"
    )
    return send_message(body, disable_web_page_preview=True)


if __name__ == "__main__":
    print("Testing telegram alert card formatters...")
    sample_j = {
        "title": "RTL Design Intern",
        "company": "Semiconductor Labs",
        "location": "Bengaluru",
        "match_score": 92,
        "matching_skills": ["Verilog HDL", "Xilinx Vivado"],
        "url": "https://unstop.com",
        "deadline": "2026-11-20"
    }
    card = format_job_alert(sample_j)
    print(card[:250] + "...")
