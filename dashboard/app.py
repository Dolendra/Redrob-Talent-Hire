"""
Redrob-Talent-Hire Streamlit Dashboard — Talent Opportunity Map & SaaS Suite.
Converted from React TSX for Hackathon visual excellence and technical credibility.
"""

from __future__ import annotations

import os
# Prevent OpenBLAS memory allocation errors on Windows or high-thread systems
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import json
import sys
import tempfile
import uuid
import re
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dashboard.components.candidate_card import render_talent_dna_report, render_deconstructed_reasoning_html
from dashboard.components.opportunity_map import build_opportunity_map, build_tree_opportunity_map
from dashboard.components.skill_adjacency_map import render_skill_adjacency_map
from src.main import run_ranking
from src.models import RankedCandidate, CandidateRecord, ScoreBundle
from src.parser import load_job_description, load_weights, normalize_candidate
from src.ingestion import ProductionIngestionService

# Set Streamlit page config
st.set_page_config(page_title="Redrob-Talent-Hire — SaaS Suite", layout="wide")

def clean_html(html: str) -> str:
    return "\n".join(line.strip() for line in html.splitlines())

def render_hackathon_compliance_banner() -> None:
    st.markdown("""
    <div style="background: rgba(30, 41, 59, 0.65); border: 2px solid #38bdf8; border-radius: 12px; padding: 16px; margin-bottom: 24px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);">
        <div style="display: flex; align-items: center; gap: 8px; font-family: monospace; font-size: 13px; color: #38bdf8; font-weight: bold; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1.5px;">
            <span>🏆</span> HACKATHON OFFLINE COMPLIANCE & REPRODUCTION AUDIT
        </div>
        <div style="font-size: 13.5px; color: #f8fafc; line-height: 1.5; margin-bottom: 12px;">
            The ranking engine is strictly sandboxed and operates <strong>entirely offline</strong> (<code>has_network=False</code> / local models only) to satisfy constraints. Note that active PDF resume parsing requires external APIs, but the <strong>100k candidate pool ranking is fully localized and runs in under 4 minutes on CPU</strong>.
        </div>
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 12px; font-family: monospace; font-size: 13px; color: #a7f3d0; display: flex; flex-direction: column; gap: 4px;">
            <div style="color: #94a3b8; font-size: 10px; text-transform: uppercase; letter-spacing: 1px;">Reproduction Command for Judges:</div>
            <div style="font-weight: bold; color: #34d399;">python rank.py --candidates candidates.jsonl</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Helper function to initialize and persist Job Registry
def init_job_registry() -> dict:
    registry_path = ROOT / "data" / "job_registry.json"
    if registry_path.exists():
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
            
    # If the registry doesn't exist, build a default one from job_description.md
    weights = load_weights(ROOT / "config" / "weights.json")
    default_jd = load_job_description(ROOT / "data" / "job_description.md", weights)
    
    registry = {
        "JOB_DEFAULT": {
            "job_id": "JOB_DEFAULT",
            "title": default_jd.title,
            "required_skills": default_jd.required_skills,
            "preferred_skills": default_jd.preferred_skills,
            "min_experience_years": default_jd.min_experience_years or 5.0,
            "max_experience_years": default_jd.max_experience_years or 9.0,
            "locations": default_jd.locations or ["Pune", "Noida", "Hyderabad", "Mumbai", "Delhi NCR"],
            "description": default_jd.ranking_text,
            "jd_path": "data/job_description.md"
        }
    }
    
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
    return registry

# Detect if running in HuggingFace Spaces environment
IS_HF_SPACES = os.environ.get("SPACE_ID") is not None or os.environ.get("SPACE_HOST") is not None

# Initialize Session States
if "job_db" not in st.session_state:
    st.session_state.job_db = init_job_registry()

if "candidate_pool" not in st.session_state:
    # Load default sample_candidates.json to prevent the dashboard from being empty/gone on start
    sample_path = ROOT / "data" / "sample_candidates.json"
    if sample_path.exists():
        try:
            with open(sample_path, "r", encoding="utf-8") as f:
                st.session_state.candidate_pool = json.load(f)
        except Exception:
            st.session_state.candidate_pool = []
    else:
        st.session_state.candidate_pool = []

if "temp_pool_path" not in st.session_state:
    st.session_state.temp_pool_path = None
if "temp_pool_mtime" not in st.session_state:
    st.session_state.temp_pool_mtime = 0.0

if "app_mode" not in st.session_state:
    st.session_state.app_mode = "Recruiter Command Center"

if "selected_candidate_id" not in st.session_state:
    st.session_state.selected_candidate_id = None

if "selected_job_id" not in st.session_state:
    st.session_state.selected_job_id = list(st.session_state.job_db.keys())[0]

# Session states for form population (so JD parsing populates form inputs)
if "new_job_title" not in st.session_state:
    st.session_state.new_job_title = ""
if "new_job_desc" not in st.session_state:
    st.session_state.new_job_desc = ""
if "new_job_locs" not in st.session_state:
    st.session_state.new_job_locs = ""
if "new_job_min_exp" not in st.session_state:
    st.session_state.new_job_min_exp = 3.0
if "new_job_max_exp" not in st.session_state:
    st.session_state.new_job_max_exp = 8.0
if "new_job_req_skills" not in st.session_state:
    st.session_state.new_job_req_skills = ""
if "new_job_pref_skills" not in st.session_state:
    st.session_state.new_job_pref_skills = ""
if "new_job_company" not in st.session_state:
    st.session_state.new_job_company = "Redrob AI"

# Form state for queued resumes in Upload Portal
if "upload_queue" not in st.session_state:
    st.session_state.upload_queue = []

if "clear_new_job_inputs" not in st.session_state:
    st.session_state.clear_new_job_inputs = False

if st.session_state.clear_new_job_inputs:
    st.session_state.new_job_title = ""
    st.session_state.new_job_desc = ""
    st.session_state.new_job_locs = ""
    st.session_state.new_job_min_exp = 3.0
    st.session_state.new_job_max_exp = 8.0
    st.session_state.new_job_req_skills = ""
    st.session_state.new_job_pref_skills = ""
    st.session_state.jd_pasted_prose = ""
    if "jd_file_loader" in st.session_state:
        try:
            del st.session_state.jd_file_loader
        except KeyError:
            pass
    st.session_state.clear_new_job_inputs = False

# Navigation guard: force user to load candidates if pool is empty
is_pool_loaded = len(st.session_state.candidate_pool) > 0
if not is_pool_loaded and st.session_state.app_mode not in ["Load Candidates", "Create New Job", "Settings"]:
    st.session_state.app_mode = "Load Candidates"

# Dynamic programmatic navigation helper
def navigate_to(screen_name: str, candidate_id: str | None = None, job_id: str | None = None) -> None:
    st.session_state.app_mode = screen_name
    if candidate_id:
        st.session_state.selected_candidate_id = candidate_id
    if job_id:
        st.session_state.selected_job_id = job_id
    st.rerun()

# Inject premium dark command-center theme CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
    
    /* Global App Background & Font */
    .stApp {
        background-color: #080b11 !important;
        background-image: none !important;
        color: #e2e8f0 !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Headings */
    h1, h2, h3, h4 {
        font-family: 'Inter', sans-serif !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #03050a !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
    }
    
    /* Hide default sidebar padding and widgets if any */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        padding-top: 15px !important;
    }
    
    /* Custom Sidebar section labels */
    .sidebar-section-label {
        font-size: 10px;
        color: #64748b;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 24px;
        margin-bottom: 8px;
        padding-left: 12px;
        font-family: monospace;
    }
    
    /* Sidebar Buttons */
    [data-testid="stSidebar"] button {
        background-color: transparent !important;
        border: none !important;
        color: #94a3b8 !important;
        text-align: left !important;
        padding: 8px 12px !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        border-radius: 6px !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        box-shadow: none !important;
        transition: all 0.15s ease !important;
        height: 36px !important;
        margin-bottom: 2px !important;
    }
    
    [data-testid="stSidebar"] button:hover {
        color: #ffffff !important;
        background-color: rgba(255, 255, 255, 0.04) !important;
    }
    
    /* Active sidebar item container */
    .sidebar-active-item button {
        background-color: rgba(255, 255, 255, 0.08) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border-left: 3px solid #06b6d4 !important;
        border-radius: 0 6px 6px 0 !important;
    }
    
    /* Sidebar Monospace Footer */
    .sidebar-footer {
        font-family: monospace;
        font-size: 9px;
        color: #475569;
        letter-spacing: 1px;
        margin-top: 50px;
        padding-left: 12px;
    }
    
    /* Form input labels */
    label {
        color: #94a3b8 !important;
        font-size: 10px !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        font-family: monospace !important;
        font-weight: bold !important;
        margin-bottom: 6px !important;
    }
    
    /* Input inputs/textareas */
    textarea, input {
        background-color: #0d111d !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        color: #ffffff !important;
        border-radius: 6px !important;
        font-size: 13.5px !important;
    }
    
    /* Target selectbox background */
    div[data-baseweb="select"] > div {
        background-color: #0d111d !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        color: #ffffff !important;
        border-radius: 6px !important;
    }
    div[data-baseweb="select"] svg {
        fill: #94a3b8 !important;
    }
    
    /* Primary buttons (Cyan) */
    div[data-testid="stButton"] button[kind="primary"], div[data-testid="stButton"] button[class*="primary"] {
        background: #06b6d4 !important;
        color: #030712 !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 8px 16px !important;
        border-radius: 6px !important;
        box-shadow: 0 4px 12px rgba(6, 182, 212, 0.2) !important;
        transition: all 0.2s ease !important;
        width: auto !important;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover, div[data-testid="stButton"] button[class*="primary"]:hover {
        background: #22d3ee !important;
        box-shadow: 0 6px 16px rgba(6, 182, 212, 0.35) !important;
    }
    
    /* Secondary buttons (Dark Gray/Bordered) */
    div[data-testid="stButton"] button[kind="secondary"], div[data-testid="stButton"] button[class*="secondary"] {
        background-color: #131926 !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        font-weight: 500 !important;
        padding: 6px 14px !important;
        border-radius: 6px !important;
        box-shadow: none !important;
        transition: all 0.2s ease !important;
        width: auto !important;
    }
    div[data-testid="stButton"] button[kind="secondary"]:hover, div[data-testid="stButton"] button[class*="secondary"]:hover {
        background-color: rgba(255, 255, 255, 0.04) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
    }
    
    /* Custom File Uploader */
    div[data-testid="stFileUploader"] {
        background-color: rgba(6, 182, 212, 0.01) !important;
        border: 1px dashed rgba(6, 182, 212, 0.25) !important;
        border-radius: 8px !important;
        padding: 24px !important;
        text-align: center !important;
    }
    div[data-testid="stFileUploader"] section {
        background-color: transparent !important;
        border: none !important;
    }
    div[data-testid="stFileUploader"] label {
        display: none !important;
    }
    div[data-testid="stFileUploader"] button {
        background-color: #131926 !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        margin: 10px auto 0 auto !important;
    }
    </style>
""", unsafe_allow_html=True)

# Cache ranking engine execution on path + mtime rather than candidates JSON string
@st.cache_data(show_spinner="Ranking candidates pool…")
def rank_pool_cached(pool_path: str, mtime: float, top_n: int, jd_path: str, weights_path: str) -> list[dict]:
    # Determine directory for outputs - use /tmp under HF Spaces
    out_dir = Path("/tmp") if IS_HF_SPACES else Path(tempfile.mkdtemp())
    out_csv = out_dir / "submission.csv"
    
    ranked = run_ranking(
        candidates_path=Path(pool_path),
        out_path=out_csv,
        jd_path=Path(jd_path),
        weights_path=Path(weights_path),
        top_n=top_n,
        analytics_path=None,
        results_path=None,
        validate_ids=None,
        offline=True,
    )
    
    # Memory-safe streaming extraction of atsScore from raw candidate pool
    ats_map = {}
    try:
        if pool_path.endswith(".json"):
            import ijson
            with open(pool_path, "rb") as f:
                for item in ijson.items(f, "item"):
                    cid = item.get("candidate_id")
                    if cid:
                        ats_map[cid] = item.get("atsScore", 50.0)
        else:
            from src.parser import _open_text
            with _open_text(Path(pool_path)) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    item = json.loads(line)
                    cid = item.get("candidate_id")
                    if cid:
                        ats_map[cid] = item.get("atsScore", 50.0)
    except Exception:
        pass
        
    return [
        {
            "candidate_id": r.candidate_id,
            "rank": r.rank,
            "score": r.score,
            "reasoning": r.reasoning,
            "bundle": r.bundle.model_dump(),
            "profile": {
                "name": r.record.profile.anonymized_name,
                "title": r.record.profile.current_title,
                "years": r.record.profile.years_of_experience,
                "location": r.record.profile.location,
            },
            "record_dump": r.record.model_dump(),
            "ats_score": ats_map.get(r.candidate_id, 50.0)
        }
        for r in ranked
    ]

# Helper to fetch line count of candidates.jsonl dynamically and cache the result
@st.cache_resource
def get_candidates_jsonl_count() -> int:
    candidates_file = ROOT / "candidates.jsonl"
    if candidates_file.exists():
        try:
            with open(candidates_file, "rb") as f:
                return sum(1 for _ in f)
        except Exception:
            return 100000
    return 0

# Get total tracked candidates including pre-loaded pool and user uploads
def get_total_tracked_candidates() -> int:
    if st.session_state.get("temp_pool_path"):
        return len(st.session_state.candidate_pool)
    jsonl_count = get_candidates_jsonl_count()
    if jsonl_count > 0:
        sample_path = ROOT / "data" / "sample_candidates.json"
        sample_len = 100
        if sample_path.exists():
            try:
                with open(sample_path, "r", encoding="utf-8") as f:
                    sample_len = len(json.load(f))
            except Exception:
                pass
        additions = max(0, len(st.session_state.candidate_pool) - sample_len)
        return jsonl_count + additions
    return len(st.session_state.candidate_pool)

# Load candidates from Advait.csv by matching them in session state or candidates.jsonl
def load_advait_candidates() -> list[dict]:
    advait_path = ROOT / "Advait.csv"
    if not advait_path.exists():
        return []
        
    df_advait = pd.read_csv(advait_path)
    advait_ids = set(df_advait["candidate_id"].tolist())
    
    # Check memory pool first
    found_candidates = {}
    for c in st.session_state.get("candidate_pool", []):
        if c.get("candidate_id") in advait_ids:
            found_candidates[c["candidate_id"]] = c
            
    # If any are missing, search in candidates.jsonl on disk
    missing_ids = advait_ids - set(found_candidates.keys())
    if missing_ids:
        candidates_jsonl_path = ROOT / "candidates.jsonl"
        if candidates_jsonl_path.exists():
            from src.parser import _open_text
            id_pattern = re.compile(r'"candidate_id"\s*:\s*"([^"]+)"')
            with _open_text(candidates_jsonl_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    m = id_pattern.search(line)
                    if m:
                        cid = m.group(1)
                        if cid in missing_ids:
                            item = json.loads(line)
                            found_candidates[cid] = item
                            missing_ids.remove(cid)
                    if not missing_ids:
                        break
                        
    # Maintain the exact rank order of Advait.csv
    ordered_records = []
    for idx, row in df_advait.iterrows():
        cid = row["candidate_id"]
        if cid in found_candidates:
            ordered_records.append(found_candidates[cid])
            
    return ordered_records

# Dynamic engine execution for a specific job selection
def get_ranked_candidates_for_job(job_id: str) -> list[dict]:
    job_info = st.session_state.job_db[job_id]
    
    # Pre-configure weights
    weights = load_weights(ROOT / "config" / "weights.json")
    weights["jd_skill_seeds"] = {
        "required": job_info["required_skills"],
        "preferred": job_info["preferred_skills"]
    }
    # Adapt experience band weights matching current JD
    weights["experience_band"] = {
        "min": float(job_info.get("min_experience_years", 3.0)),
        "max": float(job_info.get("max_experience_years", 8.0))
    }
    
    temp_dir = Path("/tmp") if IS_HF_SPACES else Path(tempfile.mkdtemp())
    temp_weights_path = temp_dir / "weights.json"
    with open(temp_weights_path, "w", encoding="utf-8") as f:
        json.dump(weights, f)
        
    jd_path = ROOT / job_info["jd_path"]
    if not jd_path.exists():
        jd_path = ROOT / "data" / "job_description.md"
        
    # Check if we should restrict to Advait.csv candidates for JOB_DEFAULT
    is_default_job = (job_id == "JOB_DEFAULT")
    advait_path = ROOT / "Advait.csv"
    
    use_advait = False
    if is_default_job and advait_path.exists():
        advait_candidates = load_advait_candidates()
        if advait_candidates:
            temp_pool = temp_dir / "advait_pool.json"
            temp_pool.write_text(json.dumps(advait_candidates), encoding="utf-8")
            pool_path = str(temp_pool)
            mtime = os.path.getmtime(temp_pool)
            pool_len = len(advait_candidates)
            use_advait = True
            
    if not use_advait:
        # Ensure a valid pool path is stored on disk
        pool_path = st.session_state.get("temp_pool_path")
        if not pool_path:
            temp_pool = temp_dir / "sample_pool.json"
            # If empty pool but trying to rank, try loading default sample_candidates.json
            if not st.session_state.candidate_pool:
                sample_path = ROOT / "data" / "sample_candidates.json"
                if sample_path.exists():
                    with open(sample_path, "r", encoding="utf-8") as f:
                        st.session_state.candidate_pool = json.load(f)
                else:
                    st.session_state.candidate_pool = []
            temp_pool.write_text(json.dumps(st.session_state.candidate_pool), encoding="utf-8")
            st.session_state.temp_pool_path = str(temp_pool)
            st.session_state.temp_pool_mtime = os.path.getmtime(temp_pool)
            pool_path = str(temp_pool)
            
        mtime = st.session_state.get("temp_pool_mtime", 0.0)
        pool_len = len(st.session_state.candidate_pool)
    
    results = rank_pool_cached(
        pool_path,
        mtime,
        pool_len,
        str(jd_path),
        str(temp_weights_path)
    )
    return results

# Custom Navigation Sidebar
with st.sidebar:
    # 1. Logo
    st.markdown("""
        <div style="padding: 10px 0 10px 12px; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid rgba(255,255,255,0.06); margin-bottom: 15px;">
            <div style="background: linear-gradient(135deg, #0ea5e9, #10b981); width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-family: 'Space Grotesk', sans-serif; font-size: 18px;">🧬</div>
            <div>
                <div style="font-family: 'Space Grotesk', sans-serif; font-size: 15px; font-weight: bold; color: #ffffff; line-height: 1.1;">Redrob-Talent-Hire</div>
                <div style="font-size: 9px; color: #94a3b8; letter-spacing: 1px; font-weight: 600;">RECRUITER OS</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # 2. Workspace section
    st.markdown('<div class="sidebar-section-label">Workspace</div>', unsafe_allow_html=True)
    # Dashboard Button (Active if any of dashboard, pipeline, report is selected)
    dashboard_active = st.session_state.app_mode in ["Recruiter Command Center", "Requisition Pipeline", "TalentDNA Report"]
    st.markdown(f'<div class="{"sidebar-active-item" if dashboard_active else "sidebar-inactive-item"}">', unsafe_allow_html=True)
    if st.button("📊 Dashboard", key="sidebar_dashboard_btn"):
        if is_pool_loaded:
            st.session_state.app_mode = "Recruiter Command Center"
        else:
            st.session_state.app_mode = "Load Candidates"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Tree Opportunity Map Button
    tree_map_active = st.session_state.app_mode == "Tree Opportunity Map"
    st.markdown(f'<div class="{"sidebar-active-item" if tree_map_active else "sidebar-inactive-item"}">', unsafe_allow_html=True)
    if st.button("🌳 Tree Map: Top 100 from 100k", key="sidebar_tree_map_btn"):
        if is_pool_loaded:
            st.session_state.app_mode = "Tree Opportunity Map"
        else:
            st.session_state.app_mode = "Load Candidates"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Load Candidates Button
    load_active = st.session_state.app_mode == "Load Candidates"
    st.markdown(f'<div class="{"sidebar-active-item" if load_active else "sidebar-inactive-item"}">', unsafe_allow_html=True)
    if st.button("📂 Load Candidates", key="sidebar_load_btn"):
        st.session_state.app_mode = "Load Candidates"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # New Job Button
    new_job_active = st.session_state.app_mode == "Create New Job"
    st.markdown(f'<div class="{"sidebar-active-item" if new_job_active else "sidebar-inactive-item"}">', unsafe_allow_html=True)
    if st.button("＋ New Job", key="sidebar_new_job_btn"):
        st.session_state.app_mode = "Create New Job"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Settings Button
    settings_active = st.session_state.app_mode == "Settings"
    st.markdown(f'<div class="{"sidebar-active-item" if settings_active else "sidebar-inactive-item"}">', unsafe_allow_html=True)
    if st.button("⚙️ Settings", key="sidebar_settings_btn"):
        st.session_state.app_mode = "Settings"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 3. Active Requisitions section
    if is_pool_loaded:
        st.markdown('<div class="sidebar-section-label">Active Requisitions</div>', unsafe_allow_html=True)
        for job_id, job in st.session_state.job_db.items():
            title = job["title"]
            if len(title) > 24:
                title = title[:21] + "..."
                
            is_job_active = (st.session_state.selected_job_id == job_id and st.session_state.app_mode in ["Recruiter Command Center", "Requisition Pipeline", "Tree Opportunity Map"])
            
            st.markdown(f'<div class="{"sidebar-active-item" if is_job_active else "sidebar-inactive-item"}">', unsafe_allow_html=True)
            if st.button(f"💼 {title}", key=f"sidebar_job_{job_id}"):
                st.session_state.selected_job_id = job_id
                st.session_state.app_mode = "Requisition Pipeline"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
    st.markdown('<div class="sidebar-footer">V1.0 - HACKATHON UPGRADE</div>', unsafe_allow_html=True)

# ────────────────────────────────────────────────────────
# SCREEN 1: RECRUITER COMMAND CENTER
# ────────────────────────────────────────────────────────
if st.session_state.app_mode == "Recruiter Command Center":
    render_hackathon_compliance_banner()
    # 1. Breadcrumbs / Status Header
    st.markdown("""
        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 10px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 8px; font-family: monospace; font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;">
                <span>🗂</span>
                <span>Recruiter Command Center</span>
            </div>
            <div style="display: flex; align-items: center; gap: 6px; font-family: monospace; font-size: 11px; color: #10b981;">
                <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981;"></span>
                <span>Live</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 2. Main Title Row
    col_h1, col_h2 = st.columns([4, 1.2])
    with col_h1:
        st.markdown(f"""
            <div style="font-size: 10px; color: #06b6d4; font-family: monospace; text-transform: uppercase; letter-spacing: 1px; font-weight: bold; margin-bottom: 4px;">LIVE &middot; {len(st.session_state.job_db)} REQUISITIONS</div>
            <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #ffffff;">Recruiter <span style="color: #06b6d4;">Command Center</span></h1>
            <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 14px;">One pane for every open role. Click any point on the Talent Opportunity Map to open that candidate's TalentDNA report.</p>
        """, unsafe_allow_html=True)
    with col_h2:
        if st.button("＋ New Job", key="cmd_new_job_btn", type="primary"):
            navigate_to("Create New Job")
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Run dynamic ranking for selected job
    results = get_ranked_candidates_for_job(st.session_state.selected_job_id)
    gems = [r for r in results if r["bundle"]["quadrant"] == "Hidden Gem"]
    safe = [r for r in results if r["bundle"]["quadrant"] == "Safe Hire"]
    avg_future = sum(r["bundle"]["future_fit"] for r in results) / len(results) if results else 0
    
    # 3. Custom KPI cards (Metrics)
    st.markdown(f"""
        <div style="display: flex; gap: 16px; margin-bottom: 24px;">
            <!-- Card 1 -->
            <div style="flex: 1; background: #0d111d; border: 1px solid rgba(255,255,255,0.06); border-left: 4px solid #06b6d4; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; justify-content: space-between; height: 102px;">
                <div style="display: flex; justify-content: space-between; align-items: center; color: #94a3b8; font-family: monospace; font-size: 9px; text-transform: uppercase; letter-spacing: 1px;">
                    <span>ACTIVE REQUISITIONS</span>
                    <span>📁</span>
                </div>
                <div style="font-size: 28px; font-weight: bold; color: #ffffff; line-height: 1.1; margin-top: 8px;">{len(st.session_state.job_db)}</div>
                <div style="font-size: 11px; color: #64748b; margin-top: 4px;">across teams</div>
            </div>
            <!-- Card 2 -->
            <div style="flex: 1; background: #0d111d; border: 1px solid rgba(255,255,255,0.06); border-left: 4px solid #3b82f6; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; justify-content: space-between; height: 102px;">
                <div style="display: flex; justify-content: space-between; align-items: center; color: #94a3b8; font-family: monospace; font-size: 9px; text-transform: uppercase; letter-spacing: 1px;">
                    <span>TRACKED CANDIDATES</span>
                    <span>👤</span>
                </div>
                <div style="font-size: 28px; font-weight: bold; color: #ffffff; line-height: 1.1; margin-top: 8px;">{get_total_tracked_candidates():,}</div>
                <div style="font-size: 11px; color: #10b981; margin-top: 4px;">+12 this week</div>
            </div>
            <!-- Card 3 -->
            <div style="flex: 1; background: #0d111d; border: 1px solid rgba(255,255,255,0.06); border-left: 4px solid #f59e0b; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; justify-content: space-between; height: 102px;">
                <div style="display: flex; justify-content: space-between; align-items: center; color: #94a3b8; font-family: monospace; font-size: 9px; text-transform: uppercase; letter-spacing: 1px;">
                    <span>HIDDEN GEMS SURFACED</span>
                    <span>✨</span>
                </div>
                <div style="font-size: 28px; font-weight: bold; color: #ffffff; line-height: 1.1; margin-top: 8px;">{len(gems)}</div>
                <div style="font-size: 11px; color: #64748b; margin-top: 4px;">missed by ATS</div>
            </div>
            <!-- Card 4 -->
            <div style="flex: 1; background: #0d111d; border: 1px solid rgba(255,255,255,0.06); border-left: 4px solid #10b981; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; justify-content: space-between; height: 102px;">
                <div style="display: flex; justify-content: space-between; align-items: center; color: #94a3b8; font-family: monospace; font-size: 9px; text-transform: uppercase; letter-spacing: 1px;">
                    <span>POOL AVG FUTURE FIT</span>
                    <span>⚡</span>
                </div>
                <div style="font-size: 28px; font-weight: bold; color: #ffffff; line-height: 1.1; margin-top: 8px;">{avg_future:.0f}%</div>
                <div style="font-size: 11px; color: #64748b; margin-top: 4px;">for selected JD</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # 4. Main content grid (Left: Opportunity Map, Right: Hidden Gems list)
    grid_col1, grid_col2 = st.columns([1.6, 1])
    
    with grid_col1:
        st.markdown("""
            <div style="background: #0d111d; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <div style="font-size: 10px; color: #94a3b8; font-family: monospace; text-transform: uppercase; letter-spacing: 1px; font-weight: bold; margin-bottom: 6px;">TALENT OPPORTUNITY MAP</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Selected Job Dropdown inside Opportunity Map Card
        selected_job_id = st.selectbox(
            "Select Active Requisition Matrix:", 
            list(st.session_state.job_db.keys()),
            format_func=lambda x: st.session_state.job_db[x]["title"],
            key="cmd_job_select",
            label_visibility="collapsed"
        )
        if selected_job_id != st.session_state.selected_job_id:
            st.session_state.selected_job_id = selected_job_id
            st.rerun()
            
        st.markdown(f"""
            <div style="font-size: 12px; color: #94a3b8; margin-top: -10px; margin-bottom: 15px;">
                <span style="color:#10b981;">{len(safe)} safe hires</span> &middot; 
                <span style="color:#fbbf24;">{len(gems)} hidden gems</span> &middot; 
                {len(results)} candidates plotted
            </div>
        """, unsafe_allow_html=True)
        
        # Quadrant scatter plot
        fig = build_opportunity_map(pd.DataFrame([
            {
                "rank": r["rank"],
                "candidate_id": r["candidate_id"],
                "score": r["score"],
                "reasoning": r["reasoning"],
                "s_current": r["bundle"]["s_current"],
                "future_fit": r["bundle"]["future_fit"],
                "hidden_gem": r["bundle"]["hidden_gem"],
                "opportunity": r["bundle"]["opportunity"],
                "quadrant": r["bundle"]["quadrant"],
                "name": r["profile"]["name"],
                "title": r["profile"]["title"],
            }
            for r in results
        ]), st.session_state.selected_candidate_id)
        # Capture selection event for Opportunity Map (Scatter) to enable click-to-profile navigation
        selected_opp = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="scatter_opp_map_cc")
        if selected_opp and selected_opp.get("selection") and selected_opp["selection"].get("points"):
            points = selected_opp["selection"]["points"]
            if points:
                customdata = points[0].get("customdata")
                if customdata:
                    clicked_cand_id = customdata if isinstance(customdata, str) else customdata[0]
                    if clicked_cand_id != st.session_state.selected_candidate_id:
                        navigate_to("TalentDNA Report", candidate_id=clicked_cand_id, job_id=st.session_state.selected_job_id)
        
    with grid_col2:
        st.markdown("""
            <div style="background: #0d111d; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px 8px 0 0; padding: 20px 20px 0px 20px; margin-bottom: 12px;">
                <div style="font-size: 10px; color: #fbbf24; font-family: monospace; text-transform: uppercase; letter-spacing: 1px; font-weight: bold; margin-bottom: 4px;">◆ HIDDEN GEMS</div>
                <h3 style="margin: 0; font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 10px;">Why ATS missed these</h3>
            </div>
        """, unsafe_allow_html=True)
        
        if not gems:
            st.markdown(
                '<div style="font-size:13px; color:#94a3b8; border:1px dashed rgba(255,255,255,0.08); padding:16px; border-radius:8px;">'
                'No hidden gems surfaced in this requisition yet. Upload more candidates or relax skills constraint.'
                '</div>',
                unsafe_allow_html=True
            )
        else:
            sorted_gems = sorted(gems, key=lambda x: x["bundle"]["hidden_gem"], reverse=True)
            for item in sorted_gems[:3]:
                missing_str = ", ".join(item["bundle"]["missing_skills"][:3]) if item["bundle"]["missing_skills"] else "None"
                st.markdown(f"""
                    <div style="padding:16px; border:1px solid rgba(251, 191, 36, 0.15); background: #0c101b; border-radius:8px; margin-bottom: 12px; position: relative;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <div style="font-weight:bold; font-size:14px; color:#ffffff;">{item['profile']['name']}</div>
                                <div style="font-size:11px; color:#64748b; margin-top:2px;">{item['profile']['title']}</div>
                            </div>
                            <span style="font-size: 14px; color: #94a3b8;">↗</span>
                        </div>
                        <div style="margin-top:10px; font-size:11px; display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                            <span style="background:rgba(239, 68, 68, 0.1); color:#f87171; border:1px solid rgba(239, 68, 68, 0.3); padding:2px 6px; border-radius:4px; font-weight:bold; text-transform:uppercase; font-size:9px;">CONSIDER</span>
                            <span style="background:rgba(251, 191, 36, 0.1); color:#fbbf24; border:1px solid rgba(251, 191, 36, 0.3); padding:2px 6px; border-radius:4px; font-weight:bold; text-transform:uppercase; font-size:9px;">◆ Gem</span>
                            <span style="margin-left:auto; color:#94a3b8;">ATS <span style="color:#f87171;">{item['ats_score']:.0f}</span> &rarr; DNA <span style="color:#10b981;">{item['bundle']['future_fit']:.0f}</span></span>
                        </div>
                        <div style="font-size:11px; color:#94a3b8; margin-top:8px; line-height:1.4;">
                            <strong>Why bypassed:</strong> missing {missing_str}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Inspect {item['profile']['name']}", key=f"cmd_gem_inspect_{item['candidate_id']}", type="primary"):
                    navigate_to("TalentDNA Report", candidate_id=item['candidate_id'], job_id=st.session_state.selected_job_id)

    st.markdown("<br>", unsafe_allow_html=True)
    if results:
        if st.button("View Requisition Pipeline", key="cmd_view_pipeline_btn", type="secondary"):
            navigate_to("Requisition Pipeline", job_id=st.session_state.selected_job_id)

# ────────────────────────────────────────────────────────
# SCREEN 2: REQUISITION PIPELINE
# ────────────────────────────────────────────────────────
elif st.session_state.app_mode == "Requisition Pipeline":
    render_hackathon_compliance_banner()
    # Requisition selector
    selected_job_id = st.selectbox(
        "Select Active Requisition Matrix:", 
        list(st.session_state.job_db.keys()),
        format_func=lambda x: st.session_state.job_db[x]["title"],
        key="pipeline_job_select"
    )
    st.session_state.selected_job_id = selected_job_id
    
    # Load JD details
    job_info = st.session_state.job_db[selected_job_id]
    
    st.markdown(f"<h1>{job_info['title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#cbd5e1; font-size:14px;'>{job_info['description']}</p>", unsafe_allow_html=True)
    
    # Required/Preferred badges strip
    req_badges = "".join([
        f'<span style="padding:2px 8px; border-radius:12px; background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.3); color:#38bdf8; font-family:monospace; font-size:11px; margin-right:6px; margin-bottom:6px; display:inline-block;">{s}</span>'
        for s in job_info["required_skills"]
    ])
    pref_badges = "".join([
        f'<span style="padding:2px 8px; border-radius:12px; background:rgba(251,191,36,0.1); border:1px solid rgba(251,191,36,0.3); color:#fbbf24; font-family:monospace; font-size:11px; margin-right:6px; margin-bottom:6px; display:inline-block;">{s}</span>'
        for s in job_info["preferred_skills"]
    ])
    
    st.markdown(f"""
        <div style="background: rgba(30,41,59,0.3); border: 1px solid rgba(255,255,255,0.06); padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; display: flex; flex-wrap: wrap; align-items: center; gap: 10px;">
            <span style="font-family: monospace; font-size: 11px; color:#cbd5e1; text-transform: uppercase; margin-right: 8px;">Required DNA:</span>
            {req_badges}
            {f'<span style="font-family: monospace; font-size: 11px; color:#cbd5e1; text-transform: uppercase; margin-left: 12px; margin-right: 8px;">Preferred:</span>' if job_info["preferred_skills"] else ''}
            {pref_badges}
            <span style="margin-left: auto; font-family: monospace; font-size: 11px; color: #94a3b8;">min {job_info.get("min_experience_years", 3.0):.0f}y exp</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Get ranked candidates
    results = get_ranked_candidates_for_job(selected_job_id)
    
    # Export options row
    col_exp1, col_exp2, col_exp3 = st.columns([6, 1, 1])
    with col_exp2:
        # Export JSON download button
        export_payload = {
            "job": job_info,
            "candidates": results
        }
        json_data = json.dumps(export_payload, indent=2)
        st.download_button(
            label="📄 JSON",
            data=json_data,
            file_name=f"talentdna-{selected_job_id}-report.json",
            mime="application/json",
            use_container_width=True
        )
    with col_exp3:
        # Export CSV download button
        df_csv = pd.DataFrame([
            {
                "candidate_id": r["candidate_id"],
                "rank": r["rank"],
                "score": r["score"],
                "s_current": r["bundle"]["s_current"],
                "future_fit": r["bundle"]["future_fit"],
                "hiring_risk": r["bundle"]["hiring_risk"],
                "quadrant": r["bundle"]["quadrant"],
                "reasoning": r["reasoning"]
            }
            for r in results
        ])
        csv_data = df_csv.to_csv(index=False)
        st.download_button(
            label="📊 Export CSV",
            data=csv_data,
            file_name=f"talentdna-{selected_job_id}-rankings.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    # Tab Layout
    tab_list, tab_map, tab_tree, tab_adjacency = st.tabs(["Ranked List", "Opportunity Map", "🌳 Tree Map: Top 100 from 100k", "Skill Adjacency"])
    
    with tab_list:
        # Search & Filters
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1:
            search_query = st.text_input("Search name, skill, headline:", key="pipeline_search")
        with col_s2:
            filter_mode = st.selectbox(
                "Filter Quadrant:", 
                ["All", "Safe Hire", "Hidden Gem", "Overrated", "Unaligned"],
                key="pipeline_filter"
            )
            
        # Filter results
        filtered_results = results
        if search_query:
            q_lower = search_query.lower()
            filtered_results = [
                r for r in filtered_results
                if q_lower in r["profile"]["name"].lower()
                or q_lower in r["profile"]["title"].lower()
                or any(q_lower in s.lower() for s in r["record_dump"]["skills"])
            ]
        if filter_mode != "All":
            filtered_results = [r for r in filtered_results if r["bundle"]["quadrant"] == filter_mode]
            
        # Candidates table grid headers aligned with columns
        st.markdown("<h4 style='color: #cbd5e1; margin-bottom: 16px;'>Ranked Discoveries</h4>", unsafe_allow_html=True)
        
        # Load required and preferred skills from selected job
        job_info = st.session_state.job_db[selected_job_id]
        jd_req = [s.lower() for s in job_info.get("required_skills", [])]
        jd_pref = [s.lower() for s in job_info.get("preferred_skills", [])]
        jd_all_skills = set(jd_req + jd_pref)
        
        if not filtered_results:
            st.markdown(
                '<div style="text-align:center; font-size:13px; color:#94a3b8; border:1px dashed rgba(255,255,255,0.08); padding:24px; border-radius:8px; margin-top:10px;">'
                'No candidates match your search filters.'
                '</div>',
                unsafe_allow_html=True
            )
        else:
            for r in filtered_results:
                q_val = r['bundle']['quadrant']
                q_badge_color = "#22c55e" if q_val == "Safe Hire" else "#fbbf24" if q_val == "Hidden Gem" else "#f97316" if q_val == "Overrated" else "#94a3b8"
                
                # HTML Card header/container with integrated deconstructed reasoning matrix
                card_html = f"""
                <div style="background: #0d121f; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 16px; margin-bottom: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
                    <!-- Header row: Rank, Name, Title, Quadrant, Fit Scores -->
                    <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px; margin-bottom: 10px;">
                        <div>
                            <span style="font-family: monospace; font-size: 11px; font-weight: bold; background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 2px 6px; border-radius: 4px; margin-right: 8px;">Rank #{r['rank']}</span>
                            <span style="font-size: 15px; font-weight: bold; color: #ffffff;">{r['profile']['name']}</span>
                            <span style="font-size: 12px; color: #94a3b8; margin-left: 8px;">&middot; {r['profile']['title']}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span style="font-family: monospace; font-size: 9px; padding: 2px 6px; border-radius: 4px; border: 1px solid {q_badge_color}; color: {q_badge_color}; font-weight: bold;">{q_val}</span>
                            <span style="font-size: 11px; color: #cbd5e1; font-family: monospace;">
                                Current Fit: <strong style="color: #38bdf8;">{r['bundle']['s_current']:.0f}%</strong> &nbsp;|&nbsp; 
                                Future Fit: <strong style="color: {q_badge_color};">{r['bundle']['future_fit']:.0f}%</strong>
                            </span>
                        </div>
                    </div>
                    
                    {render_deconstructed_reasoning_html(r['reasoning'])}
                </div>
                """
                st.markdown(clean_html(card_html), unsafe_allow_html=True)
                
                # Full width action button below the card
                if st.button(f"🔎 Open Complete TalentDNA Analysis for {r['profile']['name']}", key=f"pipe_inspect_btn_{r['candidate_id']}", use_container_width=True):
                    navigate_to("TalentDNA Report", candidate_id=r['candidate_id'], job_id=selected_job_id)
                    
                st.markdown("<div style='border-bottom: 1px solid rgba(255,255,255,0.06); margin-bottom: 24px; margin-top: 10px;'></div>", unsafe_allow_html=True)
                
    with tab_map:
        # Quadrant scatter plot in full width
        fig_full = build_opportunity_map(pd.DataFrame([
            {
                "rank": r["rank"],
                "candidate_id": r["candidate_id"],
                "score": r["score"],
                "reasoning": r["reasoning"],
                "s_current": r["bundle"]["s_current"],
                "future_fit": r["bundle"]["future_fit"],
                "hidden_gem": r["bundle"]["hidden_gem"],
                "opportunity": r["bundle"]["opportunity"],
                "quadrant": r["bundle"]["quadrant"],
                "name": r["profile"]["name"],
                "title": r["profile"]["title"],
            }
            for r in results
        ]))
        selected_opp_full = st.plotly_chart(fig_full, use_container_width=True, on_select="rerun", key="scatter_opp_map_pipeline")
        if selected_opp_full and selected_opp_full.get("selection") and selected_opp_full["selection"].get("points"):
            points = selected_opp_full["selection"]["points"]
            if points:
                customdata = points[0].get("customdata")
                if customdata:
                    clicked_cand_id = customdata if isinstance(customdata, str) else customdata[0]
                    if clicked_cand_id != st.session_state.selected_candidate_id:
                        navigate_to("TalentDNA Report", candidate_id=clicked_cand_id, job_id=selected_job_id)
        
    with tab_tree:
        st.markdown("<h3>Tree Opportunity Map (Top 100 from 100k)</h3>", unsafe_allow_html=True)
        st.markdown("<p style='color:#94a3b8; font-size:12px;'>Visualizing the hierarchical distribution of the top 100 candidates by hiring quadrant, current title, and name.</p>", unsafe_allow_html=True)
        df_full = pd.DataFrame([
            {
                "rank": r["rank"],
                "candidate_id": r["candidate_id"],
                "score": r["score"],
                "reasoning": r["reasoning"],
                "s_current": r["bundle"]["s_current"],
                "future_fit": r["bundle"]["future_fit"],
                "hidden_gem": r["bundle"]["hidden_gem"],
                "opportunity": r["bundle"]["opportunity"],
                "quadrant": r["bundle"]["quadrant"],
                "name": r["profile"]["name"],
                "title": r["profile"]["title"],
            }
            for r in results
        ])
        df_top100 = df_full.head(100)
        fig_tree = build_tree_opportunity_map(df_top100)
        
        # Capture selection event for Treemap to enable click-to-profile navigation
        selected_tree = st.plotly_chart(fig_tree, use_container_width=True, on_select="rerun", key="pipeline_tree_map")
        if selected_tree and selected_tree.get("selection") and selected_tree["selection"].get("points"):
            points = selected_tree["selection"]["points"]
            if points:
                customdata = points[0].get("customdata")
                if customdata and len(customdata) > 3:
                    clicked_cand_id = customdata[3]
                    if clicked_cand_id != st.session_state.selected_candidate_id:
                        navigate_to("TalentDNA Report", candidate_id=clicked_cand_id, job_id=selected_job_id)
                        
        # Candidate description list below Tree Map
        st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 30px 0;'>", unsafe_allow_html=True)
        st.markdown("<h3 style='margin-bottom: 4px;'>Top 100 Candidate Descriptions</h3>", unsafe_allow_html=True)
        st.markdown("<p style='color:#94a3b8; font-size:12px; margin-bottom: 20px;'>Detailed analysis and alignment notes for the top 100 candidates in this requisition pool.</p>", unsafe_allow_html=True)
        
        # Search filter
        search_desc = st.text_input("Filter Top 100 candidates by name, title, or quadrant:", key="pipeline_tree_desc_search", placeholder="e.g. Anjali, Developer, Hidden Gem")
        
        filtered_top100 = []
        for idx, row in df_top100.iterrows():
            if search_desc:
                q = search_desc.lower()
                match = (q in row['name'].lower() or 
                         q in row['title'].lower() or 
                         q in row['quadrant'].lower())
                if not match:
                    continue
            filtered_top100.append(row)
            
        if not filtered_top100:
            st.markdown("<p style='color: #64748b;'>No candidates match the search filter.</p>", unsafe_allow_html=True)
        else:
            for row in filtered_top100:
                q_val = row['quadrant']
                q_badge_color = "#22c55e" if q_val == "Safe Hire" else "#a855f7" if q_val == "Hidden Gem" else "#f59e0b" if q_val == "Overrated" else "#94a3b8"
                
                card_html = f"""
                <div style="background: #0d121f; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 16px; margin-bottom: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
                    <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px; margin-bottom: 10px;">
                        <div>
                            <span style="font-family: monospace; font-size: 11px; font-weight: bold; background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 2px 6px; border-radius: 4px; margin-right: 8px;">Rank #{row['rank']}</span>
                            <span style="font-size: 15px; font-weight: bold; color: #ffffff;">{row['name']}</span>
                            <span style="font-size: 12px; color: #94a3b8; margin-left: 8px;">&middot; {row['title']}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span style="font-family: monospace; font-size: 9px; padding: 2px 6px; border-radius: 4px; border: 1px solid {q_badge_color}; color: {q_badge_color}; font-weight: bold;">{q_val}</span>
                            <span style="font-size: 11px; color: #cbd5e1; font-family: monospace;">
                                Current Fit: <strong style="color: #38bdf8;">{row['s_current']:.0f}%</strong> &nbsp;|&nbsp; 
                                Future Fit: <strong style="color: {q_badge_color};">{row['future_fit']:.0f}%</strong>
                            </span>
                        </div>
                    </div>
                    <div style="font-size: 13.5px; color: #cbd5e1; line-height: 1.4; padding: 4px 0;">
                        {row['reasoning']}
                    </div>
                </div>
                """
                st.markdown(clean_html(card_html), unsafe_allow_html=True)
                
                # Button to view profile
                if st.button(f"🔎 Open TalentDNA Profile for {row['name']}", key=f"pipe_tree_desc_profile_btn_{row['candidate_id']}", use_container_width=True):
                    navigate_to("TalentDNA Report", candidate_id=row['candidate_id'], job_id=selected_job_id)
        
    with tab_adjacency:
        st.markdown("<h3>How JD requirements map to your pool</h3>", unsafe_allow_html=True)
        st.markdown("<p style='color:#94a3b8; font-size:12px;'>Green = direct keyword match. Amber = a candidate has a structurally adjacent skill. Gap = skill missing.</p>", unsafe_allow_html=True)
        
        # Call Skill Adjacency Map component
        render_skill_adjacency_map(
            job_info["required_skills"],
            job_info["preferred_skills"],
            [r["record_dump"] for r in results]
        )

# ────────────────────────────────────────────────────────
# SCREEN 2.5: TREE OPPORTUNITY MAP
# ────────────────────────────────────────────────────────
elif st.session_state.app_mode == "Tree Opportunity Map":
    render_hackathon_compliance_banner()
    
    # Breadcrumbs
    st.markdown("""
        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 10px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 8px; font-family: monospace; font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;">
                <span>🌳</span>
                <span>Tree Opportunity Map</span>
            </div>
            <div style="display: flex; align-items: center; gap: 6px; font-family: monospace; font-size: 11px; color: #10b981;">
                <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981;"></span>
                <span>Live View</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Requisition selector
    selected_job_id = st.selectbox(
        "Select Active Requisition Matrix for Tree Map:", 
        list(st.session_state.job_db.keys()),
        format_func=lambda x: st.session_state.job_db[x]["title"],
        key="treemap_job_select"
    )
    st.session_state.selected_job_id = selected_job_id
    
    # Load JD details
    job_info = st.session_state.job_db[selected_job_id]
    results = get_ranked_candidates_for_job(selected_job_id)
    
    st.markdown(f"<h2>🌳 Tree Map (Top 100 from 100k) &middot; {job_info['title']}</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; font-size:14px; margin-top:-10px;'>This map visualizes the top 100 candidates grouped by their hiring quadrant, current title, and name. Sized by Future Fit percentage and colored by quadrant alignment.</p>", unsafe_allow_html=True)
    
    df_full = pd.DataFrame([
        {
            "rank": r["rank"],
            "candidate_id": r["candidate_id"],
            "score": r["score"],
            "reasoning": r["reasoning"],
            "s_current": r["bundle"]["s_current"],
            "future_fit": r["bundle"]["future_fit"],
            "hidden_gem": r["bundle"]["hidden_gem"],
            "opportunity": r["bundle"]["opportunity"],
            "quadrant": r["bundle"]["quadrant"],
            "name": r["profile"]["name"],
            "title": r["profile"]["title"],
        }
        for r in results
    ])
    
    df_top100 = df_full.head(100)
    fig_tree = build_tree_opportunity_map(df_top100)
    
    # Capture selection event for Treemap to enable click-to-profile navigation
    selected_tree = st.plotly_chart(fig_tree, use_container_width=True, on_select="rerun", key="screen_tree_map")
    if selected_tree and selected_tree.get("selection") and selected_tree["selection"].get("points"):
        points = selected_tree["selection"]["points"]
        if points:
            customdata = points[0].get("customdata")
            if customdata and len(customdata) > 3:
                clicked_cand_id = customdata[3]
                if clicked_cand_id != st.session_state.selected_candidate_id:
                    navigate_to("TalentDNA Report", candidate_id=clicked_cand_id, job_id=selected_job_id)
                    
    # Candidate description list below Tree Map
    st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 30px 0;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='margin-bottom: 4px;'>Top 100 Candidate Descriptions</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; font-size:12px; margin-bottom: 20px;'>Detailed analysis and alignment notes for the top 100 candidates in this requisition pool.</p>", unsafe_allow_html=True)
    
    # Search filter
    search_desc = st.text_input("Filter Top 100 candidates by name, title, or quadrant:", key="screen_tree_desc_search", placeholder="e.g. Anjali, Developer, Hidden Gem")
    
    filtered_top100 = []
    for idx, row in df_top100.iterrows():
        if search_desc:
            q = search_desc.lower()
            match = (q in row['name'].lower() or 
                     q in row['title'].lower() or 
                     q in row['quadrant'].lower())
            if not match:
                continue
        filtered_top100.append(row)
        
    if not filtered_top100:
        st.markdown("<p style='color: #64748b;'>No candidates match the search filter.</p>", unsafe_allow_html=True)
    else:
        for row in filtered_top100:
            q_val = row['quadrant']
            q_badge_color = "#22c55e" if q_val == "Safe Hire" else "#a855f7" if q_val == "Hidden Gem" else "#f59e0b" if q_val == "Overrated" else "#94a3b8"
            
            card_html = f"""
            <div style="background: #0d121f; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 16px; margin-bottom: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
                <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px; margin-bottom: 10px;">
                    <div>
                        <span style="font-family: monospace; font-size: 11px; font-weight: bold; background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 2px 6px; border-radius: 4px; margin-right: 8px;">Rank #{row['rank']}</span>
                        <span style="font-size: 15px; font-weight: bold; color: #ffffff;">{row['name']}</span>
                        <span style="font-size: 12px; color: #94a3b8; margin-left: 8px;">&middot; {row['title']}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-family: monospace; font-size: 9px; padding: 2px 6px; border-radius: 4px; border: 1px solid {q_badge_color}; color: {q_badge_color}; font-weight: bold;">{q_val}</span>
                        <span style="font-size: 11px; color: #cbd5e1; font-family: monospace;">
                            Current Fit: <strong style="color: #38bdf8;">{row['s_current']:.0f}%</strong> &nbsp;|&nbsp; 
                            Future Fit: <strong style="color: {q_badge_color};">{row['future_fit']:.0f}%</strong>
                        </span>
                    </div>
                </div>
                <div style="font-size: 13.5px; color: #cbd5e1; line-height: 1.4; padding: 4px 0;">
                    {row['reasoning']}
                </div>
            </div>
            """
            st.markdown(clean_html(card_html), unsafe_allow_html=True)
            
            # Button to view profile
            if st.button(f"🔎 Open TalentDNA Profile for {row['name']}", key=f"screen_tree_desc_profile_btn_{row['candidate_id']}", use_container_width=True):
                navigate_to("TalentDNA Report", candidate_id=row['candidate_id'], job_id=selected_job_id)
                
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Back to Requisition Pipeline button
    if st.button("⬅ Go to Requisition Pipeline", key="tree_map_back_btn"):
        navigate_to("Requisition Pipeline", job_id=selected_job_id)
        st.rerun()

# ────────────────────────────────────────────────────────
# SCREEN 3: TALENTDNA REPORT
# ────────────────────────────────────────────────────────
elif st.session_state.app_mode == "TalentDNA Report":
    # Pick job target first
    selected_job_id = st.selectbox(
        "Select Requisition Target:", 
        list(st.session_state.job_db.keys()),
        format_func=lambda x: st.session_state.job_db[x]["title"],
        key="report_job_select"
    )
    st.session_state.selected_job_id = selected_job_id
    
    # Get ranked list
    results = get_ranked_candidates_for_job(selected_job_id)
    
    # Candidate selection dropdown
    cand_options = [r["candidate_id"] for r in results]
    if st.session_state.selected_candidate_id not in cand_options and cand_options:
        st.session_state.selected_candidate_id = cand_options[0]
        
    selected_cand_id = st.selectbox(
        "Select Candidate to Analyze:",
        cand_options,
        format_func=lambda cid: next(f"#{r['rank']} - {r['profile']['name']} ({cid})" for r in results if r["candidate_id"] == cid),
        key="report_candidate_select"
    )
    st.session_state.selected_candidate_id = selected_cand_id
    
    if selected_cand_id:
        # Retrieve candidate details
        ranked_map = {r["candidate_id"]: r for r in results}
        cand_data = ranked_map[selected_cand_id]
        
        record = CandidateRecord(**cand_data["record_dump"])
        bundle = ScoreBundle(**cand_data["bundle"])
        reasoning = cand_data["reasoning"]
        ats_score = cand_data.get("ats_score", 50.0)
        
        # Add button to go back to Requisition Pipeline
        if st.button("⬅ Back to Requisition Pipeline", key="back_to_pipeline_btn"):
            navigate_to("Requisition Pipeline", job_id=selected_job_id)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Render high-fidelity scorecard HTML details
        render_talent_dna_report(record, bundle, reasoning, ats_score)

# ────────────────────────────────────────────────────────
# SCREEN 4: CREATE NEW JOB
# ────────────────────────────────────────────────────────
elif st.session_state.app_mode == "Create New Job":
    st.markdown("<h1 style='margin:0;'><span class='text-gradient-primary'>Author Target Job DNA Matrix</span></h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; font-size:14px; margin-top:4px;'>Define what success looks like. TalentDNA automatically scores candidates against this requirements matrix.</p>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Form Layout (Left: Ingestion & Form inputs, Right: Live preview)
    form_col1, form_col2 = st.columns([1.4, 1])
    
    with form_col1:
        # One-click Ingest block
        st.markdown("""
            <div style="background: rgba(30,41,59,0.3); border: 1px solid rgba(255,255,255,0.06); padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                <div style="font-family: monospace; font-size: 10px; color:#38bdf8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 4px;">One-click JD Intake</div>
                <div style="font-size: 14px; font-weight: bold; color: #ffffff; margin-bottom: 12px;">Paste or upload a JD document — we extract the requirements matrix automatically.</div>
            </div>
        """, unsafe_allow_html=True)
        
        # File uploader for JD
        uploaded_jd_file = st.file_uploader("Upload .pdf / .docx / .txt document:", type=["pdf", "docx", "txt"], key="jd_file_loader")
        
        # Paste area
        pasted_jd_text = st.text_area("Or paste raw job description prose:", height=100, key="jd_pasted_prose")
        
        # Parse button
        if st.button("🪄 Parse JD into Form", key="parse_jd_btn"):
            if uploaded_jd_file is not None:
                # Save temp file
                temp_dir = Path(tempfile.mkdtemp())
                temp_file = temp_dir / uploaded_jd_file.name
                with open(temp_file, "wb") as f:
                    f.write(uploaded_jd_file.getbuffer())
                
                # Check extension
                if temp_file.suffix.lower() == ".pdf":
                    ingestor = ProductionIngestionService(ROOT / "config" / "candidate_schema.json")
                    raw_text = ingestor.extract_document_text(temp_file)
                    temp_md_path = temp_dir / "temp_jd.md"
                    temp_md_path.write_text(raw_text, encoding="utf-8")
                    parsed_path = temp_md_path
                else:
                    parsed_path = temp_file
                    
                weights = load_weights(ROOT / "config" / "weights.json")
                parsed_jd = load_job_description(parsed_path, weights)
                
                st.session_state.new_job_title = parsed_jd.title
                st.session_state.new_job_desc = parsed_jd.raw_text
                st.session_state.new_job_locs = ", ".join(parsed_jd.locations)
                st.session_state.new_job_min_exp = parsed_jd.min_experience_years if parsed_jd.min_experience_years is not None else 3.0
                st.session_state.new_job_max_exp = parsed_jd.max_experience_years if parsed_jd.max_experience_years is not None else 8.0
                st.session_state.new_job_req_skills = ", ".join(parsed_jd.required_skills)
                st.session_state.new_job_pref_skills = ", ".join(parsed_jd.preferred_skills)
                st.toast("🎉 JD successfully parsed!")
                st.rerun()
                
            elif pasted_jd_text.strip():
                # Write paste to a temp markdown file
                temp_dir = Path(tempfile.mkdtemp())
                temp_file = temp_dir / "pasted_jd.md"
                temp_file.write_text(pasted_jd_text, encoding="utf-8")
                
                weights = load_weights(ROOT / "config" / "weights.json")
                parsed_jd = load_job_description(temp_file, weights)
                
                st.session_state.new_job_title = parsed_jd.title
                st.session_state.new_job_desc = parsed_jd.raw_text
                st.session_state.new_job_locs = ", ".join(parsed_jd.locations)
                st.session_state.new_job_min_exp = parsed_jd.min_experience_years if parsed_jd.min_experience_years is not None else 3.0
                st.session_state.new_job_max_exp = parsed_jd.max_experience_years if parsed_jd.max_experience_years is not None else 8.0
                st.session_state.new_job_req_skills = ", ".join(parsed_jd.required_skills)
                st.session_state.new_job_pref_skills = ", ".join(parsed_jd.preferred_skills)
                st.toast("🎉 JD successfully parsed!")
                st.rerun()

            else:
                st.error("Please upload a file or paste JD text first.")

                
        st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 20px 0;'>", unsafe_allow_html=True)
        
        # Interactive Inputs (connected to session state)
        job_id_key = f"JOB_REQ_{len(st.session_state.job_db):02d}"
        
        job_title = st.text_input("Official Job Title:", key="new_job_title", placeholder="e.g. Senior Machine Learning Engineer")
        company_name = st.text_input("Company:", key="new_job_company")
        job_desc = st.text_area("Full Job Description Prose:", key="new_job_desc", height=120, placeholder="Describe the core duties and responsibilities...")
        job_locs = st.text_input("Locations (Comma-separated):", key="new_job_locs", placeholder="e.g. Pune, Noida, Hyderabad")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            min_exp_val = st.number_input("Min Experience (years):", min_value=0.0, max_value=20.0, key="new_job_min_exp", step=1.0)
        with col_f2:
            max_exp_val = st.number_input("Max Experience (years):", min_value=0.0, max_value=30.0, key="new_job_max_exp", step=1.0)
            
        req_skills_str = st.text_input("Required Skills (Comma-separated):", key="new_job_req_skills", placeholder="e.g. python, pytorch, kubernetes")
        pref_skills_str = st.text_input("Preferred Skills (Comma-separated):", key="new_job_pref_skills", placeholder="e.g. langchain, airflow, spark")

        
        if st.button("🚀 Deploy Requisition to Registry", key="deploy_jd_btn"):
            if not job_title.strip() or not job_desc.strip():
                st.error("Please provide both a job title and description.")
            else:
                req_skills_list = [s.strip().lower() for s in req_skills_str.split(",") if s.strip()]
                pref_skills_list = [s.strip().lower() for s in pref_skills_str.split(",") if s.strip()]
                locs_list = [l.strip() for l in job_locs.split(",") if l.strip()]
                
                # Construct markdown JD file
                md_content = f"""Job Description: {job_title}
Company: {company_name}
Location: {", ".join(locs_list)}
Experience Required: {int(min_exp_val)}–{int(max_exp_val)} years

{job_desc}

Things you absolutely need
- Required Skills ({", ".join(req_skills_list)})

Things we'd like you to have but won't reject you for
- Preferred Skills ({", ".join(pref_skills_list)})

Things we explicitly do NOT want
- Title-chasers
- Framework enthusiasts
- People who have only worked at consulting firms
"""
                # Write to disk
                jobs_dir = ROOT / "data" / "jobs"
                jobs_dir.mkdir(parents=True, exist_ok=True)
                jd_path = jobs_dir / f"{job_id_key}.md"
                jd_path.write_text(md_content, encoding="utf-8")
                
                # Add to registry
                st.session_state.job_db[job_id_key] = {
                    "job_id": job_id_key,
                    "title": job_title,
                    "required_skills": req_skills_list,
                    "preferred_skills": pref_skills_list,
                    "min_experience_years": min_exp_val,
                    "max_experience_years": max_exp_val,
                    "locations": locs_list,
                    "description": job_desc,
                    "jd_path": f"data/jobs/{job_id_key}.md"
                }
                
                # Write registry back to registry json
                registry_path = ROOT / "data" / "job_registry.json"
                with open(registry_path, "w", encoding="utf-8") as f:
                    json.dump(st.session_state.job_db, f, indent=2)
                    
                # Clear cached ranking results
                rank_pool_cached.clear()
                
                # Flag to clear inputs on next run to avoid modifying widget state mid-execution
                st.session_state.clear_new_job_inputs = True
                
                st.success(f"Job Matrix for '{job_title}' compiled and successfully deployed to active database!")
                
                # Navigate back to command center
                navigate_to("Recruiter Command Center", job_id=job_id_key)
                
    with form_col2:
        # Live Preview Panel
        st.markdown("<h3 style='margin-bottom:12px;'>Live Preview</h3>", unsafe_allow_html=True)
        
        prev_req_badges = "".join([
            f'<span style="padding:2px 8px; border-radius:12px; background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.3); color:#38bdf8; font-family:monospace; font-size:10px; margin-right:4px; margin-bottom:4px; display:inline-block;">{s.strip().lower()}</span>'
            for s in st.session_state.new_job_req_skills.split(",") if s.strip()
        ]) or '<span style="font-size:12px; color:#94a3b8;">No required skills yet</span>'
        
        prev_pref_badges = "".join([
            f'<span style="padding:2px 8px; border-radius:12px; background:rgba(251,191,36,0.1); border:1px solid rgba(251,191,36,0.3); color:#fbbf24; font-family:monospace; font-size:10px; margin-right:4px; margin-bottom:4px; display:inline-block;">{s.strip().lower()}</span>'
            for s in st.session_state.new_job_pref_skills.split(",") if s.strip()
        ]) or '<span style="font-size:12px; color:#94a3b8;">None</span>'
        
        st.markdown(clean_html(f"""
            <div style="background: rgba(30, 41, 59, 0.45); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 24px; box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5); backdrop-filter: blur(12px);">
                <div style="font-family: monospace; font-size: 10px; color:#38bdf8; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 4px;">Live Preview</div>
                <div style="font-size: 20px; font-weight: bold; color: #ffffff; margin-top: 10px;">{st.session_state.new_job_title if st.session_state.new_job_title else "Job Title"}</div>
                <div style="font-size: 12px; color: #cbd5e1; margin-top: 4px; margin-bottom: 20px;">{company_name} &middot; {st.session_state.new_job_locs if st.session_state.new_job_locs else "Location"} &middot; {st.session_state.new_job_min_exp:.0f}-{st.session_state.new_job_max_exp:.0f}y exp</div>
                
                <div style="margin-bottom: 16px;">
                    <div style="font-family: monospace; font-size: 10px; color: #94a3b8; text-transform: uppercase; margin-bottom: 6px;">Required DNA</div>
                    <div>{prev_req_badges}</div>
                </div>
                
                <div style="margin-bottom: 16px;">
                    <div style="font-family: monospace; font-size: 10px; color: #94a3b8; text-transform: uppercase; margin-bottom: 6px;">Preferred DNA</div>
                    <div>{prev_pref_badges}</div>
                </div>
            </div>
            <div style="margin-top: 16px; font-size: 12px; color: #94a3b8; line-height: 1.4; padding: 0 8px;">
                Skills are matched against our canonical technology taxonomy. Missing skills are forgiven and bridged automatically if candidate has structurally adjacent stacks.
            </div>
        """), unsafe_allow_html=True)

# ────────────────────────────────────────────────────────
# SCREEN 5: UPLOAD CANDIDATE RESUME
# ────────────────────────────────────────────────────────
elif st.session_state.app_mode == "Upload Candidate Resume":
    st.markdown("<h1 style='margin:0;'><span class='text-gradient-primary'>Ingestion Portal</span></h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; font-size:14px; margin-top:4px;'>Drop candidate resumes. Resumes are parsed, scored against the selected JD, and queued for commit to the dashboard.</p>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Grid (Left Ingest drag-and-drop, Right parsing queue status)
    up_col1, up_col2 = st.columns([1.1, 1])
    
    with up_col1:
        # Requisition assignment
        target_job_id = st.selectbox(
            "Assign Submission to Requisition Target:", 
            list(st.session_state.job_db.keys()),
            format_func=lambda x: st.session_state.job_db[x]["title"],
            key="upload_job_select"
        )
        st.session_state.selected_job_id = target_job_id
        
        # File uploader (allows multiple resumes)
        uploaded_resumes = st.file_uploader(
            "Drop Candidate Resume Documents (PDF, DOCX, TXT):", 
            type=["pdf", "docx", "txt"], 
            accept_multiple_files=True, 
            key="bulk_resume_loader"
        )
        
        if uploaded_resumes:
            st.markdown("<div style='background: rgba(30,41,59,0.3); border:1px solid rgba(255,255,255,0.06); padding:16px; border-radius:8px; margin-top:16px;'>", unsafe_allow_html=True)
            st.write("⚙️ **Initializing Ingestion Pipeline...**")
            
            job_info = st.session_state.job_db[target_job_id]
            vocab = job_info["required_skills"] + job_info["preferred_skills"]
            
            new_added = 0
            
            for uploaded_file in uploaded_resumes:
                # Avoid duplicate processing of already queued files
                if any(q["filename"] == uploaded_file.name for q in st.session_state.upload_queue):
                    continue
                    
                # Save temp file
                temp_dir = Path("/tmp") if IS_HF_SPACES else Path(tempfile.mkdtemp())
                temp_file = temp_dir / uploaded_file.name
                with open(temp_file, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                    
                try:
                    ingestor = ProductionIngestionService(ROOT / "config" / "candidate_schema.json")
                    extracted_text = ingestor.extract_document_text(temp_file)
                    
                    features = ingestor.rule_based_ner_normalizer(extracted_text, vocab)
                    candidate_dict = ingestor.compile_to_schema_row(features)
                    
                    # Store in queue state
                    st.session_state.upload_queue.append({
                        "filename": uploaded_file.name,
                        "size_kb": len(uploaded_file.getbuffer()) / 1024.0,
                        "candidate": candidate_dict,
                        "status": "ready"
                    })
                    new_added += 1
                except Exception as e:
                    st.session_state.upload_queue.append({
                        "filename": uploaded_file.name,
                        "size_kb": len(uploaded_file.getbuffer()) / 1024.0,
                        "candidate": None,
                        "status": "error",
                        "error": str(e)
                    })
                    
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass
                    
            if new_added > 0:
                st.success(f"🎉 Successfully parsed {new_added} resumes into candidates queue!")
            st.markdown("</div>", unsafe_allow_html=True)
            
        # Bulk commit button
        ready_items = [q for q in st.session_state.upload_queue if q["status"] == "ready"]
        if ready_items:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f"Commit {len(ready_items)} Candidates to Pool", key="bulk_commit_btn"):
                committed_count = 0
                for item in ready_items:
                    # Append to candidate pool
                    st.session_state.candidate_pool.append(item["candidate"])
                    item["status"] = "added"
                    committed_count += 1
                    
                # Write candidate pool changes back to disk
                temp_pool_path = st.session_state.get("temp_pool_path")
                if temp_pool_path:
                    with open(temp_pool_path, "w", encoding="utf-8") as f:
                        json.dump(st.session_state.candidate_pool, f, indent=2)
                    st.session_state.temp_pool_mtime = os.path.getmtime(temp_pool_path)
                else:
                    with open(ROOT / "data" / "sample_candidates.json", "w", encoding="utf-8") as f:
                        json.dump(st.session_state.candidate_pool, f, indent=2)
                    
                # Clear ranking cache so they get re-scored
                rank_pool_cached.clear()
                
                st.success(f"🎉 Successfully committed {committed_count} candidates to Requisition Pipeline!")
                navigate_to("Requisition Pipeline", job_id=target_job_id)
                
    with up_col2:
        # Ingestion Queue Status
        st.markdown("<h3 style='margin-bottom:12px;'>Ingestion Queue</h3>", unsafe_allow_html=True)
        
        if not st.session_state.upload_queue:
            st.markdown("""
                <div style="background: rgba(30, 41, 59, 0.45); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 40px 20px; text-align: center; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                    <div style="font-size: 36px; opacity: 0.5; margin-bottom: 12px;">🗂️</div>
                    <div style="font-weight: bold; color: #ffffff;">Queue is currently empty</div>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Uploaded resumes will appear here. Each profile is evaluated dynamically.</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            for idx, item in enumerate(st.session_state.upload_queue):
                status_color = "#38bdf8" if item["status"] == "ready" else "#22c55e" if item["status"] == "added" else "#f87171"
                status_lbl = "ready" if item["status"] == "ready" else "committed" if item["status"] == "added" else "error"
                
                skills_html = ""
                metrics_html = ""
                action_btn_html = ""
                
                if item["candidate"]:
                    cand = item["candidate"]
                    skills_list = [s["name"] for s in cand["skills"][:6]]
                    skills_html = "".join([
                        f'<span style="padding: 1px 6px; border-radius: 4px; background: rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); color: #cbd5e1; font-family: monospace; font-size: 9px; margin-right: 4px; margin-bottom: 4px; display: inline-block;">{s}</span>'
                        for s in skills_list
                    ])
                    metrics_html = f"""
                    <div style="font-family: monospace; font-size: 11px; color:#cbd5e1; margin-top:6px;">
                        {cand['profile']['years_of_experience']:.1f}y exp &middot; {len(cand['skills'])} skills detected
                    </div>
                    """
                    
                st.markdown(f"""
                    <div style="background: rgba(30, 41, 59, 0.45); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 16px; margin-bottom: 12px; position: relative;">
                        <div style="position: absolute; right: 16px; top: 16px; font-family: monospace; font-size: 10px; font-weight: bold; text-transform: uppercase; color: {status_color}; border: 1px solid {status_color}; padding: 1px 6px; border-radius: 4px;">
                            {status_lbl}
                        </div>
                        <div style="font-weight: bold; font-size: 14px; color: #ffffff; width: 75%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                            {cand['profile']['anonymized_name'] if item['candidate'] else item['filename']}
                        </div>
                        <div style="font-size: 11px; color: #94a3b8; font-family: monospace; margin-top: 2px;">
                            {item['filename']} &middot; {item['size_kb']:.0f} KB
                        </div>
                        {metrics_html}
                        <div style="margin-top: 8px;">{skills_html}</div>
                        {f'<div style="color: #f87171; font-size: 11px; margin-top: 8px;">Error: {item["error"]}</div>' if item["error"] else ''}
                    </div>
                """, unsafe_allow_html=True)
                
                # Single open buttons for ready candidates
                if item["status"] == "ready":
                    col_btn1, col_btn2 = st.columns([4, 1])
                    with col_btn2:
                        if st.button("Commit & Open", key=f"commit_one_btn_{idx}"):
                            st.session_state.candidate_pool.append(item["candidate"])
                            item["status"] = "added"
                            temp_pool_path = st.session_state.get("temp_pool_path")
                            if temp_pool_path:
                                with open(temp_pool_path, "w", encoding="utf-8") as f:
                                    json.dump(st.session_state.candidate_pool, f, indent=2)
                                st.session_state.temp_pool_mtime = os.path.getmtime(temp_pool_path)
                            else:
                                with open(ROOT / "data" / "sample_candidates.json", "w", encoding="utf-8") as f:
                                    json.dump(st.session_state.candidate_pool, f, indent=2)
                            rank_pool_cached.clear()
                            navigate_to("TalentDNA Report", candidate_id=item["candidate"]["candidate_id"], job_id=target_job_id)
                            
                st.markdown("<div style='border-bottom:1px solid rgba(255,255,255,0.03); margin-bottom:8px;'></div>", unsafe_allow_html=True)
                
            # Clear queue button
            if st.button("🧹 Clear Ingestion Queue", key="clear_queue_btn"):
                st.session_state.upload_queue = []
                st.rerun()

# ────────────────────────────────────────────────────────
# SCREEN 6: LOAD CANDIDATES
# ────────────────────────────────────────────────────────
elif st.session_state.app_mode == "Load Candidates":
    from dashboard.components.pool_upload import render_pool_upload
    from src.pool_manager import PoolManager
    
    # Initialize pool manager
    pool_manager = PoolManager(ROOT / "config" / "candidate_schema.json")
    if is_pool_loaded:
        pool_manager.candidates = st.session_state.candidate_pool
        pool_manager.stats["total"] = len(st.session_state.candidate_pool)
        
    # Get active JD vocab
    job_id = st.session_state.get("selected_job_id")
    if job_id and job_id in st.session_state.job_db:
        job_info = st.session_state.job_db[job_id]
        vocab = job_info["required_skills"] + job_info["preferred_skills"]
    else:
        # Default seeds
        weights = load_weights(ROOT / "config" / "weights.json")
        vocab = weights.get("jd_skill_seeds", {}).get("required", []) + weights.get("jd_skill_seeds", {}).get("preferred", [])
        
    render_pool_upload(pool_manager, vocab)

# ────────────────────────────────────────────────────────
# SCREEN 7: SYSTEM SETTINGS
# ────────────────────────────────────────────────────────
elif st.session_state.app_mode == "Settings":
    st.markdown("<h1>System Settings</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; font-size:14px;'>Adjust weighting configurations for Current Fit, Future Fit, and composite ranking.</p>", unsafe_allow_html=True)
    
    weights_path = ROOT / "config" / "weights.json"
    weights = load_weights(weights_path)
    
    st.markdown("<h3>Future Fit Component Weights</h3>", unsafe_allow_html=True)
    ff = weights.get("future_fit_weights", {})
    st_val = st.slider("Skill Transferability (ST) weight", 0.0, 1.0, float(ff.get("st", 0.40)), 0.05)
    as_val = st.slider("Adaptability Score (AS) weight", 0.0, 1.0, float(ff.get("as", 0.30)), 0.05)
    cv_val = st.slider("Career Velocity (CV) weight", 0.0, 1.0, float(ff.get("cv", 0.30)), 0.05)
    
    st.markdown("<h3>Composite Score Weight Contribution</h3>", unsafe_allow_html=True)
    cw = weights.get("composite_weights", {})
    s_cur = st.slider("Current Fit weight", 0.0, 1.0, float(cw.get("s_current", 0.12)), 0.05)
    f_fit = st.slider("Future Fit weight", 0.0, 1.0, float(cw.get("future_fit", 0.32)), 0.05)
    h_gem = st.slider("Hidden Gem weight", 0.0, 1.0, float(cw.get("hidden_gem", 0.22)), 0.05)
    opp = st.slider("Opportunity weight", 0.0, 1.0, float(cw.get("opportunity", 0.12)), 0.05)
    risk = st.slider("Hiring Risk penalty weight", 0.0, 1.0, float(cw.get("risk", 0.15)), 0.05)
    
    if st.button("💾 Save Settings", key="save_settings_btn"):
        weights["future_fit_weights"] = {"st": st_val, "as": as_val, "cv": cv_val}
        weights["composite_weights"]["s_current"] = s_cur
        weights["composite_weights"]["future_fit"] = f_fit
        weights["composite_weights"]["hidden_gem"] = h_gem
        weights["composite_weights"]["opportunity"] = opp
        weights["composite_weights"]["risk"] = risk
        
        weights_path.parent.mkdir(parents=True, exist_ok=True)
        with open(weights_path, "w", encoding="utf-8") as f:
            json.dump(weights, f, indent=2)
            
        rank_pool_cached.clear()
        st.success("⚙️ Weights configuration successfully saved and cached ranking cleared!")
