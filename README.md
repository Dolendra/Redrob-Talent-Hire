<<<<<<< HEAD
# TalentDNA — Redrob Hackathon v4

AI recruitment ranker that scores **Current Fit** vs **Future Fit**, surfaces **Hidden Gems**, and explains why keyword ATS would fail.

## Quick start

Use a **virtual environment** so dependencies (especially PyTorch + sentence-transformers) stay isolated from your system Python and match the versions in `requirements.txt`.

**Windows (PowerShell):**

```powershell
cd D:\Redrob-Talent-Hire
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

After activation, your prompt should show `(.venv)`. All commands below assume the venv is active.

To deactivate later: `deactivate`

```powershell
# Place bundle data (not in git):
#   data/candidates.jsonl.gz  →  gunzip -k data/candidates.jsonl.gz
#   copy to repo root for reproduce_command:
copy data\candidates.jsonl candidates.jsonl

# One-time offline prep (network allowed here):
python scripts/precompute_embeddings.py --candidates data/candidates.jsonl --save-model

# Rank top 100 (offline, no network):
python rank.py --candidates candidates.jsonl --out team_xxx.csv --validate

# Dashboard (sample 50 candidates):
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
3. Fill [`submission_metadata.yaml`](submission_metadata.yaml) and upload with CSV

**Reproduce command:** `python rank.py --candidates ./candidates.jsonl --out ./submission.csv`

## Hosting strategy

| Artifact | Where |
|----------|-------|
| Full 100K rank | Local CPU only |
| HF Space demo | `data/sample_candidates.json` (50 rows) |
| Embeddings cache | `data/embeddings/skill_vectors.npz` (commit for Space) |

## Demo narrative (PPT scripts)

### Slide 1 — The problem
> "Traditional ATS ranks on keywords. Our JD asks for embeddings, vector DBs, and ranking eval — but the best hire might be a backend engineer who built recommendation systems without listing Pinecone. Keyword filters bury them."

### Slide 2 — TalentDNA approach
> "We compute Current Fit (semantic skill match) and Future Fit (transferability + adaptability + career velocity). Hidden Gems score high on future potential with low keyword overlap — exactly where ATS fails."

### Slide 3 — Live demo
> Open the Streamlit dashboard. Click a Hidden Gem quadrant dot. Show the contrast card: ATS failed on missing keywords; TalentDNA selected on adjacent stack and timeline signals.

### Sample decision card (CLI output after ranking)

```
+--------------------------------------------------------------+
| TALENTDNA DECISION CARD  Rank #1    CAND_00XXXXXX           |
+--------------------------------------------------------------+
| Ira Vora                     | Backend Engineer              |
+--------------------------------------------------------------+
| WHY ATS FAILED              | WHY TALENTDNA SELECTED       |
| Current Fit:  42.0%           | Future Fit:   71.0%          |
| Missing: embeddings, FAISS   | Hidden Gem:  18.5           |
| Quadrant: Hidden Gem         | Onboarding: ~4-6 weeks       |
+--------------------------------------------------------------+
```

Run `python rank.py ...` to print the top 3 cards automatically.

## Project layout

```
rank.py                    # Public CLI
validate_submission.py     # Organizer CSV validator
src/                       # parser, features, scoring, explainability, main
dashboard/                 # Streamlit + Plotly Opportunity Map
scripts/precompute_embeddings.py
config/weights.json
data/job_description.md
```
=======
---
title: Redrob Talent Hire
emoji: 🚀
colorFrom: red
colorTo: red
sdk: docker
app_port: 8501
tags:
- streamlit
pinned: false
short_description: Streamlit template space
---

# Welcome to Streamlit!

Edit `/src/streamlit_app.py` to customize this app to your heart's desire. :heart:

If you have any questions, checkout our [documentation](https://docs.streamlit.io) and [community
forums](https://discuss.streamlit.io).
>>>>>>> 150caada6feffb818d2b7c82de956b2d81ce4908
