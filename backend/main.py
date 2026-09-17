# ── Imports ───────────────────────────────────────────────────────────────────
import os
import sys
import re                          # For stripping markdown fences from Gemini response
import json                        # For parsing Gemini's JSON output
import io                          # For reading file bytes in memory
import uuid
import hashlib
import secrets
import urllib.request
import urllib.error
import zipfile                     # For unpacking .docx files (they are ZIP archives)
import xml.etree.ElementTree as ET # For parsing the XML inside .docx files
from datetime import datetime, timezone      # For timestamping each saved project
from typing import Optional, List, Dict, Any

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        load_dotenv(env_file)
    else:
        load_dotenv()
except ImportError:
    pass

def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path, override=True)
        except Exception:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip("\"'")
    return os.environ.get(key, default)

from bson import ObjectId          # For converting string IDs to MongoDB ObjectId format
from bson.errors import InvalidId
import gridfs
from pymongo import MongoClient    # MongoDB Python driver
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

try:
    from google import genai       # Official Gemini AI client
    from google.genai import types
except ImportError:
    genai = None
    types = None

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
try:
    import requests
except ImportError:
    requests = None
import uvicorn


# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="Agentic Resource Allocation Engine with Player Cards")

# Allow React frontend and external services
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Gemini Client Setup ───────────────────────────────────────────────────────
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
client = None
if genai is not None and GOOGLE_API_KEY:
    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)
    except Exception as e:
        print(f"[WARN] Failed to initialize genai.Client: {e}")
        client = None

# ── Resilient Database Layer (MongoDB + In-Memory Fallback) ───────────────────
memory_projects: Dict[str, dict] = {}
memory_candidates: Dict[str, dict] = {}
memory_files: Dict[str, dict] = {}
memory_users: Dict[str, dict] = {}
memory_notifications: List[dict] = []
active_sessions: Dict[str, dict] = {}

has_mongo = False
projects_col = None
candidates_col = None
users_col = None
notifications_col = None
fs = None

try:
    mongo = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=1200)
    mongo.server_info()  # Check if server is actually alive
    db = mongo["pong_ai"]
    projects_col = db["projects"]
    candidates_col = db["candidates"]
    users_col = db["users"]
    notifications_col = db["notifications"]
    fs = gridfs.GridFS(db)
    has_mongo = True
    print("[INFO] Connected successfully to local MongoDB.")
except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
    print(f"[WARN] MongoDB not available ({e}). Using resilient in-memory store for projects, candidates, users & notifications.")
    has_mongo = False

# ── Backend Authentication Utilities ─────────────────────────────────────────
def hash_password(password: str, salt: str = "") -> str:
    if not salt:
        salt = secrets.token_hex(8)
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}:{h}"

def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash or ":" not in stored_hash:
        return False
    salt, h = stored_hash.split(":", 1)
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest() == h

# Pre-seeded default Manager account (Zero mock applicants)
DEFAULT_MANAGERS = [
    {
        "id": "mgr_01",
        "email": "manager@enterprise.io",
        "name": "Sarah Chen",
        "role": "manager",
        "department": "Engineering & Delivery Operations",
        "password_hash": hash_password("manager123", salt="p0ngs@lt1"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
]

for mgr in DEFAULT_MANAGERS:
    memory_users[mgr["email"]] = mgr.copy()
    if has_mongo and users_col is not None:
        try:
            users_col.update_one({"email": mgr["email"]}, {"$set": mgr.copy()}, upsert=True)
        except Exception:
            pass

# ── In-App Notifications Helper ──────────────────────────────────────────────
def add_notification(notif: dict):
    """Adds a notification to memory and MongoDB."""
    if "id" not in notif:
        notif["id"] = f"notif_{uuid.uuid4().hex[:8]}"
    if "created_at" not in notif:
        notif["created_at"] = datetime.now(timezone.utc).isoformat()
    if "read" not in notif:
        notif["read"] = False
    memory_notifications.insert(0, notif)
    if has_mongo and notifications_col is not None:
        try:
            notifications_col.insert_one(notif.copy())
        except Exception:
            pass

# ── Role style map ────────────────────────────────────────────────────────────
# ── Role style map ────────────────────────────────────────────────────────────
ROLE_STYLE = {
    "project manager":        {"icon": "PM", "color": "#8b5cf6"},
    "backend developer":      {"icon": "BE",  "color": "#3b82f6"},
    "backend engineer":       {"icon": "BE",  "color": "#3b82f6"},
    "frontend developer":     {"icon": "FE", "color": "#06b6d4"},
    "frontend engineer":      {"icon": "FE", "color": "#06b6d4"},
    "full-stack engineer":    {"icon": "FS", "color": "#f59e0b"},
    "full stack engineer":    {"icon": "FS", "color": "#f59e0b"},
    "qa engineer":            {"icon": "QA", "color": "#f43f5e"},
    "devops engineer":        {"icon": "OPS", "color": "#f59e0b"},
    "devops":                 {"icon": "OPS", "color": "#f59e0b"},
    "tech lead":              {"icon": "LEAD", "color": "#6366f1"},
    "tech lead / backend":    {"icon": "LEAD", "color": "#6366f1"},
    "tech lead / pm":         {"icon": "LEAD", "color": "#6366f1"},
    "frontend engineer / qa": {"icon": "UI/QA", "color": "#10b981"},
    "ai/ml engineer":         {"icon": "AI", "color": "#ec4899"},
    "data engineer":          {"icon": "DATA", "color": "#14b8a6"},
    "security engineer":      {"icon": "SEC", "color": "#ef4444"},
}

def style_for_role(role_name: str) -> dict:
    key = role_name.lower().strip()
    for pattern, style in ROLE_STYLE.items():
        if pattern in key:
            return style
            
    # Domain specific heuristics
    if any(k in key for k in ["event director", "producer"]):
        return {"icon": "EVT", "color": "#8b5cf6"}
    if any(k in key for k in ["venue", "logistics", "coordinator"]):
        return {"icon": "LOG", "color": "#0ea5e9"}
    if any(k in key for k in ["hospitality", "guest", "experience"]):
        return {"icon": "HOSP", "color": "#10b981"}
    if any(k in key for k in ["stage", "av", "sound", "lighting"]):
        return {"icon": "AV", "color": "#f59e0b"}
    if any(k in key for k in ["qa lead", "test strategist", "qa"]):
        return {"icon": "QA", "color": "#f43f5e"}
    if any(k in key for k in ["automation", "automated"]):
        return {"icon": "AUTO", "color": "#06b6d4"}
    if any(k in key for k in ["performance", "load"]):
        return {"icon": "PERF", "color": "#eab308"}
    if any(k in key for k in ["security", "penetration", "compliance"]):
        return {"icon": "SEC", "color": "#ef4444"}
    if any(k in key for k in ["marketing", "campaign", "growth"]):
        return {"icon": "MKT", "color": "#ec4899"}
    if any(k in key for k in ["content", "creative", "brand"]):
        return {"icon": "CRTV", "color": "#a855f7"}
    if any(k in key for k in ["lead", "pm", "manager", "director"]):
        return {"icon": "LEAD", "color": "#6366f1"}

    # Dynamic fallback based on role words
    words = [w for w in re.split(r"\W+", role_name) if w]
    if len(words) >= 2:
        icon = (words[0][0] + words[1][0]).upper()
    elif len(words) == 1:
        icon = words[0][:3].upper()
    else:
        icon = "ROLE"
    return {"icon": icon, "color": "#6366f1"}

# ── Seed Candidate Player Cards (PURGED: Zero hardcoded mock names) ───────────
SEED_CANDIDATES = []

# ── Seed Multi-Department Enterprise Projects (IT, Event, Testing) ───────────
SEED_PROJECTS = [
    {
        "id": "proj_event_summit_2026",
        "project_name": "Global Tech Summit & Partner Expo 2026",
        "domain": "Event Management & Production",
        "team_size": 4,
        "domain_skills": ["Venue Logistics", "Vendor Negotiation", "Event Budgeting", "Guest Hospitality", "Stage Production", "Crisis & Safety"],
        "tech_signals": ["Venue Contracting", "On-site Attendee Flow", "Keynote AV Production", "Catering & Hospitality", "Sponsor Booth Allocation"],
        "total_roles": 4,
        "roles": [
            {
                "role": "Event Director & Executive Producer",
                "icon": "EVT",
                "badge": "Lead",
                "color": "#8b5cf6",
                "tasks": [
                    "Lead end-to-end summit execution across keynotes, partner tracks, and sponsor exhibits",
                    "Negotiate high-value venue, catering, and audio-visual vendor service contracts",
                    "Manage multi-track master schedule, executive speaker arrivals, and VIP greenrooms",
                    "Oversee health, safety compliance, municipal permits, and emergency contingency plans"
                ],
                "assigned_candidate": None
            },
            {
                "role": "Venue & Logistics Coordinator",
                "icon": "LOG",
                "badge": "Specialist",
                "color": "#0ea5e9",
                "tasks": [
                    "Coordinate floorplans, booth electrical drops, and exhibitor load-in logistics",
                    "Manage attendee badge printing stations, turnstile scanning, and traffic flow",
                    "Liaise with convention center facilities management and freight shipping partners",
                    "Track real-time venue asset inventories and resolve facility access requests"
                ],
                "assigned_candidate": None
            },
            {
                "role": "Hospitality & Guest Experience Lead",
                "icon": "HOSP",
                "badge": "Dedicated",
                "color": "#10b981",
                "tasks": [
                    "Design seamless guest registration journeys, welcome desk protocols, and VIP escorting",
                    "Direct catering menus, dietary requirement tracking, and executive reception service",
                    "Coordinate partner lounge amenities, hotel room blocks, and shuttle transportation",
                    "Conduct real-time attendee sentiment polling and resolve hospitality inquiries"
                ],
                "assigned_candidate": None
            },
            {
                "role": "Stage, AV & Production Specialist",
                "icon": "AV",
                "badge": "Dedicated",
                "color": "#f59e0b",
                "tasks": [
                    "Operate main stage LED walls, confidence monitors, wireless mic frequencies, and live streams",
                    "Conduct speaker AV technical rehearsals, slide deck aspect ratio checks, and cue timing",
                    "Manage audio mixer levels, stage lighting cues, and live broadcast feed distribution",
                    "Troubleshoot signal dropouts, presentation clicker latency, and backup feed failovers"
                ],
                "assigned_candidate": None
            }
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "jira_synced": False
    },
    {
        "id": "proj_qa_compliance_suite",
        "project_name": "Enterprise Security & Automated Compliance Suite",
        "domain": "Quality Assurance & Testing",
        "team_size": 4,
        "domain_skills": ["Automated Test Suites", "Performance & Load Profiling", "Security Testing", "Test Strategy & Planning", "Defect Triage", "CI/CD Validation"],
        "tech_signals": ["End-to-End Automation", "Load & Concurrency Stress", "Penetration Auditing", "Regression Matrix", "Defect Root Cause"],
        "total_roles": 4,
        "roles": [
            {
                "role": "QA Lead & Test Strategist",
                "icon": "QA",
                "badge": "Lead",
                "color": "#f43f5e",
                "tasks": [
                    "Formulate overall test architecture covering unit, integration, regression, and E2E gates",
                    "Define pass/fail release criteria, defect severity definitions, and test signoff governance",
                    "Establish automated test reporting dashboards and defect burndown metrics",
                    "Conduct risk-based test analysis across multi-tenant billing and auth boundaries"
                ],
                "assigned_candidate": None
            },
            {
                "role": "Test Automation Engineer",
                "icon": "AUTO",
                "badge": "Specialist",
                "color": "#06b6d4",
                "tasks": [
                    "Author Playwright and Cypress end-to-end regression suites for critical user journeys",
                    "Integrate automated smoke and sanity suites into GitHub Actions PR validation gates",
                    "Maintain test fixture data factories and isolated ephemeral test database environments",
                    "Reduce test execution flakiness and optimize parallel browser worker execution"
                ],
                "assigned_candidate": None
            },
            {
                "role": "Performance & Load Test Specialist",
                "icon": "PERF",
                "badge": "Dedicated",
                "color": "#eab308",
                "tasks": [
                    "Simulate high-concurrency peak traffic loads using Locust and k6 test scenarios",
                    "Profile API response latencies (p95, p99) under synthetic stress conditions",
                    "Identify database connection pool starvation and CPU thread contention bottlenecks",
                    "Generate load testing benchmark reports and resource autoscaling recommendations"
                ],
                "assigned_candidate": None
            },
            {
                "role": "Security & Compliance Tester",
                "icon": "SEC",
                "badge": "Dedicated",
                "color": "#ef4444",
                "tasks": [
                    "Execute OWASP Top 10 vulnerability assessments across public REST endpoints",
                    "Audit authentication token lifecycle, privilege escalation vectors, and rate limits",
                    "Verify data-at-rest encryption compliance and sanitized customer PII log masking",
                    "Produce security compliance evidence documentation for SOC2 and ISO27001 audits"
                ],
                "assigned_candidate": None
            }
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "jira_synced": False
    },
    {
        "id": "proj_it_payment_gateway",
        "project_name": "High-Concurrency Payment Gateway & Service Mesh",
        "domain": "Enterprise IT & Cloud",
        "team_size": 4,
        "domain_skills": ["API Architecture", "Backend Concurrency", "System Design", "UI / UX Interface", "Cloud Infrastructure", "Technical Communication"],
        "tech_signals": ["REST & gRPC Microservices", "PostgreSQL Sharding", "Kubernetes Clustering", "Zero-Trust JWT Auth", "Prometheus Telemetry"],
        "total_roles": 4,
        "roles": [
            {
                "role": "Lead API & Backend Architect",
                "icon": "BE",
                "badge": "Lead",
                "color": "#3b82f6",
                "tasks": [
                    "Design high-throughput REST and gRPC gateway contracts with idempotency keys",
                    "Implement double-entry transactional accounting ledgers on PostgreSQL",
                    "Construct Redis distributed locking mechanisms for transaction deduplication",
                    "Establish automated contract validation and API latency monitoring"
                ],
                "assigned_candidate": None
            },
            {
                "role": "Frontend Operations Dashboard Engineer",
                "icon": "FE",
                "badge": "Dedicated",
                "color": "#06b6d4",
                "tasks": [
                    "Build responsive transaction inspection dashboard with real-time settlement views",
                    "Implement dispute management workflows and customer refund initiation dialogs",
                    "Ensure accessible WCAG AA compliance, dark mode telemetry, and mobile responsiveness",
                    "Connect WebSockets for streaming ledger health and fraud anomaly alerts"
                ],
                "assigned_candidate": None
            },
            {
                "role": "Cloud Infrastructure & DevOps Specialist",
                "icon": "OPS",
                "badge": "Dedicated",
                "color": "#f59e0b",
                "tasks": [
                    "Deploy multi-region Kubernetes clusters with automated canary rollout strategies",
                    "Provision cloud infrastructure with Terraform including managed HSM keys",
                    "Configure Prometheus metrics, OpenTelemetry tracing, and PagerDuty escalations",
                    "Enforce strict egress firewall rules and PCI-DSS network segmentation"
                ],
                "assigned_candidate": None
            },
            {
                "role": "Technical Systems Director",
                "icon": "LEAD",
                "badge": "Dedicated",
                "color": "#6366f1",
                "tasks": [
                    "Define cross-service SLA targets, error budgets, and architecture governance",
                    "Coordinate API deprecation schedules with downstream merchant partner teams",
                    "Conduct architectural risk reviews and lead incident post-mortem retrospectives",
                    "Deliver executive readiness briefings for quarterly compliance certifications"
                ],
                "assigned_candidate": None
            }
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "jira_synced": False
    }
]

# Initialize seed projects in memory and Mongo
for sp in SEED_PROJECTS:
    memory_projects[sp["id"]] = sp.copy()
    if has_mongo and projects_col is not None:
        try:
            projects_col.update_one({"id": sp["id"]}, {"$set": sp.copy()}, upsert=True)
        except Exception:
            pass


def get_all_candidates() -> List[dict]:
    """Retrieve candidates from MongoDB or fallback to in-memory store."""
    if has_mongo and candidates_col is not None:
        try:
            docs = list(candidates_col.find())
            if docs:
                res = []
                for d in docs:
                    item = d.copy()
                    item["id"] = str(item.pop("_id"))
                    res.append(item)
                return res
        except Exception:
            pass
    return list(memory_candidates.values())


def upsert_candidate(card: dict) -> dict:
    """Save or update candidate Player Card in Mongo and in-memory store."""
    cid = card.get("candidate_id") or f"cand_{uuid.uuid4().hex[:8]}"
    card["candidate_id"] = cid
    memory_candidates[cid] = card.copy()

    if has_mongo and candidates_col is not None:
        try:
            candidates_col.update_one(
                {"candidate_id": cid},
                {"$set": card},
                upsert=True
            )
        except Exception as e:
            print(f"[WARN] Failed to write candidate to MongoDB: {e}")
    return card


# Ensure MongoDB has seed data if connected
if has_mongo and candidates_col is not None:
    try:
        if candidates_col.count_documents({}) == 0:
            for sc in SEED_CANDIDATES:
                candidates_col.insert_one(sc.copy())
    except Exception:
        pass


# ── Gemini prompt template ────────────────────────────────────────────────────
PROMPT_TEMPLATE = """You are an expert enterprise project analyst and resource allocator across diverse industry domains (including Software & Cloud Engineering, Event Management & Production, Quality Assurance & Testing, Creative Marketing, Operations, and Healthcare).

Read the project scope document below and the team size, then output a structured JSON resource allocation plan.

Rules:
1. Identify the project domain (e.g. "Event Management & Production", "Quality Assurance & Testing", "Enterprise IT & Cloud", "Marketing & Creative Strategy", "Operations & Logistics").
2. Define 6 relevant skill dimensions specific to this domain that candidate suitability should be measured against (e.g. for Event: ["Venue Logistics", "Vendor Negotiation", "Event Budgeting", "Guest Hospitality", "Stage Production", "Crisis & Safety"]; for QA: ["Automated Test Suites", "Performance & Load Profiling", "Security Testing", "Test Strategy & Planning", "Defect Triage", "CI/CD Validation"]; for IT: ["API Architecture", "Backend Concurrency", "System Design", "UI / UX Interface", "Cloud Infrastructure", "Technical Communication"]).
3. Adapt role composition to the team size. Roles MUST be tailored to the actual domain (e.g. if the document is an Event brief, output Event Director, Logistics Coordinator, Hospitality Lead, Stage Producer; do NOT output software engineering roles unless the document is IT-focused).
4. Every task must be SPECIFIC to the actual project content — not generic boilerplate.
5. Assign 4-6 actionable tasks per role derived from the document.
6. tech_signals: list 4-6 key tools, methodologies, standards, or concepts mentioned in the document.

Respond ONLY with a valid JSON object — no markdown fences, no explanation, no preamble.

JSON schema:
{{
  "project_name": "string",
  "domain": "string",
  "domain_skills": ["string", "string", "string", "string", "string", "string"],
  "tech_signals": ["string"],
  "roles": [
    {{
      "role": "string",
      "badge": "Dedicated | Hybrid | Lead | Specialist",
      "tasks": ["string"]
    }}
  ]
}}

Team size: {team_size}

--- PROJECT DOCUMENT ---
{document}
--- END DOCUMENT ---"""

# ── Text extraction helpers ───────────────────────────────────────────────────

def extract_docx_text(raw_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
            xml = archive.read("word/document.xml")
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        root = ET.fromstring(xml)
        paragraphs = []
        for paragraph in root.findall(".//w:p", namespace):
            parts = [n.text for n in paragraph.findall(".//w:t", namespace) if n.text]
            if parts:
                paragraphs.append("".join(parts))
        return "\n".join(paragraphs)
    except Exception:
        return ""

def extract_pdf_text(raw_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n".join(pages)
    except Exception as e:
        print(f"[ERROR] PDF extraction failed: {e}")
        return ""

def extract_text(file: UploadFile, raw_bytes: bytes) -> str:
    filename = (file.filename or "").lower()
    if filename.endswith(".docx"):
        return extract_docx_text(raw_bytes)
    if filename.endswith(".pdf"):
        return extract_pdf_text(raw_bytes)
    return raw_bytes.decode("utf-8", errors="ignore")

# ── Gemini API call ───────────────────────────────────────────────────────────

def ask_gemini(document_text: str, team_size: int) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or GOOGLE_API_KEY
    if not api_key:
        print("[WARN] No GEMINI_API_KEY found; falling back to intelligent parser.")
        return simulate_project_decomposition(document_text, team_size)

    prompt = PROMPT_TEMPLATE.format(
        team_size=team_size,
        document=document_text[:12000],
    )

    # 1. Try official SDK client if available
    if client is not None:
        for model_name in ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-3.5-flash-lite"]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                raw = response.text.strip()
                raw = re.sub(r"^```(?:json)?", "", raw).strip()
                raw = re.sub(r"```$", "", raw).strip()
                return json.loads(raw)
            except Exception as e:
                print(f"[WARN] Gemini SDK model {model_name} failed: {e}")

    # 2. Resilient Direct REST API Fallback via urllib (zero external dependencies)
    for model_name in ["gemini-2.0-flash", "gemini-1.5-flash"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload_data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                raw = resp_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                raw = re.sub(r"^```(?:json)?", "", raw).strip()
                raw = re.sub(r"```$", "", raw).strip()
                return json.loads(raw)
        except Exception as e:
            print(f"[WARN] Gemini REST call for {model_name} failed: {e}")

    print("[WARN] All Gemini API attempts failed; falling back to intelligent simulation parser.")
    return simulate_project_decomposition(document_text, team_size)


def simulate_project_decomposition(document_text: str, team_size: int) -> dict:
    """Deterministic, content-aware multi-domain decomposition fallback."""
    doc_lower = document_text.lower()
    
    # 1. Event Management Domain
    if any(k in doc_lower for k in ["event", "conference", "summit", "venue", "hospitality", "catering", "sponsor", "stage", "guest", "exhibition"]):
        domain = "Event Management & Production"
        domain_skills = ["Venue Logistics", "Vendor Negotiation", "Event Budgeting", "Guest Hospitality", "Stage Production", "Crisis & Safety"]
        tech_signals = ["Venue Floorplan", "Keynote AV Production", "Guest Registration", "Sponsor Relations", "Catering & Hospitality"]
        all_roles = [
            {
                "role": "Event Director & Executive Producer",
                "badge": "Lead",
                "tasks": [
                    "Lead end-to-end summit execution across keynotes, partner tracks, and sponsor exhibits",
                    "Negotiate high-value venue, catering, and audio-visual vendor service contracts",
                    "Manage multi-track master schedule, executive speaker arrivals, and VIP greenrooms",
                    "Oversee health, safety compliance, municipal permits, and emergency contingency plans"
                ]
            },
            {
                "role": "Venue & Logistics Coordinator",
                "badge": "Specialist",
                "tasks": [
                    "Coordinate floorplans, booth electrical drops, and exhibitor load-in logistics",
                    "Manage attendee badge printing stations, turnstile scanning, and traffic flow",
                    "Liaise with convention center facilities management and freight shipping partners",
                    "Track real-time venue asset inventories and resolve facility access requests"
                ]
            },
            {
                "role": "Hospitality & Guest Experience Lead",
                "badge": "Dedicated",
                "tasks": [
                    "Design seamless guest registration journeys, welcome desk protocols, and VIP escorting",
                    "Direct catering menus, dietary requirement tracking, and executive reception service",
                    "Coordinate partner lounge amenities, hotel room blocks, and shuttle transportation",
                    "Conduct real-time attendee sentiment polling and resolve hospitality inquiries"
                ]
            },
            {
                "role": "Stage, AV & Production Specialist",
                "badge": "Dedicated",
                "tasks": [
                    "Operate main stage LED walls, confidence monitors, wireless mic frequencies, and live streams",
                    "Conduct speaker AV technical rehearsals, slide deck aspect ratio checks, and cue timing",
                    "Manage audio mixer levels, stage lighting cues, and live broadcast feed distribution",
                    "Troubleshoot signal dropouts, presentation clicker latency, and backup feed failovers"
                ]
            }
        ]
    # 2. Quality Assurance & Testing Domain
    elif any(k in doc_lower for k in ["test", "testing", "qa", "quality assurance", "automation", "regression", "cypress", "selenium", "load test", "penetration", "defect", "bug triage"]):
        domain = "Quality Assurance & Testing"
        domain_skills = ["Automated Test Suites", "Performance & Load Profiling", "Security Testing", "Test Strategy & Planning", "Defect Triage", "CI/CD Validation"]
        tech_signals = ["Playwright/Cypress", "k6 Load Testing", "OWASP Security", "Defect Burndown", "GitHub Actions CI"]
        all_roles = [
            {
                "role": "QA Lead & Test Strategist",
                "badge": "Lead",
                "tasks": [
                    "Formulate overall test architecture covering unit, integration, regression, and E2E gates",
                    "Define pass/fail release criteria, defect severity definitions, and test signoff governance",
                    "Establish automated test reporting dashboards and defect burndown metrics",
                    "Conduct risk-based test analysis across multi-tenant billing and auth boundaries"
                ]
            },
            {
                "role": "Test Automation Engineer",
                "badge": "Specialist",
                "tasks": [
                    "Author Playwright and Cypress end-to-end regression suites for critical user journeys",
                    "Integrate automated smoke and sanity suites into GitHub Actions PR validation gates",
                    "Maintain test fixture data factories and isolated ephemeral test database environments",
                    "Reduce test execution flakiness and optimize parallel browser worker execution"
                ]
            },
            {
                "role": "Performance & Load Test Specialist",
                "badge": "Dedicated",
                "tasks": [
                    "Simulate high-concurrency peak traffic loads using Locust and k6 test scenarios",
                    "Profile API response latencies (p95, p99) under synthetic stress conditions",
                    "Identify database connection pool starvation and CPU thread contention bottlenecks",
                    "Generate load testing benchmark reports and resource autoscaling recommendations"
                ]
            },
            {
                "role": "Security & Compliance Tester",
                "badge": "Dedicated",
                "tasks": [
                    "Execute OWASP Top 10 vulnerability assessments across public REST endpoints",
                    "Audit authentication token lifecycle, privilege escalation vectors, and rate limits",
                    "Verify data-at-rest encryption compliance and sanitized customer PII log masking",
                    "Produce security compliance evidence documentation for SOC2 and ISO27001 audits"
                ]
            }
        ]
    # 3. Creative Marketing Domain
    elif any(k in doc_lower for k in ["marketing", "campaign", "brand", "social media", "growth", "advertising", "content", "seo"]):
        domain = "Marketing & Creative Strategy"
        domain_skills = ["Growth Strategy", "Content Production", "Brand Identity", "Performance Marketing", "Social Engagement", "Analytics & Conversion"]
        tech_signals = ["Multi-Channel Ads", "Brand Identity Guide", "SEO Optimization", "Social Retargeting", "Conversion Funnels"]
        all_roles = [
            {
                "role": "Marketing Director & Campaign Lead",
                "badge": "Lead",
                "tasks": [
                    "Develop integrated campaign positioning, audience personas, and media flight schedules",
                    "Manage multi-channel marketing budget allocation across paid, earned, and owned media",
                    "Define KPI metrics (CPA, ROAS, LTV) and deliver executive performance scorecards",
                    "Coordinate agency partners, influencer agreements, and brand safety guidelines"
                ]
            },
            {
                "role": "Creative Content & Brand Producer",
                "badge": "Specialist",
                "tasks": [
                    "Produce brand storytelling assets, video teasers, and high-impact copy for launch",
                    "Maintain brand style guide consistency across typography, tone, and visual identity",
                    "Create interactive landing page content modules with conversion-focused UX copy",
                    "Supervise creative asset library, rights clearance, and localized asset variations"
                ]
            },
            {
                "role": "Performance Marketing Specialist",
                "badge": "Dedicated",
                "tasks": [
                    "Configure programmatic ad campaigns across Google Ads, LinkedIn, and Meta ad managers",
                    "Conduct continuous A/B multivariate testing on ad creatives, headlines, and bid tactics",
                    "Instrument UTM tracking schemas, attribution modeling, and conversion API postbacks",
                    "Analyze audience drop-off funnels and optimize customer acquisition unit economics"
                ]
            },
            {
                "role": "Social Media & Community Lead",
                "badge": "Dedicated",
                "tasks": [
                    "Execute real-time social engagement calendar across LinkedIn, X, and industry forums",
                    "Manage community inquiries, direct messages, and brand advocate amplification",
                    "Monitor brand sentiment, trending industry discussions, and social PR mentions",
                    "Organize interactive AMA sessions, community webinars, and user appreciation initiatives"
                ]
            }
        ]
    # 4. Default Enterprise IT & Systems Domain
    else:
        domain = "Enterprise IT & Cloud"
        domain_skills = ["API Architecture", "Backend Concurrency", "System Design", "UI / UX Interface", "Cloud Infrastructure", "Technical Communication"]
        tech_signals = ["REST API Architecture", "Microservices", "High-Concurrency Backend", "FastAPI/PostgreSQL", "Docker & Kubernetes"]
        all_roles = [
            {
                "role": "Lead API & Backend Developer",
                "badge": "Lead",
                "tasks": [
                    "Design OpenAPI 3.0 specification & high-throughput API gateway routing",
                    "Implement secure JWT authentication, rate-limiting, and error middleware",
                    "Construct relational schema and query optimization for high-concurrency endpoints",
                    "Establish automated integration tests and contract validation for all REST routes"
                ]
            },
            {
                "role": "Frontend Engineer",
                "badge": "Dedicated",
                "tasks": [
                    "Build responsive React component library and interactive user dashboards",
                    "Integrate client-side REST API consumption with optimistic UI updates",
                    "Ensure accessible WCAG compliance, mobile viewport responsiveness, and UX flow",
                    "Set up client-side error boundary handling and analytics telemetry"
                ]
            },
            {
                "role": "DevOps & Cloud Engineer",
                "badge": "Dedicated",
                "tasks": [
                    "Containerize microservices with multi-stage Docker builds",
                    "Configure GitHub Actions automated CI/CD pipeline and deployment stages",
                    "Provision cloud infrastructure with Terraform and environment secrets",
                    "Configure centralized logging, Grafana dashboard, and uptime alerts"
                ]
            },
            {
                "role": "Tech Lead / Project Manager",
                "badge": "Dedicated",
                "tasks": [
                    "Define sprint deliverables, milestone criteria, and architectural guidelines",
                    "Coordinate cross-team API contracts between frontend and backend engineers",
                    "Conduct code reviews and ensure security best practices across all modules",
                    "Prepare stakeholder presentation, sprint demo, and release documentation"
                ]
            }
        ]

    first_line = document_text.strip().split("\n")[0][:45].strip("# ").strip()
    project_name = first_line if len(first_line) > 5 else f"{domain} Initiative"

    return {
        "project_name": project_name,
        "domain": domain,
        "domain_skills": domain_skills,
        "tech_signals": tech_signals,
        "roles": all_roles[:team_size]
    }


# ── Stat-Based Role Matching Engine (PongAI Core) ─────────────────────────────

def match_candidates_to_roles(roles: list, tech_signals: list, document_text: str = "") -> list:
    """
    Compares project brief requirements against candidate Player Cards.
    Purged mock data: if no real applicants exist, returns roles with assigned_candidate as None.
    """
    candidate_pool = get_all_candidates()
    if not candidate_pool:
        # Zero mock candidates: roles remain cleanly unassigned
        return roles

    doc_lower = (document_text + " " + " ".join(tech_signals)).lower()
    is_api_heavy = any(k in doc_lower for k in [
        "api", "microservice", "rest", "graphql", "grpc", "gateway", "endpoint", "architecture", "concurrency"
    ])

    assigned_ids = set()
    matched_roles = []

    for role_item in roles:
        role_name = role_item.get("role", "").lower()
        
        # Calculate role requirement weights
        weights = {}
        if any(k in role_name for k in ["backend", "api", "database", "data"]):
            if is_api_heavy:
                # Strong emphasis on API Architecture and Backend as requested
                weights = {"api_architecture": 0.55, "backend": 0.35, "system_design": 0.10}
            else:
                weights = {"backend": 0.50, "api_architecture": 0.30, "system_design": 0.20}
        elif any(k in role_name for k in ["frontend", "ui", "ux", "client", "web"]):
            weights = {"frontend": 0.70, "communication": 0.15, "api_architecture": 0.15}
        elif any(k in role_name for k in ["devops", "cloud", "infra", "security", "qa"]):
            weights = {"devops_cloud": 0.65, "system_design": 0.20, "backend": 0.15}
        elif any(k in role_name for k in ["lead", "pm", "manager", "director", "architect"]):
            weights = {"communication": 0.40, "system_design": 0.30, "api_architecture": 0.15, "presence_energy": 0.15}
        else:
            weights = {"system_design": 0.30, "backend": 0.30, "frontend": 0.20, "communication": 0.20}

        # Find best available candidate
        best_candidate = None
        best_score = -1.0

        for cand in candidate_pool:
            cid = cand.get("candidate_id")
            if cid in assigned_ids:
                continue

            stats = cand.get("stats", {})
            score = sum(stats.get(metric, 70) * w for metric, w in weights.items())
            if score > best_score:
                best_score = score
                best_candidate = cand

        # Fallback if pool exhausted
        if not best_candidate and candidate_pool:
            best_candidate = candidate_pool[0]
            best_score = 80.0

        if best_candidate:
            assigned_ids.add(best_candidate.get("candidate_id"))
            cstats = best_candidate.get("stats", {})

            # Craft Manager Match Rationale
            if any(k in role_name for k in ["backend", "api"]):
                rationale = f"Matched {best_candidate.get('name')}: Top-ranked API Architecture ({cstats.get('api_architecture')}/100) and Backend ({cstats.get('backend')}/100) stats perfectly align with high-throughput API gateway and microservice requirements."
            elif any(k in role_name for k in ["frontend", "ui"]):
                rationale = f"Matched {best_candidate.get('name')}: Standout Frontend score ({cstats.get('frontend')}/100) and high empathy UX alignment."
            elif any(k in role_name for k in ["devops", "cloud"]):
                rationale = f"Matched {best_candidate.get('name')}: Elite DevOps & Cloud score ({cstats.get('devops_cloud')}/100) and Kubernetes/CI-CD mastery."
            else:
                rationale = f"Matched {best_candidate.get('name')}: High Communication ({cstats.get('communication')}/100) and Systems Design ({cstats.get('system_design')}/100) leadership."

            role_item["assigned_candidate"] = {
                "candidate_id": best_candidate.get("candidate_id"),
                "name": best_candidate.get("name"),
                "email": best_candidate.get("email"),
                "archetype": best_candidate.get("archetype"),
                "avatar_badge": best_candidate.get("avatar_badge"),
                "overall_rating": best_candidate.get("overall_rating"),
                "match_score": round(best_score, 1),
                "match_rationale": rationale,
                "stats": cstats,
                "strengths": best_candidate.get("key_strengths", [])
            }

        matched_roles.append(role_item)

    return matched_roles


# ── MongoDB serialization helper ──────────────────────────────────────────────

def serialize(doc: dict) -> dict:
    serialized = doc.copy()
    if "_id" in serialized:
        serialized["id"] = str(serialized.pop("_id"))
    elif "id" not in serialized:
        serialized["id"] = f"proj_{uuid.uuid4().hex[:8]}"
    if "file_id" in serialized and serialized["file_id"] is not None:
        serialized["file_id"] = str(serialized["file_id"])
    return serialized


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.post("/api/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    team_size: int = Form(4),
):
    """
    Main endpoint:
    1. Extracts project documentation.
    2. Runs Gemini project decomposition.
    3. Runs PongAI Player Card Matching Engine (stat-based candidate allocation).
    4. Persists project and returns structured result.
    """
    raw_bytes = await file.read()
    content = extract_text(file, raw_bytes)

    if not content.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from the uploaded file.")

    gemini_result = ask_gemini(content, team_size)

    # Style roles — Initial setup contains ONLY roles and tasks (Zero candidate names)
    scoped_roles = []
    for role in gemini_result.get("roles", []):
        style = style_for_role(role["role"])
        scoped_roles.append({
            "role":  role["role"],
            "icon":  style["icon"],
            "badge": role.get("badge", "Dedicated"),
            "color": style["color"],
            "tasks": role.get("tasks", []),
            "assigned_candidate": None  # No name in initial setup — only role and deliverables
        })

    tech_signals = gemini_result.get("tech_signals", [])
    domain = gemini_result.get("domain", "Enterprise IT & Cloud")
    domain_skills = gemini_result.get("domain_skills", ["Domain Skill 1", "Domain Skill 2", "Domain Skill 3", "Domain Skill 4", "Domain Skill 5", "Domain Skill 6"])

    project_id = f"proj_{uuid.uuid4().hex[:12]}"
    result = {
        "id": project_id,
        "project_name": gemini_result.get("project_name", file.filename),
        "domain": domain,
        "domain_skills": domain_skills,
        "team_size": team_size,
        "tech_signals": tech_signals,
        "total_roles": len(scoped_roles),
        "roles": scoped_roles,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "jira_synced": False
    }

    # Save to MongoDB if available, otherwise in-memory
    if has_mongo and projects_col is not None:
        try:
            if raw_bytes and fs:
                stored_file_id = fs.put(raw_bytes, filename=file.filename or "upload.bin", contentType=getattr(file, "content_type", None))
                result["file_id"] = str(stored_file_id)
                result["file_name"] = file.filename
            inserted = projects_col.insert_one(result.copy())
            result["id"] = str(inserted.inserted_id)
        except Exception as e:
            print(f"[WARN] Failed to write project to MongoDB: {e}")
            memory_projects[result["id"]] = result
    else:
        memory_projects[result["id"]] = result
        if raw_bytes:
            memory_files[result["id"]] = {
                "bytes": raw_bytes,
                "filename": file.filename,
                "content_type": getattr(file, "content_type", "application/octet-stream")
            }

    return result


@app.post("/api/projects/{project_id}/match")
def match_project_candidates(project_id: str):
    """
    Phase 2: Runs candidate matching against open roles
    only when explicitly triggered.
    """
    project = None
    if has_mongo and projects_col is not None:
        try:
            project = projects_col.find_one({"_id": ObjectId(project_id)})
        except Exception:
            pass
    if not project and project_id in memory_projects:
        project = memory_projects[project_id]

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    roles = project.get("roles", [])
    tech_signals = project.get("tech_signals", [])
    matched_roles = match_candidates_to_roles(roles, tech_signals)
    project["roles"] = matched_roles

    if has_mongo and projects_col is not None:
        try:
            projects_col.update_one({"_id": ObjectId(project_id)}, {"$set": {"roles": matched_roles}})
        except Exception:
            pass

    return {
        "status": "matched",
        "project_id": project_id,
        "roles": matched_roles
    }


@app.get("/api/projects")
def list_projects():
    if has_mongo and projects_col is not None:
        try:
            docs = list(projects_col.find().sort("created_at", -1))
            return [serialize(d) for d in docs]
        except Exception:
            pass
    return sorted(list(memory_projects.values()), key=lambda x: x.get("created_at", ""), reverse=True)


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    if has_mongo and projects_col is not None:
        try:
            oid = ObjectId(project_id)
            doc = projects_col.find_one({"_id": oid})
            if doc:
                return serialize(doc)
        except Exception:
            pass
    if project_id in memory_projects:
        return memory_projects[project_id]
    raise HTTPException(status_code=404, detail="Project not found")


@app.put("/api/projects/{project_id}")
def update_project(project_id: str, payload: dict = Body(...)):
    """
    Allows managers to adjust or modify a past project:
    - Update project_name, domain, team_size
    - Update, add, or remove roles
    - Update role tasks and deliverables
    """
    proj = None
    if has_mongo and projects_col is not None:
        try:
            proj = projects_col.find_one({"_id": ObjectId(project_id)})
        except Exception:
            pass
        if not proj:
            try:
                proj = projects_col.find_one({"id": project_id})
            except Exception:
                pass
    if not proj and project_id in memory_projects:
        proj = memory_projects[project_id]

    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Apply adjustments
    if "project_name" in payload:
        proj["project_name"] = payload["project_name"]
    if "domain" in payload:
        proj["domain"] = payload["domain"]
    if "team_size" in payload:
        proj["team_size"] = int(payload["team_size"])
    if "roles" in payload:
        updated_roles = []
        for r in payload["roles"]:
            style = style_for_role(r.get("role", "Role"))
            r["icon"] = r.get("icon") or style["icon"]
            r["color"] = r.get("color") or style["color"]
            updated_roles.append(r)
        proj["roles"] = updated_roles
        proj["total_roles"] = len(updated_roles)
    if "tech_signals" in payload:
        proj["tech_signals"] = payload["tech_signals"]
    if "domain_skills" in payload:
        proj["domain_skills"] = payload["domain_skills"]
    proj["updated_at"] = datetime.now(timezone.utc).isoformat()

    if has_mongo and projects_col is not None:
        try:
            projects_col.update_one({"id": project_id}, {"$set": proj}, upsert=True)
        except Exception as e:
            print(f"[WARN] Failed to write updated project to MongoDB: {e}")
    memory_projects[project_id] = proj
    return {"status": "success", "project": serialize(proj)}


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    """Allows managers to delete a project from history."""
    if has_mongo and projects_col is not None:
        try:
            projects_col.delete_one({"_id": ObjectId(project_id)})
        except Exception:
            pass
        try:
            projects_col.delete_one({"id": project_id})
        except Exception:
            pass
    memory_projects.pop(project_id, None)
    return {"status": "success", "message": f"Project {project_id} deleted"}


@app.post("/api/projects/{project_id}/assign-candidate")
def assign_candidate_to_project_role(project_id: str, payload: dict = Body(...)):
    """Assigns an applicant to an open role on the project (from manager action or Slack approval)."""
    candidate_id = payload.get("candidate_id")
    role_name = payload.get("role") or payload.get("role_name")

    # Fetch candidate
    cand = None
    for c in get_all_candidates():
        if c.get("candidate_id") == candidate_id:
            cand = c
            break

    proj = None
    if has_mongo and projects_col is not None:
        try:
            proj = projects_col.find_one({"_id": ObjectId(project_id)})
        except Exception:
            pass
        if not proj:
            try:
                proj = projects_col.find_one({"id": project_id})
            except Exception:
                pass
    if not proj and project_id in memory_projects:
        proj = memory_projects[project_id]

    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update role
    assigned = False
    for r in proj.get("roles", []):
        if r.get("role") == role_name:
            r["assigned_candidate"] = {
                "candidate_id": cand.get("candidate_id", candidate_id) if cand else candidate_id,
                "name": cand.get("name", payload.get("candidate_name", "Assigned Applicant")) if cand else payload.get("candidate_name", "Assigned Applicant"),
                "email": cand.get("email", "") if cand else "",
                "archetype": cand.get("archetype", "Specialist") if cand else "Specialist",
                "avatar_badge": cand.get("avatar_badge", "Verified") if cand else "Verified",
                "overall_rating": cand.get("overall_rating", 92) if cand else 92,
                "stats": cand.get("stats", {}) if cand else {},
                "match_rationale": payload.get("rationale") or f"Approved assignment to {role_name}."
            }
            assigned = True
            break

    if not assigned and proj.get("roles"):
        # Fallback to first open role
        for r in proj.get("roles"):
            if not r.get("assigned_candidate"):
                r["assigned_candidate"] = {
                    "candidate_id": candidate_id,
                    "name": cand.get("name", "Assigned Applicant") if cand else "Assigned Applicant",
                    "overall_rating": 90
                }
                break

    if has_mongo and projects_col is not None:
        try:
            projects_col.update_one({"id": project_id}, {"$set": {"roles": proj["roles"]}}, upsert=True)
        except Exception:
            pass
    memory_projects[project_id] = proj

    # Add notification for manager
    add_notification({
        "type": "assignment_approved",
        "title": f"Assignment Confirmed: {role_name}",
        "message": f"Applicant {cand.get('name') if cand else candidate_id} successfully assigned to {role_name} on '{proj.get('project_name')}'.",
        "project_id": project_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": False
    })

    return {"status": "success", "project": serialize(proj)}


# ── Manager Authentication Endpoints ──────────────────────────────────────────

@app.post("/api/auth/login")
def manager_login(credentials: dict = Body(...)):
    """Authenticates manager credentials and returns a secure session token."""
    email = (credentials.get("email") or "").strip().lower()
    password = credentials.get("password") or ""
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    user = None
    if has_mongo and users_col is not None:
        try:
            user = users_col.find_one({"email": email})
        except Exception:
            pass
    if not user:
        user = memory_users.get(email)

    if not user or not verify_password(password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = secrets.token_hex(24)
    session_data = {
        "token": token,
        "user_id": user.get("id") or str(user.get("_id", "")),
        "email": user["email"],
        "name": user.get("name", "Sarah Chen"),
        "role": user.get("role", "manager"),
        "department": user.get("department", "Engineering Operations"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    active_sessions[token] = session_data
    return {
        "status": "success",
        "token": token,
        "user": {
            "id": session_data["user_id"],
            "email": session_data["email"],
            "name": session_data["name"],
            "role": session_data["role"],
            "department": session_data["department"]
        }
    }


@app.post("/api/auth/register")
def manager_register(data: dict = Body(...)):
    """Registers a new manager account."""
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip() or "Project Lead"
    dept = (data.get("department") or "").strip() or "Delivery & Talent Operations"

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    if email in memory_users:
        raise HTTPException(status_code=400, detail="A manager account with this email already exists")

    new_user = {
        "id": f"mgr_{uuid.uuid4().hex[:8]}",
        "email": email,
        "name": name,
        "role": "manager",
        "department": dept,
        "password_hash": hash_password(password),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    memory_users[email] = new_user.copy()
    if has_mongo and users_col is not None:
        try:
            users_col.insert_one(new_user.copy())
        except Exception:
            pass

    token = secrets.token_hex(24)
    active_sessions[token] = {
        "token": token,
        "user_id": new_user["id"],
        "email": new_user["email"],
        "name": new_user["name"],
        "role": new_user["role"],
        "department": new_user["department"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    return {
        "status": "success",
        "token": token,
        "user": {
            "id": new_user["id"],
            "email": new_user["email"],
            "name": new_user["name"],
            "role": new_user["role"],
            "department": new_user["department"]
        }
    }


@app.get("/api/auth/me")
def get_current_manager(request: Request):
    """Validates the Authorization Bearer token."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()
    if not token or token not in active_sessions:
        raise HTTPException(status_code=401, detail="Valid manager session required")
    sess = active_sessions[token]
    return {
        "status": "success",
        "user": {
            "id": sess["user_id"],
            "email": sess["email"],
            "name": sess["name"],
            "role": sess["role"],
            "department": sess.get("department", "Operations")
        }
    }


# ── Notifications Endpoints ───────────────────────────────────────────────────

@app.get("/api/notifications")
def list_notifications():
    """Returns real-time notifications for the manager."""
    if has_mongo and notifications_col is not None:
        try:
            docs = list(notifications_col.find().sort("created_at", -1).limit(20))
            if docs:
                return [serialize(d) for d in docs]
        except Exception:
            pass
    return memory_notifications[:20]


@app.post("/api/notifications/clear")
def clear_all_notifications():
    global memory_notifications
    memory_notifications = []
    if has_mongo and notifications_col is not None:
        try:
            notifications_col.delete_many({})
        except Exception:
            pass
    return {"status": "success", "message": "Notifications cleared"}


@app.post("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str):
    for n in memory_notifications:
        if n.get("id") == notification_id:
            n["read"] = True
            break
    if has_mongo and notifications_col is not None:
        try:
            notifications_col.update_one({"id": notification_id}, {"$set": {"read": True}})
        except Exception:
            pass
    return {"status": "success"}


# ── Candidate Player Card Endpoints ───────────────────────────────────────────

@app.get("/api/candidates")
def list_candidates():
    """Returns the candidate roster of Player Cards generated by Workato AI."""
    return get_all_candidates()


@app.post("/api/candidates")
def save_candidate_endpoint(card: dict = Body(...)):
    """Receives a generated Player Card from Workato AI or Blueprint and stores it."""
    saved = upsert_candidate(card)
    return {"status": "success", "message": f"Player Card for {saved.get('name')} registered.", "candidate": saved}


@app.post("/api/candidates/seed")
def seed_candidates_endpoint():
    """Resets the candidate pool with realistic benchmark engineering cards."""
    for sc in SEED_CANDIDATES:
        upsert_candidate(sc.copy())
    return {"status": "success", "count": len(SEED_CANDIDATES), "candidates": get_all_candidates()}


@app.delete("/api/candidates")
def clear_all_candidates():
    """Removes all candidates from the roster."""
    memory_candidates.clear()
    if has_mongo and candidates_col is not None:
        try:
            candidates_col.delete_many({})
        except Exception as e:
            print(f"[WARN] Failed to clear candidates from MongoDB: {e}")
    return {"status": "success", "message": "All candidates cleared from roster."}


@app.delete("/api/candidates/{candidate_id}")
def delete_candidate_endpoint(candidate_id: str):
    """Removes a specific candidate from the roster by candidate_id."""
    removed = False
    if candidate_id in memory_candidates:
        del memory_candidates[candidate_id]
        removed = True
    if has_mongo and candidates_col is not None:
        try:
            result = candidates_col.delete_one({"candidate_id": candidate_id})
            if result.deleted_count > 0:
                removed = True
        except Exception as e:
            print(f"[WARN] Failed to delete candidate from MongoDB: {e}")
    if not removed:
        raise HTTPException(status_code=404, detail=f"Candidate '{candidate_id}' not found in roster.")
    return {"status": "success", "message": f"Candidate {candidate_id} removed from roster."}


# ── Workato -> Jira Provisioning Endpoint ─────────────────────────────────────

@app.post("/api/projects/{project_id}/sync-jira")
def sync_project_to_jira(project_id: str):
    """
    Executes Step 4 of the End-to-End Workflow:
    Takes the matched project and candidates, builds the Jira Project Board,
    attaches candidate player card stats to their issues, and auto-populates Sprint 1.
    """
    # Fetch project
    project = None
    if has_mongo and projects_col is not None:
        try:
            project = projects_col.find_one({"_id": ObjectId(project_id)})
        except Exception:
            pass
    if not project and project_id in memory_projects:
        project = memory_projects[project_id]

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_name = project.get("project_name", "Enterprise Project")
    project_key = re.sub(r"[^A-Z]", "", project_name.upper())[:4] or "PONG"
    roles = project.get("roles", [])

    # Build Jira Sprint Backlog Payload with Player Card Stats
    created_issues = []
    total_story_points = 0
    issue_counter = 1

    for r_idx, role_data in enumerate(roles):
        r_name = role_data.get("role", "Developer")
        cand = role_data.get("assigned_candidate") or {}
        has_cand = bool(cand.get("name"))
        c_name = cand.get("name") if has_cand else None
        c_stats = cand.get("stats", {})

        for t_idx, task in enumerate(role_data.get("tasks", [])):
            issue_key = f"{project_key}-{issue_counter}"
            issue_counter += 1
            pts = 3 if t_idx % 2 == 0 else 5
            total_story_points += pts

            if has_cand:
                description = (
                    f"h3. Assigned Developer: {cand.get('name')} ({cand.get('archetype', 'Engineer')})\n"
                    f"*Overall Rating (OVR):* {cand.get('overall_rating', 90)} | *Match Score:* {cand.get('match_score', 95)}%\n"
                    f"*Manager Match Rationale:* {cand.get('match_rationale', 'Selected based on skill alignment.')}\n\n"
                    f"|| Verified Player Stat || Rating ||\n"
                    f"| API Architecture | {c_stats.get('api_architecture', 85)} / 100 |\n"
                    f"| Backend Engineering | {c_stats.get('backend', 85)} / 100 |\n"
                    f"| System Design | {c_stats.get('system_design', 80)} / 100 |\n"
                    f"| Frontend UI/UX | {c_stats.get('frontend', 70)} / 100 |\n"
                    f"| DevOps & Cloud | {c_stats.get('devops_cloud', 75)} / 100 |\n"
                    f"| Pitch & Communication | {c_stats.get('communication', 85)} / 100 |\n\n"
                    f"h4. Task Objective & Deliverable:\n{task}"
                )
                status = "In Sprint 1"
                labels = ["pongai-matched", "player-card-aligned", cand.get("candidate_id", "cand")]
            else:
                description = (
                    f"h3. Open Sprint Backlog Task\n"
                    f"*Required Role:* {r_name}\n"
                    f"*Project:* {project_name}\n"
                    f"*Assignment Status:* Unassigned (Awaiting Candidate Applications)\n\n"
                    f"h4. Task Objective & Deliverable:\n{task}\n\n"
                    f"_Note: Upon candidate pitch evaluation and manager approval in Slack, this ticket will be automatically assigned with the verified Player Card stats._"
                )
                status = "Backlog (Unassigned)"
                labels = ["open-role", "unassigned", "pongai-scoped"]

            created_issues.append({
                "key": issue_key,
                "role": r_name,
                "summary": f"[{r_name}] {task}",
                "assignee": c_name,
                "candidate_id": cand.get("candidate_id") if has_cand else None,
                "story_points": pts,
                "status": status,
                "description": description,
                "labels": labels
            })

    jira_response = {
        "status": "provisioned",
        "jira_project": {
            "key": project_key,
            "name": project_name,
            "type": "Scrum Software Project",
            "board_name": f"{project_name} Agile Board",
            "board_url": f"https://your-company.atlassian.net/jira/software/projects/{project_key}/boards/1"
        },
        "sprint": {
            "sprint_id": 101,
            "name": "Sprint 1 - Foundation & Core Architecture",
            "goal": "Deliver core API contracts and architecture aligned to candidate strengths",
            "total_story_points": total_story_points,
            "issues_count": len(created_issues)
        },
        "issues": created_issues,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Optionally trigger external Workato Webhook if URL is configured
    workato_url = get_env("WORKATO_JIRA_WEBHOOK_URL") or get_env("WORKATO_SCOPING_WEBHOOK_URL")
    if workato_url and requests is not None:
        try:
            res = requests.post(workato_url, json={"event": "pongai_project_matched", "payload": jira_response}, timeout=8)
            print(f"[INFO] Forwarded to Workato Webhook: status {res.status_code}")
        except Exception as e:
            print(f"[WARN] Could not forward to Workato Webhook: {e}")

    # Mark project as synced
    if project:
        project["jira_synced"] = True
        project["jira_summary"] = {
            "project_key": project_key,
            "board_name": f"{project_name} Agile Board",
            "issues_count": len(created_issues),
            "story_points": total_story_points
        }

    return jira_response


# ── Phase 1: Automated Backlog Staging (Unassigned) ───────────────────────────

@app.post("/api/projects/{project_id}/stage-backlog")
def stage_project_backlog(project_id: str):
    """
    Phase 1: Instantiates Jira project workspace and stages unassigned tasks in backlog.
    Dispatches to Workato Recipe Phase 1 webhook.
    """
    project = None
    if has_mongo and projects_col is not None:
        try:
            project = projects_col.find_one({"_id": ObjectId(project_id)})
        except Exception:
            pass
    if not project and project_id in memory_projects:
        project = memory_projects[project_id]

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_name = project.get("project_name", "Enterprise Project")
    project_key = re.sub(r"[^A-Z]", "", project_name.upper())[:4] or "PONG"
    roles = project.get("roles", [])

    unassigned_issues = []
    counter = 1
    for role_item in roles:
        r_name = role_item.get("role", "Developer")
        for task in role_item.get("tasks", []):
            unassigned_issues.append({
                "key": f"{project_key}-{counter}",
                "summary": f"[{r_name}] {task}",
                "role": r_name,
                "status": "Backlog (Unassigned)",
                "assignee": None,
                "labels": ["open-role", "phase1-staged", "unassigned"]
            })
            counter += 1

    payload = {
        "event": "pongai_project_scoped",
        "project_id": project_id,
        "project_name": project_name,
        "tech_signals": project.get("tech_signals", []),
        "team_size": project.get("team_size", len(roles)),
        "roles": roles,
        "unassigned_backlog": unassigned_issues,
        "staged_count": len(unassigned_issues)
    }

    # Dispatch to Workato Phase 1 webhook if configured
    workato_url = get_env("WORKATO_SCOPING_WEBHOOK_URL") or get_env("WORKATO_JIRA_WEBHOOK_URL")
    if workato_url and requests is not None:
        try:
            res = requests.post(workato_url, json=payload, timeout=8)
            print(f"[INFO] Dispatched scoping payload to Workato Webhook: status {res.status_code}")
        except Exception as e:
            print(f"[WARN] Workato scoping webhook failed: {e}")

    project["backlog_staged"] = True
    return {
        "status": "staged",
        "project_key": project_key,
        "total_tasks_staged": len(unassigned_issues),
        "issues": unassigned_issues
    }


# ── Phase 2: Interactive Slack Approval Dispatch ─────────────────────────────

@app.post("/api/projects/{project_id}/request-approval")
def request_manager_approval(project_id: str, candidate_id: Optional[str] = None):
    """
    Phase 2: Prepares AI role recommendation and interactive Slack card with
    [Approve Assignment] and [Deny] buttons for the Project Manager.
    """
    project = None
    if has_mongo and projects_col is not None:
        try:
            project = projects_col.find_one({"_id": ObjectId(project_id)})
        except Exception:
            pass
    if not project and project_id in memory_projects:
        project = memory_projects[project_id]

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    candidates = get_all_candidates()
    cand = next((c for c in candidates if c.get("candidate_id") == candidate_id), None)
    if not cand and candidates:
        cand = candidates[0]

    # Matched role dynamically based on candidate profile, target_role, or highest verified stats
    roles = project.get("roles", [])
    cand_target = (cand.get("target_role") or "").lower() if cand else ""
    matched_role = None

    if cand_target and roles:
        matched_role = next((r for r in roles if cand_target in r.get("role", "").lower() or r.get("role", "").lower() in cand_target), None)

    if not matched_role and cand and roles:
        cand_stats = cand.get("stats", {})
        if cand_stats:
            top_stat = max(cand_stats, key=lambda k: cand_stats.get(k, 0))
            for r in roles:
                r_title = r.get("role", "").lower()
                if "front" in top_stat and ("front" in r_title or "ui" in r_title):
                    matched_role = r
                    break
                elif ("devops" in top_stat or "cloud" in top_stat) and ("devops" in r_title or "cloud" in r_title or "infra" in r_title):
                    matched_role = r
                    break
                elif ("backend" in top_stat or "api" in top_stat) and ("backend" in r_title or "api" in r_title):
                    matched_role = r
                    break
                elif "system" in top_stat and ("architect" in r_title or "lead" in r_title):
                    matched_role = r
                    break

    if not matched_role:
        matched_role = roles[0] if roles else {"role": cand.get("target_role", "Software Engineer") if cand else "Software Engineer"}

    role_name = matched_role.get("role", "Software Engineer")

    slack_interactive_payload = {
        "event": "candidate_pitch_applied",
        "project_id": project_id,
        "project_name": project.get("project_name", "Enterprise Project"),
        "candidate": cand or {"name": "Candidate", "target_role": "Developer"},
        "player_card": cand or {},
        "recommended_role": role_name,
        "interactive_buttons": [
            {"label": "Approve Assignment", "action_id": "approve_assignment", "style": "primary"},
            {"label": "Deny / Reassign", "action_id": "deny_assignment", "style": "danger"}
        ]
    }

    # Dispatch to Workato Phase 2 webhook if configured
    workato_url = get_env("WORKATO_APPROVAL_WEBHOOK_URL") or get_env("WORKATO_SCOPING_WEBHOOK_URL")
    if workato_url and requests is not None:
        try:
            res = requests.post(workato_url, json=slack_interactive_payload, timeout=8)
            print(f"[INFO] Dispatched approval payload to Workato Webhook: status {res.status_code}")
        except Exception as e:
            print(f"[WARN] Workato approval webhook failed: {e}")

    c_name = cand.get("name", "Candidate") if cand else "Candidate"
    return {
        "status": "approval_requested",
        "candidate_name": c_name,
        "recommended_role": role_name,
        "slack_message_preview": f"Interactive card sent to Slack with [Approve] and [Deny] buttons for {c_name} -> {role_name}."
    }



# ── Blueprint Intake & Workato Dispatch Endpoints ────────────────────────────

sys.path.append("/home/raymv/workato/Blueprint-and-Beacon-FINALS")
try:
    import workato_service
except ImportError:
    workato_service = None

def transcribe_audio_with_gemini(audio_bytes: bytes, mime_type: str = "audio/webm") -> tuple:
    """
    Transcribes audio accurately and verbatim using Gemini native multimodal audio capabilities.
    Supports audio/webm, audio/wav, audio/mp3, audio/ogg, audio/mp4.
    Returns (transcript_string, debug_message).
    """
    global client
    if client is None:
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""
        if genai is not None and api_key:
            try:
                client = genai.Client(api_key=api_key)
            except Exception as e:
                return "", f"Failed to initialize Gemini client: {e}"
        else:
            return "", f"Gemini client not initialized (genai_present={genai is not None}, has_api_key={bool(api_key)})"

    if not audio_bytes or len(audio_bytes) < 100:
        return "", "Audio sample was too short or empty."

    clean_mime = mime_type.split(";")[0].strip() if mime_type else "audio/webm"
    if clean_mime not in ["audio/webm", "audio/wav", "audio/mp3", "audio/ogg", "audio/aac", "audio/m4a", "audio/mp4", "audio/mpeg"]:
        clean_mime = "audio/webm"

    err_list = []
    try:
        from google.genai import types
        part = types.Part.from_bytes(data=audio_bytes, mime_type=clean_mime)
        prompt = (
            "You are an exact speech-to-text audio transcriber.\n"
            "Listen carefully to the audio file and transcribe the candidate's spoken words word-for-word.\n"
            "Strict rules:\n"
            "- Transcribe spoken words faithfully, preserving technical terms, frameworks, and metrics.\n"
            "- If the speech has slight background noise or lower volume, do your best to capture what the speaker is saying.\n"
            "- Output ONLY the plain transcription text with natural punctuation.\n"
            "- Do NOT add any introductory text, markdown quotes, or conversational notes.\n"
            "- Only if there is zero human speech (pure silence, static, or hum), output strictly: [NO_SPEECH]"
        )
        for model_name in [
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-3.6-flash",
            "gemini-2.5-flash",
            "gemini-flash-latest"
        ]:
            try:
                res = client.models.generate_content(
                    model=model_name,
                    contents=[part, prompt],
                    config=types.GenerateContentConfig(
                        temperature=0.0
                    )
                )
                transcript = (res.text or "").strip()
                if transcript and "[no_speech]" not in transcript.lower() and transcript.lower() not in ("[silence]", "no speech detected.", "silence", "no audio detected."):
                    return transcript, f"Transcribed via {model_name}"
                elif "[no_speech]" in transcript.lower():
                    return "", "Model detected silence / no speech"
            except Exception as e:
                err_list.append(f"{model_name}: {e}")
                print(f"[WARN] Gemini audio transcription on {model_name} failed: {e}")
    except Exception as e:
        err_list.append(f"Audio prep error: {e}")
        print(f"[WARN] Failed to prepare audio for Gemini: {e}")

    return "", "; ".join(err_list) if err_list else "No transcript produced"


@app.post("/api/blueprint/transcribe")
async def transcribe_pitch_audio(request: Request):
    """
    Receives an audio blob recorded from the candidate's pitch and
    uses Gemini to accurately transcribe their spoken words word-for-word.
    """
    content_type = request.headers.get("content-type", "")
    audio_bytes = b""
    mime_type = "audio/webm"

    if "multipart/form-data" in content_type:
        form = await request.form()
        audio_file = form.get("audio") or form.get("file")
        if audio_file and hasattr(audio_file, "read"):
            audio_bytes = await audio_file.read()
            mime_type = getattr(audio_file, "content_type", "audio/webm") or "audio/webm"
    else:
        audio_bytes = await request.body()
        mime_type = content_type or "audio/webm"

    if not audio_bytes or len(audio_bytes) < 100:
        return {
            "status": "empty",
            "transcript": "",
            "message": "Audio stream was too brief or empty."
        }

    transcript, detail = transcribe_audio_with_gemini(audio_bytes, mime_type)
    word_count = len(transcript.split()) if transcript else 0

    status = "success" if transcript else ("no_speech" if "no speech" in detail.lower() else "api_error")

    return {
        "status": status,
        "transcript": transcript,
        "word_count": word_count,
        "byte_count": len(audio_bytes),
        "mime_type": mime_type,
        "detail": detail
    }


def extract_candidate_from_resume(resume_text: str, pitch_transcript: str = "") -> dict:
    """
    Dynamically extracts candidate name, email, target role, and domain skills
    from the submitted resume text using Gemini, with intelligent regex fallback.
    No hardcoded candidate names or roles!
    """
    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", resume_text)
    detected_email = email_match.group(0) if email_match else ""
    
    lines = [l.strip() for l in resume_text.split("\n") if l.strip() and not l.strip().startswith("#")]
    
    # Smarter fallback name: avoid "Intern Resume", "Resume", "CV", "PAGE", "PAGE 1"
    fallback_name = "Candidate Applicant"
    bad_name_words = ["resume", "resumé", "curriculum", "vitae", "profile", "intern", "applicant", "contact", "page", "p a g e", "education", "skills", "experience", "summary", "phone", "email"]
    for line in lines[:8]:
        # Strip leading label like "Name: ", "Full Name: "
        stripped_line = re.sub(r"^(?:name|full name|candidate name|applicant name|candidate|applicant)\s*[:\-]?\s*", "", line, flags=re.IGNORECASE).strip()
        clean_l = re.sub(r"[^a-zA-Z\s]", "", stripped_line).strip()
        lower_l = clean_l.lower()
        compressed = lower_l.replace(" ", "")
        if any(bad in lower_l for bad in bad_name_words) or compressed in ["page", "pageone", "pagetwo", "internresume", "myresume", "name"]:
            continue
        # Also check for single-letter spaced words like "P A G E"
        words = clean_l.split()
        if all(len(w) == 1 for w in words):
            continue
        if 2 <= len(words) <= 4 and len(clean_l) < 40:
            fallback_name = clean_l.title()
            break
    if fallback_name == "Candidate Applicant" and detected_email:
        prefix = detected_email.split("@")[0].replace(".", " ").replace("_", " ").replace("-", " ")
        if not re.search(r"\d", prefix):
            fallback_name = prefix.title()

    # Dynamic skill extraction: Check for explicit "Skills:" or "Technical Skills:" section
    invalid_skill_words = {
        "june", "july", "august", "september", "october", "november", "december",
        "january", "february", "march", "april", "may", "present", "current",
        "work", "related", "courses", "course", "experience", "education",
        "summary", "project", "projects", "page", "university", "college",
        "school", "high school", "date", "dates", "duration", "year", "years",
        "month", "months", "from", "to", "gpa", "degree", "bachelor", "master"
    }
    extracted_section_skills = []
    skills_match = re.search(r"(?:skills|technical skills|core competencies|technologies|tools)[\s:]+([^\n]+(?:\n[^\n]+){0,3})", resume_text, re.IGNORECASE)
    if skills_match:
        raw_skills_block = skills_match.group(1)
        # Split by comma, bullet, pipe, or semicolon
        items = re.split(r"[,•|\n;•\-]+", raw_skills_block)
        for item in items:
            cleaned = item.strip()
            # Must not contain digits (dates/years like 2023) or date/education stopwords
            if (2 <= len(cleaned) <= 30 and 
                not re.search(r"\d", cleaned) and 
                not any(w in cleaned.lower().split() for w in invalid_skill_words)):
                extracted_section_skills.append(cleaned.title())

    # Comprehensive domain skill keyword scanning fallback (60+ skills across all domains)
    known_skills = [
        "FastAPI", "Python", "REST API", "Microservices", "Docker", "Kubernetes", "PostgreSQL",
        "AWS", "Cloud Architecture", "CI/CD", "Redis", "Kafka", "React", "TypeScript", "JavaScript",
        "Node.js", "HTML", "CSS", "SQL", "MongoDB", "Git", "GitHub", "Linux", "Playwright",
        "Cypress", "Selenium", "Test Automation", "Performance Testing", "QA Compliance", "End-to-End Testing",
        "API Testing", "Unit Testing", "Integration Testing", "Defect Tracking", "Jira", "Agile", "Scrum",
        "Event Management", "Venue Operations", "Logistics", "Budget Management", "Vendor Coordination",
        "Guest Experience", "Hospitality", "Stage Production", "Conference Planning", "Audio Visual",
        "Digital Marketing", "SEO", "Content Strategy", "Brand Strategy", "Google Analytics",
        "Financial Modeling", "Accounting", "Variance Analysis", "Auditing", "Risk Management"
    ]
    detected_skills = [sk for sk in known_skills if re.search(r"\b" + re.escape(sk) + r"\b", resume_text, re.IGNORECASE)]
    
    # Merge detected skills with section skills (preserve uniqueness and valid skills)
    combined_skills = []
    for s in (extracted_section_skills + detected_skills):
        s_clean = s.strip()
        if (s_clean and 
            s_clean not in combined_skills and 
            not re.search(r"\d", s_clean) and 
            not any(w in s_clean.lower().split() for w in invalid_skill_words)):
            combined_skills.append(s_clean)

    if not combined_skills:
        combined_skills = ["Software Engineering", "Systems Architecture", "Technical Execution"]

    detected_role = "Professional Candidate"
    r_lower = resume_text.lower()
    if any(k in r_lower for k in ["event", "venue", "hospitality", "logistics"]):
        detected_role = "Event Operations & Logistics Specialist"
    elif any(k in r_lower for k in ["qa", "test", "cypress", "selenium", "compliance", "playwright"]):
        detected_role = "QA & Systems Test Engineer"
    elif any(k in r_lower for k in ["api", "backend", "fastapi", "microservice", "distributed"]):
        detected_role = "Lead API & Backend Architect"

    candidate_data = {
        "name": fallback_name,
        "email": detected_email,
        "target_role": detected_role,
        "skills": combined_skills,
        "experience_level": "Senior"
    }

    if client is not None:
        prompt = f"""Extract the candidate contact details, target professional role, and core skills from this resume and elevator pitch across any domain (Event, QA/Testing, IT, Marketing, Operations, etc.).
Output ONLY a valid JSON object matching this schema:
{{
  "name": "Actual person full name (e.g. Alex Martinez, NOT 'PAGE', 'RESUME', or document headers)",
  "email": "Candidate Email Address",
  "target_role": "Target or current professional title across any field",
  "skills": ["Skill 1", "Skill 2", "Skill 3", "Skill 4", "Skill 5", "...extract ALL skills found in the resume"],
  "experience_level": "Senior / Mid-Level / Junior / Lead"
}}

RESUME:
{resume_text[:6000]}

PITCH:
{pitch_transcript[:2000]}
"""
        for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                gen_config = types.GenerateContentConfig(temperature=0.1) if types is not None else None
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=gen_config
                )
                raw = resp.text.strip()
                raw = re.sub(r"^```(?:json)?", "", raw).strip()
                raw = re.sub(r"```$", "", raw).strip()
                parsed = json.loads(raw)
                p_name = (parsed.get("name") or "").strip()
                p_name_lower = p_name.lower()
                p_compressed = p_name_lower.replace(" ", "")
                if p_name and not any(bad in p_name_lower for bad in bad_name_words) and p_compressed not in ["page", "pageone", "pagetwo"]:
                    candidate_data["name"] = p_name
                if parsed.get("email"):
                    candidate_data["email"] = parsed["email"].strip()
                if parsed.get("target_role"):
                    candidate_data["target_role"] = parsed["target_role"].strip()
                if parsed.get("skills") and isinstance(parsed["skills"], list) and len(parsed["skills"]) > 0:
                    candidate_data["skills"] = parsed["skills"]
                if parsed.get("experience_level"):
                    candidate_data["experience_level"] = parsed["experience_level"].strip()
                break
            except Exception as e:
                print(f"[WARN] Gemini resume extraction failed on {model_name}: {e}")

    return candidate_data


def match_candidate_across_projects(candidate: dict) -> dict:
    """
    Evaluates candidate fit across ALL active enterprise projects (Event, QA, IT, etc.)
    Returns the single best matching project & role along with top contenders.
    """
    all_projects = list_projects()
    if not all_projects:
        return {"best_match": None, "all_matches": []}

    cand_role = (candidate.get("target_role") or "").lower()
    cand_skills = [str(s).lower() for s in candidate.get("skills", [])]
    cand_text = (candidate.get("pitch_evaluation", {}).get("transcript") or candidate.get("spoken_text") or "").lower()
    cand_text += " " + cand_role + " " + " ".join(cand_skills)

    matches = []

    for proj in all_projects:
        proj_id = proj.get("id")
        proj_name = proj.get("project_name")
        domain = proj.get("domain", "General")

        for r in proj.get("roles", []):
            role_name = r.get("role", "")
            r_lower = role_name.lower()
            tasks = [str(t).lower() for t in r.get("tasks", [])]
            tasks_text = " ".join(tasks)

            # Base compatibility score
            score = 68.0

            # 1. Target role token overlap
            role_tokens = [w for w in re.split(r"\W+", r_lower) if len(w) > 2]
            token_matches = sum(1 for w in role_tokens if w in cand_text)
            if token_matches:
                score += min(18.0, token_matches * 6.0)

            # 2. Skill overlap
            for sk in cand_skills:
                if len(sk) > 2 and (sk in r_lower or sk in tasks_text):
                    score += 4.5

            # 3. Domain boost
            if any(k in cand_text for k in ["event", "hospitality", "venue", "conference", "guest"]) and "event" in domain.lower():
                score += 10.0
            elif any(k in cand_text for k in ["test", "qa", "cypress", "automation", "quality", "selenium"]) and ("qa" in domain.lower() or "test" in domain.lower()):
                score += 10.0
            elif any(k in cand_text for k in ["api", "backend", "cloud", "software", "developer", "engineer"]) and ("it" in domain.lower() or "cloud" in domain.lower()):
                score += 10.0
            elif any(k in cand_text for k in ["marketing", "campaign", "social", "brand", "growth"]) and "market" in domain.lower():
                score += 10.0

            # 4. Telemetry Confidence boost
            conf = candidate.get("stats", {}).get("confidence", 85)
            score += (conf - 70) * 0.1

            score = min(98.0, max(60.0, score))

            rationale = f"Candidate demonstrated {int(score)}% alignment with {role_name} deliverables in {domain} based on verified skills and delivery confidence."

            matches.append({
                "project_id": proj_id,
                "project_name": proj_name,
                "domain": domain,
                "role": role_name,
                "role_name": role_name,
                "score": round(score, 1),
                "match_score": round(score, 1),
                "rationale": rationale
            })

    matches.sort(key=lambda x: x["score"], reverse=True)
    best = matches[0] if matches else None
    return {"best_match": best, "all_matches": matches[:5]}


@app.post("/api/blueprint/pitch")
async def submit_blueprint_pitch(request: Request):
    """
    Submits an applicant pitch via Blueprint camera/voice & resume upload:
    1. Extracts text from the uploaded resume (PDF/DOCX/TXT).
    2. Uses Gemini to dynamically retrieve candidate name, email, target role, and skills from the resume.
    3. Synthesizes a standardized Developer Player Card.
    4. Registers the candidate into PongAI's live candidate roster.
    5. Dispatches the full dynamic payload to the Workato Blueprint webhook.
    """
    content_type = request.headers.get("content-type", "")
    resume_text = ""
    spoken_text = ""
    telem = {"focus_percentage": 88.0, "gesture_energy": 72.0, "gesture_profile": "composed_dynamic"}
    filename = "uploaded_resume.pdf"

    if "multipart/form-data" in content_type:
        form = await request.form()
        spoken_text = form.get("spoken_text") or form.get("pitch_text") or ""
        telem_raw = form.get("telemetry_metrics")
        if telem_raw:
            try:
                telem = json.loads(str(telem_raw))
            except Exception:
                pass
        
        # Check for uploaded resume file
        file_obj = form.get("file") or form.get("resume_file") or form.get("resume")
        if file_obj and hasattr(file_obj, "read"):
            raw_bytes = await file_obj.read()
            filename = getattr(file_obj, "filename", "uploaded_resume.pdf") or "uploaded_resume.pdf"
            extracted = extract_text(file_obj, raw_bytes)
            if extracted:
                resume_text = extracted
        
        # Check for fallback resume text input if no binary file was provided
        if not resume_text and form.get("resume_text"):
            resume_text = str(form.get("resume_text"))

        # If spoken_text is empty, check if an audio blob was submitted with the form
        audio_file = form.get("audio") or form.get("pitch_audio") or form.get("voice")
        if (not spoken_text or len(spoken_text.strip()) < 5) and audio_file and hasattr(audio_file, "read"):
            try:
                audio_bytes = await audio_file.read()
                mime = getattr(audio_file, "content_type", "audio/webm") or "audio/webm"
                detected = transcribe_audio_with_gemini(audio_bytes, mime)
                if detected:
                    spoken_text = detected
            except Exception as e:
                print(f"[WARN] In-pitch audio transcription notice: {e}")
    else:
        try:
            body = await request.json()
        except Exception:
            body = {}
        spoken_text = body.get("spoken_text") or body.get("pitch_text") or ""
        resume_text = body.get("resume_text") or ""
        if body.get("telemetry_metrics"):
            telem = body.get("telemetry_metrics")

    # Dynamically extract Name, Email, Target Role, and Skills from the resume using Gemini
    extracted_cand = extract_candidate_from_resume(resume_text, spoken_text)
    
    cid = f"cand_{uuid.uuid4().hex[:8]}"
    c_info = {
        "candidate_id": cid,
        "name": extracted_cand.get("name", "Applicant"),
        "email": extracted_cand.get("email", ""),
        "target_role": extracted_cand.get("target_role", "Software Engineer"),
        "skills": extracted_cand.get("skills", ["REST API", "Backend Engineering"]),
        "experience_level": extracted_cand.get("experience_level", "Senior")
    }

    if not spoken_text:
        spoken_text = f"Candidate pitch submitted for {c_info['target_role']}."

    if workato_service is not None:
        import importlib
        try:
            importlib.reload(workato_service)
        except Exception:
            pass
        payload = workato_service.build_candidate_payload(
            candidate_info=c_info,
            resume_text=resume_text,
            spoken_text=spoken_text,
            telemetry_metrics=telem,
            coaching_report=f"Candidate presented technical competency for {c_info['target_role']}.",
            resume_filename=filename
        )
        player_card = workato_service.generate_player_card(payload)
        payload["player_card"] = player_card
    else:
        eye_contact = float(telem.get("eye_contact_percentage") or telem.get("focus_percentage") or 88.0)
        confidence = int(telem.get("confidence_score") or min(98, max(60, int(eye_contact * 0.5 + 45))))
        archetype_src = telem.get("confidence_archetype") or "Composed Delivery"
        cadence = float(telem.get("vocal_cadence") or telem.get("vocal_energy") or 80.0)

        skills = c_info.get("skills", [])
        target_role = c_info.get("target_role", "").lower()
        skills_lower = [str(s).lower() for s in skills]
        combined = " ".join(skills_lower) + " " + target_role + " " + spoken_text.lower() + " " + resume_text.lower()

        # Communication/Soft skills (always relevant)
        communication = min(98, max(50, int(eye_contact * 0.4 + cadence * 0.6)))
        presence = min(98, max(50, int(eye_contact * 0.5 + confidence * 0.5)))

        # Domain detection
        is_it = any(k in combined for k in ["api", "backend", "fastapi", "python", "microservice", "database", "cloud", "devops", "software", "developer", "docker", "kubernetes"])
        is_event = any(k in combined for k in ["event", "venue", "logistics", "hospitality", "conference", "summit", "guest", "catering", "stage", "production", "planning"])
        is_qa = any(k in combined for k in ["qa", "test", "cypress", "selenium", "automation", "compliance", "quality", "bug", "regression", "performance testing"])
        is_marketing = any(k in combined for k in ["marketing", "campaign", "brand", "social media", "content", "seo", "growth", "advertising"])
        is_finance = any(k in combined for k in ["finance", "accounting", "budget", "audit", "revenue", "cost", "payroll", "tax"])
        is_operations = any(k in combined for k in ["operations", "supply chain", "procurement", "vendor", "facility", "process improvement"])

        if is_event and not is_it:
            # Event Management domain
            archetype = "Event Operations & Logistics Specialist"
            badge = "Event Director"
            stats = {
                "event_planning": min(98, max(65, 75 + sum(4 for k in ["event", "planning", "coordination"] if k in combined))),
                "logistics": min(98, max(65, 74 + sum(4 for k in ["logistics", "venue", "transport", "supply"] if k in combined))),
                "vendor_management": min(98, max(65, 72 + sum(4 for k in ["vendor", "supplier", "contract", "budget"] if k in combined))),
                "guest_experience": min(98, max(65, 70 + sum(4 for k in ["guest", "experience", "hospitality", "customer"] if k in combined))),
                "communication": communication,
                "confidence": confidence,
                "eye_contact": eye_contact
            }
        elif is_qa and not is_it:
            # QA & Testing domain
            archetype = "QA & Systems Test Engineer"
            badge = "Quality Specialist"
            stats = {
                "test_automation": min(98, max(65, 75 + sum(5 for k in ["cypress", "selenium", "playwright", "automation"] if k in combined))),
                "manual_testing": min(98, max(65, 72 + sum(4 for k in ["qa", "test", "manual", "regression"] if k in combined))),
                "compliance": min(98, max(65, 70 + sum(5 for k in ["compliance", "audit", "iso", "security"] if k in combined))),
                "bug_tracking": min(98, max(65, 68 + sum(4 for k in ["jira", "bug", "defect", "ticket"] if k in combined))),
                "communication": communication,
                "confidence": confidence,
                "eye_contact": eye_contact
            }
        elif is_marketing:
            archetype = "Marketing & Growth Specialist"
            badge = "Brand Strategist"
            stats = {
                "brand_strategy": min(98, max(65, 74 + sum(4 for k in ["brand", "strategy", "positioning", "identity"] if k in combined))),
                "content_creation": min(98, max(65, 72 + sum(4 for k in ["content", "copywriting", "creative", "social"] if k in combined))),
                "digital_marketing": min(98, max(65, 70 + sum(4 for k in ["seo", "sem", "ads", "digital", "campaign"] if k in combined))),
                "analytics": min(98, max(65, 68 + sum(4 for k in ["analytics", "kpi", "metrics", "data", "growth"] if k in combined))),
                "communication": communication,
                "confidence": confidence,
                "eye_contact": eye_contact
            }
        elif is_finance:
            archetype = "Finance & Accounting Professional"
            badge = "Financial Analyst"
            stats = {
                "financial_analysis": min(98, max(65, 74 + sum(4 for k in ["finance", "analysis", "model", "forecast"] if k in combined))),
                "accounting": min(98, max(65, 72 + sum(4 for k in ["accounting", "audit", "tax", "ledger", "payroll"] if k in combined))),
                "budgeting": min(98, max(65, 70 + sum(4 for k in ["budget", "cost", "revenue", "variance"] if k in combined))),
                "compliance": min(98, max(65, 68 + sum(4 for k in ["regulatory", "compliance", "sox", "gaap"] if k in combined))),
                "communication": communication,
                "confidence": confidence,
                "eye_contact": eye_contact
            }
        else:
            # IT / Software domain (default)
            archetype = "Software Systems Engineer"
            badge = "Polyglot Engineer"
            api_sc = min(98, max(55, 65 + sum(5 for k in ["api", "rest", "graphql", "grpc", "gateway", "openapi", "swagger", "fastapi"] if k in combined)))
            backend_sc = min(98, max(55, 65 + sum(4 for k in ["python", "backend", "database", "sql", "postgres", "redis", "mongodb", "microservice"] if k in combined)))
            frontend_sc = min(98, max(55, 60 + sum(6 for k in ["react", "vue", "angular", "html", "css", "tailwind", "frontend", "typescript"] if k in combined)))
            devops_sc = min(98, max(55, 60 + sum(6 for k in ["docker", "kubernetes", "ci/cd", "aws", "gcp", "azure", "terraform", "devops", "pipeline"] if k in combined)))
            sysdes_sc = min(98, max(55, 62 + sum(6 for k in ["distributed", "architecture", "scalable", "caching", "kafka", "design", "system"] if k in combined)))
            if api_sc >= 90 and backend_sc >= 85:
                archetype = "Lead API & Backend Architect"
                badge = "API Maestro"
            elif frontend_sc >= 88:
                archetype = "Frontend & Interface Specialist"
                badge = "UI Virtuoso"
            elif devops_sc >= 85:
                archetype = "Cloud & DevOps Engineer"
                badge = "Infra Specialist"
            stats = {
                "api_architecture": api_sc,
                "backend": backend_sc,
                "frontend": frontend_sc,
                "devops_cloud": devops_sc,
                "system_design": sysdes_sc,
                "communication": communication,
                "confidence": confidence,
                "eye_contact": eye_contact
            }

        # Compute OVR from primary stats (excluding confidence, eye_contact)
        primary_vals = [v for k, v in stats.items() if k not in ("confidence", "eye_contact")]
        ovr = round(sum(primary_vals) / len(primary_vals)) if primary_vals else 75

        # Build key strengths from actual skills
        key_strengths = []
        if confidence >= 80 and eye_contact >= 75:
            key_strengths.append(f"High-confidence delivery with {eye_contact}% eye contact focus")
        if skills:
            top_skills = skills[:3]
            key_strengths.append(f"Verified competency in: {', '.join(top_skills)}")
        if not key_strengths:
            key_strengths.append(f"Demonstrated presence and communication for {c_info['target_role']}")

        player_card = {
            "candidate_id": c_info["candidate_id"],
            "name": c_info["name"],
            "email": c_info["email"],
            "target_role": c_info["target_role"],
            "skills": skills,
            "archetype": archetype,
            "avatar_badge": badge,
            "overall_rating": ovr,
            "stats": stats,
            "key_strengths": key_strengths,
            "growth_areas": [],
            "telemetry_metrics": telem,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        payload = {
            "event": "candidate_pitch_submitted",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "candidate": c_info,
            "resume": {
                "filename": filename,
                "character_count": len(resume_text),
                "text_preview": resume_text[:1000],
                "has_resume": bool(resume_text)
            },
            "pitch_evaluation": {"transcript": spoken_text, "telemetry": telem},
            "player_card": player_card
        }

    # Cross-Project Fit Evaluation across all stored projects (IT, Event, Testing, etc.)
    match_result = match_candidate_across_projects(player_card)
    best_match = match_result.get("best_match")
    all_matches = match_result.get("all_matches", [])

    if best_match:
        player_card["matched_project_id"] = best_match["project_id"]
        player_card["matched_project_name"] = best_match["project_name"]
        player_card["matched_project_domain"] = best_match.get("domain", "General")
        player_card["matched_role"] = best_match["role"]
        player_card["match_score"] = best_match["score"]
        player_card["match_rationale"] = best_match["rationale"]
        player_card["status"] = "pending_manager_approval"

        # Push in-app manager notification
        add_notification({
            "type": "applicant_matched",
            "title": f"New Applicant Match: {player_card.get('name')}",
            "message": f"Candidate {player_card.get('name')} ({player_card.get('overall_rating')} OVR) scored {best_match['score']}% fit for {best_match['role']} on '{best_match['project_name']}' ({best_match.get('domain', 'General')}). Review card dispatched to Slack.",
            "candidate_id": player_card.get("candidate_id"),
            "project_id": best_match["project_id"],
            "project_name": best_match["project_name"],
            "role_name": best_match["role"],
            "match_score": best_match["score"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "read": False
        })

    # Prepare enriched cross-project payload for Workato Blueprint Webhook
    eye_val = telem.get("eye_contact_percentage") or telem.get("focus_percentage")
    try:
        eye_contact = round(float(eye_val), 1) if eye_val is not None and float(eye_val) > 0 else 88.0
    except (ValueError, TypeError):
        eye_contact = 88.0

    conf_val = telem.get("confidence_score")
    try:
        confidence = int(conf_val) if conf_val is not None and int(conf_val) > 0 else 90
    except (ValueError, TypeError):
        confidence = 90

    archetype = telem.get("confidence_archetype") or "Executive Composure"
    
    cadence_val = telem.get("vocal_cadence") or telem.get("vocal_energy")
    try:
        cadence = round(float(cadence_val), 1) if cadence_val is not None and float(cadence_val) > 0 else 84.0
    except (ValueError, TypeError):
        cadence = 84.0

    telemetry_obj = {
        "eye_contact_percentage": eye_contact,
        "confidence_score": confidence,
        "confidence_archetype": archetype,
        "vocal_cadence": cadence,
        "focus_percentage": eye_contact,
        "gesture_energy": cadence,
        "gesture_profile": telem.get("gesture_profile", "composed_dynamic")
    }

    if "candidate" not in payload:
        payload["candidate"] = dict(c_info)
    payload["candidate"]["telemetry"] = telemetry_obj
    payload["candidate"]["overall_rating"] = player_card.get("overall_rating", 88)
    if isinstance(payload["candidate"].get("skills"), list):
        payload["candidate"]["skills_text"] = ", ".join(payload["candidate"]["skills"])

    payload["telemetry"] = telemetry_obj
    payload["event"] = "candidate_pitch_applied"

    if best_match:
        best_match["role_name"] = best_match.get("role")
        best_match["match_score"] = best_match.get("score")
        payload["recommended_match"] = best_match
    else:
        payload["recommended_match"] = {}

    payload["all_project_matches"] = all_matches

    available_summary_lines = []
    for p in list_projects():
        p_name = p.get("project_name")
        p_domain = p.get("domain", "General")
        open_roles = [r.get("role") for r in p.get("roles", []) if not r.get("assigned_candidate")]
        roles_str = ", ".join(open_roles) if open_roles else "All roles filled"
        available_summary_lines.append(f"- {p_name} ({p_domain}) | Open Roles: {roles_str}")
    available_projects_summary = "\n".join(available_summary_lines)

    payload["available_projects_summary"] = available_projects_summary
    payload["all_projects_text"] = available_projects_summary
    payload["all_open_projects_text"] = available_projects_summary
    payload["available_projects"] = [
        {
            "project_id": p.get("id"),
            "project_name": p.get("project_name"),
            "domain": p.get("domain", "General"),
            "open_roles": [r.get("role") for r in p.get("roles", []) if not r.get("assigned_candidate")]
        }
        for p in list_projects()
    ]

    # Upsert into PongAI candidate roster
    upsert_candidate(player_card)

    # Dispatch to Workato webhook
    webhook_url = (
        get_env("WORKATO_BLUEPRINT_WEBHOOK_URL")
        or get_env("WORKATO_APPROVAL_WEBHOOK_URL")
        or get_env("WORKATO_WEBHOOK_URL")
        or "https://webhooks.trial.workato.com/webhooks/rest/3bab9a2f-bb30-454b-9639-3354ff497494/candidate---slack-manager-approval"
    )
    dispatch_status = "unconfigured"
    dispatch_msg = "No Workato Blueprint Webhook URL configured"
    status_code = None

    if webhook_url:
        try:
            if workato_service is not None:
                success, dispatch_msg, details = workato_service.send_to_workato(payload, webhook_url=webhook_url)
                dispatch_status = "delivered" if success else "failed"
                status_code = details.get("status_code")
            elif requests is not None:
                res = requests.post(webhook_url, json=payload, timeout=8)
                status_code = res.status_code
                dispatch_status = "delivered" if 200 <= res.status_code < 300 else "failed"
                dispatch_msg = f"Workato responded HTTP {res.status_code}"
        except Exception as e:
            dispatch_status = "error"
            dispatch_msg = str(e)

    return {
        "status": "success",
        "candidate": player_card,
        "recommended_match": best_match,
        "all_matches": all_matches,
        "extracted_from_resume": {
            "name": c_info["name"],
            "email": c_info["email"],
            "target_role": c_info["target_role"],
            "skills": c_info["skills"]
        },
        "workato_webhook_url": webhook_url,
        "workato_status": dispatch_status,
        "workato_message": dispatch_msg,
        "status_code": status_code
    }


@app.post("/api/blueprint/test-dispatch")
def test_dispatch_to_blueprint_webhook():
    """
    Fires an active candidate pitch directly to the Workato Blueprint webhook
    so Workato can capture the schema without requiring manual sample JSON pasting.
    """
    webhook_url = (
        get_env("WORKATO_BLUEPRINT_WEBHOOK_URL")
        or get_env("WORKATO_APPROVAL_WEBHOOK_URL")
        or get_env("WORKATO_WEBHOOK_URL")
        or "https://webhooks.trial.workato.com/webhooks/rest/3bab9a2f-bb30-454b-9639-3354ff497494/candidate---slack-manager-approval"
    )

    candidates = get_all_candidates()
    cand = candidates[0] if candidates else {
        "candidate_id": f"cand_{uuid.uuid4().hex[:8]}",
        "name": "Applicant",
        "target_role": "Software Engineer",
        "archetype": "Distributed Systems Engineer",
        "avatar_badge": "Systems Engineer",
        "overall_rating": 93,
        "stats": {"api_architecture": 95, "backend": 94, "system_design": 91, "frontend": 76, "devops_cloud": 85, "communication": 90}
    }

    payload = {
        "event": "candidate_pitch_submitted",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "candidate": {
            "id": cand.get("candidate_id"),
            "name": cand.get("name"),
            "email": cand.get("email", "candidate@enterprise.io"),
            "target_role": cand.get("target_role", "Lead API & Backend Architect"),
            "skills": ["FastAPI", "Python", "Microservices", "PostgreSQL", "Docker", "Kubernetes"],
            "skills_text": "FastAPI, Python, Microservices, PostgreSQL, Docker, Kubernetes",
            "experience_level": "Senior",
            "overall_rating": cand.get("overall_rating", 93),
            "telemetry": {
                "eye_contact_percentage": 92.5,
                "confidence_score": 94,
                "confidence_archetype": "Executive Composure",
                "vocal_cadence": 86.0
            }
        },
        "telemetry": {
            "eye_contact_percentage": 92.5,
            "confidence_score": 94,
            "confidence_archetype": "Executive Composure",
            "vocal_cadence": 86.0
        },
        "recommended_match": {
            "project_id": "proj_it_payment_gateway",
            "project_name": "High-Concurrency Payment Gateway & Service Mesh",
            "domain": "Enterprise IT & Cloud",
            "role": "Lead API & Backend Architect",
            "role_name": "Lead API & Backend Architect",
            "score": 94.0,
            "match_score": 94.0,
            "rationale": "Strong domain match in distributed backend systems and high-availability API architecture."
        },
        "available_projects_summary": "- High-Concurrency Payment Gateway & Service Mesh (Enterprise IT & Cloud) | Open Roles: Lead API & Backend Architect, Cloud Infrastructure Engineer\n- Global Tech Summit 2026 Experience Platform (Event Management) | Open Roles: Event Director & Operations Lead, Venue & Logistics Coordinator, Guest Experience Manager\n- Multi-Tenant Enterprise Compliance & QA Suite (QA & Systems Testing) | Open Roles: Lead Test Automation Architect, Compliance & Security Verification Specialist",
        "resume": {
            "filename": "applicant_resume.pdf",
            "character_count": 1200,
            "text_preview": f"Experienced engineer in {cand.get('target_role')}.",
            "has_resume": True
        },
        "pitch_evaluation": {
            "transcript": f"Hello, I am presenting my technical pitch for {cand.get('target_role')}. My key strength is building high-availability API architectures and resilient microservices.",
            "duration_seconds": 58,
            "telemetry": {
                "focus_percentage": 92.5,
                "gesture_energy": 78.0,
                "gesture_profile": "composed_dynamic",
                "eye_contact_percentage": 92.5,
                "confidence_score": 94,
                "confidence_archetype": "Executive Composure"
            },
            "executive_summary": "Strong technical articulation with high executive presence.",
            "full_report": "Candidate demonstrated deep domain mastery and concise technical communication."
        },
        "player_card": cand,
        "metadata": {
            "source": "Blueprint AI Coach",
            "version": "2.0-hackathon",
            "pipeline_target": "Workato -> PongAI -> Jira"
        }
    }

    try:
        res = requests.post(webhook_url, json=payload, timeout=8)
        return {
            "status": "success" if 200 <= res.status_code < 300 else "warning",
            "status_code": res.status_code,
            "workato_response": res.text[:250],
            "webhook_url": webhook_url,
            "dispatched_candidate": cand.get("name")
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "webhook_url": webhook_url
        }

# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "status": "Agentic Resource Allocation Engine — online",
        "storage": "MongoDB" if has_mongo else "Resilient In-Memory",
        "registered_candidates": len(get_all_candidates()),
        "endpoints": ["/api/analyze", "/api/candidates", "/api/projects", "/api/projects/{id}/sync-jira"]
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)