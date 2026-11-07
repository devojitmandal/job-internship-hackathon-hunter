# 🚀 Automated Job, Internship & Hackathon Hunter

An intelligent, automated opportunity discovery engine tailored to your technical profile. Scrapes live hackathons (**Devfolio**, **Unstop**, **Devpost**) and engineering internships (**Internshala Core ECE**, **Unstop**, **Jobicy**, **Arbeitnow**, and **Google Custom Search**), scores them against your background (RTL Design, FPGA, Embedded Systems, IoT, Web Dev), and delivers real-time notifications to your Telegram chat every day at **8:00 PM IST**.

---

## 🌟 Key Features

* **Multi-Platform Scrapers**:
  * **Core ECE Internships**: Live scrapers for **Internshala** (Embedded Systems, VLSI, Electronics, IoT, Robotics).
  * **Student Tech Challenges**: Scrapers for **Devfolio**, **Unstop**, and **Devpost** (including local Bengaluru campus events).
  * **Developer Roles**: Integration with **Jobicy** and **Arbeitnow**.
  * **Google Custom Search**: Targeted queries across 50+ career domains using dual search engines (CX1 & CX2).
* **Dual-LLM Engine with Groq Fallback**:
  * Primary: Google Gemini (`gemini-3.8-flash`).
  * Fallback: Groq Cloud (`llama-3.3-70b-versatile`) when rate limits or quotas are reached.
  * Fail-safe: Deterministic heuristic advisor ensures zero downtime.
* **Tailored Resume Customization**:
  * For every matched internship, generates specific minor tweaks (which projects to lead with, which skills to re-order, and how to apply).
  * For hackathons, breaks down the theme and suggests an actionable winning project concept with registration steps.
* **Smart De-duplication**:
  * Tracks notified opportunity IDs in `data/history.json` so you never receive duplicate notifications.
* **Silent Failure Prevention**:
  * Comprehensive health verification across all sources. If no new opportunities are found, sends a verified `"Did not find anything today"` breakdown of all scanned items. If scrapers fail, immediately alerts with error details.
* **8:00 PM IST Automation**:
  * Cloud: GitHub Actions workflow (`daily_hunt.yml`) scheduled for 14:30 UTC (**8:00 PM IST**).
  * Local: Native Windows Scheduled Task (`OpportunityHunter`) and continuous runner (`src/scheduler.py`).

---

## 📁 Project Architecture

```
job-internship-hackathon-hunter/
├── .github/
│   └── workflows/
│       └── daily_hunt.yml        # GitHub Actions 8:00 PM IST cron runner
├── data/
│   ├── users/
│   │   └── devojit/
│   │       └── profile.json      # Structured profile parsed from resume (sanitized)
│   ├── hackathons.json           # Latest scraped hackathons
│   ├── jobs.json                 # Latest scraped active internships
│   ├── scored_opportunities.json # Scored & ranked matches
│   └── history.json              # De-duplication record of sent alerts
├── src/
│   ├── parse_resume.py           # Extracts structured JSON from resume PDF using Gemini
│   ├── fetch_hackathons.py       # Scrapes Devfolio, Unstop, Devpost & Google CSE
│   ├── fetch_jobs.py             # Scrapes Internshala, Unstop, Jobicy, Arbeitnow & Google CSE
│   ├── match_and_score.py        # Scores opportunities against profile.json
│   ├── advisor.py                # Dual-LLM (Gemini + Groq) resume tips & hackathon planner
│   ├── telegram_notify.py        # Telegram Bot API client and card formatter
│   ├── scheduler.py              # Continuous local 8:00 PM IST loop runner
│   └── main.py                   # Master pipeline orchestrator
├── .env.example                  # Environment template
├── requirements.txt              # Project dependencies
└── README.md
```

---

## ⚙️ Quick Start

### 1. Installation

```bash
git clone https://github.com/devojitmandal/job-internship-hackathon-hunter.git
cd job-internship-hackathon-hunter
pip install -r requirements.txt
```

### 2. Environment Setup

Create a `.env` file in the root directory:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_numeric_chat_id
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.8-flash
GROQ_API_KEY=your_groq_api_key_optional
GOOGLE_SEARCH_API_KEY=your_google_cloud_api_key
GOOGLE_SEARCH_ENGINE_ID=40b9a5bdac4314792
GOOGLE_SEARCH_ENGINE_ID_JOBS=441d50735a8ee4581
```

### 3. Usage Commands

* **Run Full Hunt & Send Alerts**:
  ```bash
  python src/main.py
  ```
* **Dry Run (Fetch & score without sending Telegram alerts)**:
  ```bash
  python src/main.py --dry-run
  ```
* **Continuous Local 8:00 PM IST Scheduler**:
  ```bash
  python src/scheduler.py
  ```
* **Test Telegram Connection**:
  ```bash
  python src/telegram_notify.py
  ```

---

## 🤖 GitHub Actions Setup (Cloud Automation at 8:00 PM IST)

The workflow in `.github/workflows/daily_hunt.yml` runs daily at **14:30 UTC (8:00 PM IST)**.
Set the following secrets in **Settings > Secrets and variables > Actions**:
* `TELEGRAM_BOT_TOKEN`
* `TELEGRAM_CHAT_ID`
* `GEMINI_API_KEY`
* `GROQ_API_KEY` (optional)
* `GOOGLE_SEARCH_API_KEY` (optional)
