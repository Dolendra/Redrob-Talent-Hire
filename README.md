---
title: Redrob-Talent-Hire
emoji: 🧬
colorFrom: blue
colorTo: purple
sdk: streamlit
sdk_version: "1.28.0"
app_file: app.py
pinned: false
---

# Redrob-Talent-Hire — Redrob Hackathon v4

AI recruitment ranker that scores **Current Fit** vs **Future Fit**, surfaces **Hidden Gems**, and explains why keyword ATS would fail.

**Live demo:** This HuggingFace Space runs the Streamlit dashboard on `data/sample_candidates.json` (50 candidates). Full 100K ranking runs locally via `rank.py`.

## Quick start (local)

Use a **virtual environment** so dependencies stay isolated:

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

```powershell
# One-time offline prep (network allowed):
python scripts/precompute_embeddings.py --candidates data/candidates.jsonl --save-model

# Rank top 100 (offline, no network):
python rank.py --candidates candidates.jsonl --out team_xxx.csv --validate

# Dashboard locally:
streamlit run dashboard/app.py
```

## Formulas

| Metric | Formula |
|--------|---------|
| **Current Fit** | Avg max cosine(JD skill, candidate skill) × 100 via `all-MiniLM-L6-v2` |
| **Future Fit** | `0.40·ST + 0.30·AS + 0.30·CV` |
| **Hidden Gem** | `FutureFit × Confidence × max(0, FutureFit − CurrentFit) / 100` |
| **Opportunity** | `FutureFit × recruiter_response_rate × interview_completion_rate / 100` |

## Architecture

- **Two-pass streaming** over JSONL/`.gz` — never loads 100K into RAM
- **Pass 1:** pool min/max for Adaptability & Career Velocity
- **Pass 2:** score + `heapq` top-100 with tie-break by ascending `candidate_id`
- **Reasoning:** fact-slot contrast cards (no LLM in `rank.py`)

## Submission

1. Rename CSV to your registered ID: `team_xxx.csv`
2. Validate: `python validate_submission.py team_xxx.csv`
3. Upload with [`submission_metadata.yaml`](submission_metadata.yaml)

**Reproduce command:** `python rank.py --candidates ./candidates.jsonl --out ./submission.csv`

## Project layout

```
app.py                     # HF Space entrypoint → dashboard/app.py
rank.py                    # Public CLI
validate_submission.py     # Organizer CSV validator
src/                       # parser, features, scoring, explainability, main
dashboard/                 # Streamlit + Plotly Opportunity Map
scripts/precompute_embeddings.py
config/weights.json
data/job_description.md
data/sample_candidates.json
data/embeddings/skill_vectors.npz
```

## Push to GitHub and HuggingFace Space

This repo uses **two remotes** (they are different destinations):

| Remote | URL | Purpose |
|--------|-----|---------|
| `origin` | `github.com/Dolendra/Redrob-Talent-Hire` | Hackathon code repo |
| `hf` | `huggingface.co/spaces/Dolendra/Redrob-Talent-Hire` | Live Streamlit demo |

```powershell
# Push to BOTH after each change:
.\scripts\push-both.ps1 "describe your change"

# Or manually:
git add -A
git commit -m "your message"
git push origin main    # GitHub
git push hf main        # HuggingFace Space
```

If `git push origin` only updated the Space before, that was because `origin` pointed at HuggingFace. It is now fixed to GitHub.
