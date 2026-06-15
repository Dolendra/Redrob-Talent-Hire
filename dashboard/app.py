"""Redrob-Talent-Hire Streamlit dashboard — Talent Opportunity Map + contrast cards."""

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
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dashboard.components.candidate_card import render_contrast_card
from dashboard.components.opportunity_map import build_opportunity_map
from src.main import run_ranking
from src.models import RankedCandidate
from src.parser import load_job_description, load_weights

st.set_page_config(page_title="Redrob-Talent-Hire", layout="wide")

RESULTS_PATH = ROOT / "output" / "results.json"
SAMPLE_PATH = ROOT / "data" / "sample_candidates.json"
JD_PATH = ROOT / "data" / "job_description.md"


def ranked_to_df(ranked: list[RankedCandidate]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "rank": r.rank,
                "candidate_id": r.candidate_id,
                "score": r.score,
                "reasoning": r.reasoning,
                "s_current": r.bundle.s_current,
                "future_fit": r.bundle.future_fit,
                "hidden_gem": r.bundle.hidden_gem,
                "opportunity": r.bundle.opportunity,
                "quadrant": r.bundle.quadrant,
                "name": r.record.profile.anonymized_name,
                "title": r.record.profile.current_title,
            }
            for r in ranked
        ]
    )


@st.cache_data(show_spinner="Ranking candidates…")
def rank_pool(candidates_path: str, top_n: int) -> list[dict]:
    out_csv = Path(tempfile.mkdtemp()) / "submission.csv"
    ranked = run_ranking(
        candidates_path=Path(candidates_path),
        out_path=out_csv,
        jd_path=JD_PATH,
        top_n=top_n,
        analytics_path=None,
        results_path=None,
        validate_ids=None,
        offline=True,
    )
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
            },
            "record_dump": r.record.model_dump(),
        }
        for r in ranked
    ]


def load_precomputed_rows() -> list[dict] | None:
    if not RESULTS_PATH.exists():
        return None
    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    return data.get("candidates", [])


def main() -> None:
    job = load_job_description(JD_PATH, load_weights(ROOT / "config" / "weights.json"))
    st.title("Redrob-Talent-Hire")
    st.caption(f"Target role: **{job.title}**")

    pre = load_precomputed_rows()
    use_pre = pre and st.sidebar.checkbox("Use output/results.json", value=False)

    uploaded = st.sidebar.file_uploader("Upload JSONL (≤100 lines)", type=["jsonl"])

    if uploaded is not None:
        tmp = Path(tempfile.mkdtemp()) / "upload.jsonl"
        raw_bytes = uploaded.read()
        try:
            content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = raw_bytes.decode("latin-1")
        
        lines = [line for line in content.strip().splitlines() if line.strip()]
        n = len(lines)
        if n > 2000:
            st.sidebar.warning(f"Sandbox limit: 2000 candidates. The uploaded file has been truncated from {n} to the first 2000 candidates.")
            lines = lines[:2000]
            n = 2000
        
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        serialized = rank_pool(str(tmp), min(2000, n))
    elif use_pre and pre:
        df = pd.DataFrame(
            [
                {
                    "rank": c["rank"],
                    "candidate_id": c["candidate_id"],
                    "score": c["score"],
                    "reasoning": c["reasoning"],
                    "s_current": c["metrics"]["s_current"],
                    "future_fit": c["metrics"]["future_fit"],
                    "hidden_gem": c["metrics"]["hidden_gem"],
                    "opportunity": c["metrics"]["opportunity"],
                    "quadrant": c["metrics"]["quadrant"],
                    "name": c["profile"]["name"],
                    "title": c["profile"]["title"],
                }
                for c in pre
            ]
        )
        st.success(f"Loaded {len(df)} from results.json")
        _render(df, None)
        return
    elif SAMPLE_PATH.exists():
        serialized = rank_pool(str(SAMPLE_PATH), 50)
    else:
        st.error("Missing data/sample_candidates.json")
        st.stop()

    ranked_map = {s["candidate_id"]: s for s in serialized}
    df = pd.DataFrame(
        [
            {
                "rank": s["rank"],
                "candidate_id": s["candidate_id"],
                "score": s["score"],
                "reasoning": s["reasoning"],
                "s_current": s["bundle"]["s_current"],
                "future_fit": s["bundle"]["future_fit"],
                "hidden_gem": s["bundle"]["hidden_gem"],
                "opportunity": s["bundle"]["opportunity"],
                "quadrant": s["bundle"]["quadrant"],
                "name": s["profile"]["name"],
                "title": s["profile"]["title"],
            }
            for s in serialized
        ]
    )
    _render(df, ranked_map)


def _render(df: pd.DataFrame, ranked_map: dict | None) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ranked", len(df))
    c2.metric("Hidden Gems", int((df["quadrant"] == "Hidden Gem").sum()))
    c3.metric("Avg Future Fit", f"{df['future_fit'].mean():.0f}%")
    c4.metric("Avg Current Fit", f"{df['s_current'].mean():.0f}%")

    selected = st.selectbox(
        "Candidate",
        df.sort_values("rank")["candidate_id"],
        format_func=lambda cid: f"#{df.loc[df['candidate_id']==cid,'rank'].iloc[0]} {cid}",
    )
    st.plotly_chart(build_opportunity_map(df, selected), use_container_width=True)

    row = df[df["candidate_id"] == selected].iloc[0]
    if ranked_map and selected in ranked_map:
        from src.models import CandidateRecord, ScoreBundle

        s = ranked_map[selected]
        record = CandidateRecord(**s["record_dump"])
        bundle = ScoreBundle(**s["bundle"])
        render_contrast_card(record, bundle, s["reasoning"])
    else:
        st.markdown(f"**{row['name']}** — {row['title']}")
        st.info(row["reasoning"])


if __name__ == "__main__":
    main()
