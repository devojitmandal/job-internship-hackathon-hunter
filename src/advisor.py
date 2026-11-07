# advisor.py
# Generates personalized resume customization tips and hackathon action plans.
# Supports Gemini API with timeout protection, instant quota failover,
# Groq API fallback (llama-3.3-70b-versatile), and instantaneous heuristic advice.

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Circuit breaker: If Gemini hits quota, disable for the remainder of this run
_GEMINI_EXHAUSTED = False


def call_llm_json(prompt: str) -> Optional[Dict[str, Any]]:
    """
    Calls Gemini API with strict timeout and failover to Groq API.
    Guarantees no hanging or exponential backoff delay.
    """
    global _GEMINI_EXHAUSTED

    # 1. Try Gemini (only if not already marked as exhausted in this run)
    if not _GEMINI_EXHAUSTED and GEMINI_API_KEY:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=GEMINI_API_KEY,
                http_options=types.HttpOptions(timeout=3000)  # 3-second hard timeout
            )
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text.strip())
        except Exception as e:
            logger.warning("Gemini call failed (%s). Disabling Gemini for this run.", type(e).__name__)
            _GEMINI_EXHAUSTED = True

    # 2. Try Groq Fallback
    if GROQ_API_KEY:
        try:
            import groq
            groq_client = groq.Groq(api_key=GROQ_API_KEY, timeout=4.0)
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a career and resume advisor. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            raw = completion.choices[0].message.content
            return json.loads(raw.strip())
        except Exception as e:
            logger.warning("Groq fallback failed: %s", type(e).__name__)

    return None


def generate_resume_tips(job: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates actionable minor tweaks for the candidate's resume based on the job requirements.
    Uses AI if available, with instantaneous heuristic rule-based fallback.
    """
    title = job.get("title", "")
    company = job.get("company", "")
    desc = (job.get("description", "") + " " + " ".join(job.get("skills_hint", []))).lower()
    combined = f"{title.lower()} {desc}"

    # Only attempt LLM if quota is not exhausted
    if not _GEMINI_EXHAUSTED or GROQ_API_KEY:
        prompt = f"""Given this engineering candidate and job listing, generate 3 specific, minor resume modifications to maximize interview chances.

Candidate:
- Degree: B.E. in Electronics & Communication (ECE)
- Top Skills: Verilog HDL, Xilinx Vivado, RTL Design, ESP32-C3, C, Python, React
- Projects: 4-bit ALU & Combinational Subsystems in Verilog, Advanced Biometric Watch (ESP32-C3 Firmware), Student Management System (C), Interactive Portfolio (React)

Job:
- Title: {title}
- Company: {company}
- Details: {desc[:200]}

Return JSON:
{{
  "project_tip": "Specific recommendation on which project to lead with and what bullet point to emphasize",
  "skill_tip": "Exact technical skills to re-order to the top of Technical Skills section",
  "highlight_tip": "One key academic or competition detail to highlight for this specific company"
}}
"""
        ai_result = call_llm_json(prompt)
        if ai_result and "project_tip" in ai_result:
            return ai_result

    # Instantaneous Deterministic Rule-Based Fallback (< 0.001s)
    project_tip = ""
    skill_tip = ""
    highlight_tip = ""

    if any(k in combined for k in ["rtl", "verilog", "fpga", "vivado", "vlsi", "asic", "digital logic", "digital design"]):
        project_tip = "Lead with 'Digital Logic & RTL Design Lab Projects'; emphasize your 4-bit ALU, structural/behavioral RTL modeling, and Vivado simulation waveforms."
        skill_tip = "List Verilog HDL, Xilinx Vivado, and RTL Design first under Technical Skills."
        highlight_tip = "Highlight your ongoing 3rd Semester ECE coursework in Combinational & Sequential Logic."

    elif any(k in combined for k in ["embedded", "firmware", "esp32", "microcontroller", "arduino", "i2c", "spi", "sensors"]):
        project_tip = "Spotlight the 'Advanced Biometric Watch v3.0'; emphasize ESP32-C3 firmware, I2C/SPI bus protocols, and real-time biological sensor data extraction."
        skill_tip = "Highlight C (Intermediate), ESP32-C3, I2C, SPI, and Wokwi Simulation."
        highlight_tip = "Reference your basic circuit design and mathematical biological sensor modeling."

    elif any(k in combined for k in ["hardware", "electronics", "robotics", "circuit", "pcb", "ece"]):
        project_tip = "Feature both the Biometric Watch (hardware interfacing) and Digital Logic ALU projects."
        skill_tip = "Promote Basic Circuit Design, ESP32, and Xilinx Vivado alongside C and Python."
        highlight_tip = "Highlight your ECE degree and strong fundamentals in circuit analysis and hardware debugging."

    elif any(k in combined for k in ["frontend", "front-end", "react", "ui", "web", "javascript"]):
        project_tip = "Lead with the 'Space-Themed Interactive Portfolio' and 'Resilience Hub' React prototype."
        skill_tip = "List React, Tailwind CSS, Vite, and HTML/CSS at the top of your skills."
        highlight_tip = "Highlight your experience bridging hardware concepts with modern web UIs."

    else:
        project_tip = "Lead with the 'Student Management System' (C data structures) and Python projects."
        skill_tip = "Emphasize C, Python (Intermediate), and Git/GitHub."
        highlight_tip = "Emphasize problem-solving, structured algorithms, and Top 50 hackathon finish."

    return {
        "project_tip": project_tip,
        "skill_tip": skill_tip,
        "highlight_tip": highlight_tip
    }


def generate_hackathon_plan(hackathon: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates problem statement analysis, winning idea, and immediate application steps.
    """
    name = hackathon.get("name", "")
    tagline = hackathon.get("tagline", "") or hackathon.get("description", "")
    platform = hackathon.get("platform", "Platform")
    location = hackathon.get("location", "")
    text = f"{name} {tagline} {location}".lower()

    is_campus = any(loc in text for loc in ["acharya", "bengaluru", "bangalore"])

    if any(k in text for k in ["iot", "hardware", "robot", "embedded"]):
        theme = "Hardware, Smart IoT & Embedded Solutions"
        project_idea = "A Smart Edge Device: Pitch an ESP32-C3 health or environmental telemetry hub with offline sensor caching and OLED display."
        tech_stack = "ESP32-C3, C/C++, I2C/SPI sensors, Wokwi"
    elif any(k in text for k in ["ai", "genai", "machine learning", "intelligence"]):
        theme = "AI-Driven Applications & Automation"
        project_idea = "AI Health Assistant or Smart ECE Workflow: Pitch an interactive tool combining Gemini/Groq with an embedded sensor simulator or assistive terminal."
        tech_stack = "Python, Gemini / Groq API, React, Tailwind CSS"
    elif any(k in text for k in ["web3", "blockchain", "crypto", "defi"]):
        theme = "Decentralized Tech & Open Innovation"
        project_idea = "Decentralized Hardware Identity: Connect IoT sensor metrics to a verified tamper-proof registry."
        tech_stack = "React, ESP32, Python, Web APIs"
    else:
        theme = "Open Innovation & Problem Solving"
        project_idea = "Edge-to-Cloud Resilience Monitor: A dual-mode wearable concept linking low-power microcontrollers with a real-time web dashboard."
        tech_stack = "ESP32-C3, React, Tailwind CSS, Python"

    steps = [
        f"Click the application link below to visit {platform}.",
        "Register your profile (solo or invite 2-4 college teammates).",
        f"Submit project abstract titled around: '{project_idea.split(':')[0]}'.",
        "Prepare an initial GitHub repository with README and architecture diagram."
    ]

    return {
        "theme": theme,
        "project_idea": project_idea,
        "tech_stack": tech_stack,
        "is_campus": is_campus,
        "steps": steps
    }
