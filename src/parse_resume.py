# parse_resume.py
# Run this manually whenever you update your resume.
# Output: data/users/devojit/profile.json

import os
import re
import json
import time
import fitz  # PyMuPDF
from google import genai
from datetime import datetime, timezone
from dotenv import load_dotenv

# ── Load environment variables ──────────────────────────────────────────────
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
RESUME_PATH = "resume/resume.pdf"
OUTPUT_PATH = "data/users/devojit/profile.json"
MAX_RETRIES = 3

# ── Schema that Gemini must follow ──────────────────────────────────────────
SCHEMA = {
    "name": "string",
    "email": "string",
    "phone": "string",
    "education": {
        "degree": "string",
        "branch": "string",
        "college": "string",
        "graduation_year": "string"
    },
    "skills": ["list of strings"],
    "projects": [
        {
            "name": "string",
            "description": "string",
            "technologies": ["list of strings"]
        }
    ],
    "target_roles": ["list of strings inferred from resume context"],
    "experience_level": "fresher | junior | mid",
    "languages": ["list of programming languages only"],
    "hackathon_achievements": [
        {
            "name": "string",
            "rank": "string",
            "total_participants": "string",
            "platform": "string"
        }
    ],
    "last_parsed": "ISO timestamp — leave as empty string, will be filled by script"
}

GEMINI_PROMPT = f"""You are a resume parser. Extract structured information from the resume text below.
Return ONLY a valid JSON object. No markdown, no code fences, no explanation, no extra text.
Follow this schema exactly:

{json.dumps(SCHEMA, indent=2)}

For target_roles: infer 3-5 specific job/internship titles this person would realistically apply for, based on their skills and projects.
For experience_level: use "fresher" if they are a student with no full-time work experience.
For last_parsed: leave as an empty string.

Resume text:
"""


def extract_text_from_pdf(path):
    doc = fitz.open(path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()
    return full_text.strip()


def parse_resume_with_gemini(resume_text):
    client = genai.Client(api_key=GEMINI_API_KEY)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=GEMINI_PROMPT + resume_text,
                config={"response_mime_type": "application/json"},
            )
            return response.text.strip()
        except Exception as e:
            message = str(e)
            is_rate_limit = "429" in message or "RESOURCE_EXHAUSTED" in message
            if not is_rate_limit or attempt == MAX_RETRIES:
                raise

            # Gemini usually says "Please retry in 24.3s" — use that if present
            match = re.search(r"retry in ([\d.]+)s", message)
            wait_seconds = float(match.group(1)) + 2 if match else 30
            print(f"Rate limit hit (attempt {attempt}/{MAX_RETRIES}). "
                  f"Waiting {wait_seconds:.0f}s before retrying...")
            time.sleep(wait_seconds)


def save_profile(profile_dict):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(profile_dict, f, indent=2, ensure_ascii=False)


def main():
    # ── Validate environment ─────────────────────────────────────────────────
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not found in environment. Check your .env file.")
        return

    # ── Check resume file exists ─────────────────────────────────────────────
    if not os.path.exists(RESUME_PATH):
        print(f"ERROR: Resume not found at '{RESUME_PATH}'.")
        print("Make sure your resume PDF is placed at resume/resume.pdf")
        return

    print("Extracting text from resume...")
    resume_text = extract_text_from_pdf(RESUME_PATH)

    if not resume_text:
        print("ERROR: Could not extract any text from the PDF. Is it a scanned image?")
        return

    print(f"Extracted {len(resume_text)} characters. Sending to Gemini ({GEMINI_MODEL})...")

    # ── Call Gemini ──────────────────────────────────────────────────────────
    try:
        raw_response = parse_resume_with_gemini(resume_text)
    except Exception as e:
        print(f"ERROR: Gemini API call failed: {e}")
        return

    # ── Parse JSON response ──────────────────────────────────────────────────
    try:
        # Strip accidental markdown fences if Gemini adds them despite instructions
        cleaned = raw_response
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        profile = json.loads(cleaned)
    except json.JSONDecodeError:
        print("ERROR: Gemini did not return valid JSON. Raw response:")
        print(raw_response)
        return

    # ── Add timestamp ────────────────────────────────────────────────────────
    profile["last_parsed"] = datetime.now(timezone.utc).isoformat()

    # ── Save to disk ─────────────────────────────────────────────────────────
    save_profile(profile)

    print(f"\nResume parsed successfully. Profile saved to: {OUTPUT_PATH}")
    print("\nExtracted profile:")
    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    main()