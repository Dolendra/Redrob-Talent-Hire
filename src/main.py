"""Orchestrator: two-pass streaming rank over candidate pool."""

from __future__ import annotations

import csv
import heapq
import json
import re
from pathlib import Path
from typing import Optional

from src.explainability import attach_reasoning, print_decision_cards
from src.features import adaptability_count, career_velocity_raw, signal_fingerprint
from src.models import RankedCandidate
from src.parser import (
    iter_candidates,
    load_job_description,
    load_schema,
    load_weights,
)
from src.scoring import ensure_skill_vectors, score_candidate


def _collect_skills_from_jd_and_iter(path: Path, job_skills: list[str]) -> set[str]:
    skills = set(job_skills)
    path = Path(path)
    if path.suffix.lower() == ".json":
        for rec in iter_candidates(path, validate=False):
            skills.update(rec.skills)
        return skills
    from src.parser import _open_text
    # Fast raw parsing for jsonl files to avoid overhead
    with _open_text(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            for s in raw.get("skills", []):
                name = s.get("name")
                if name:
                    skills.add(name.strip().lower())
    return skills


def run_ranking(
    candidates_path: Path,
    out_path: Path,
    jd_path: Path = Path("data/job_description.md"),
    weights_path: Path = Path("config/weights.json"),
    schema_path: Path = Path("config/candidate_schema.json"),
    top_n: int = 100,
    analytics_path: Optional[Path] = Path("output/analytics.csv"),
    results_path: Optional[Path] = Path("output/results.json"),
    validate_ids: Optional[set[str]] = None,
    offline: bool = True,
    progress_callback: Optional[callable] = None,
) -> list[RankedCandidate]:
    if progress_callback:
        progress_callback(0.02, "Loading weights and job description...")
    weights = load_weights(weights_path)
    schema = load_schema(schema_path) if schema_path.exists() else None
    job = load_job_description(jd_path, weights)

    # Dynamically align experience and scoring weights with the Job Description attributes
    is_fresher_job = any(
        k in job.title.lower() for k in ["fresher", "associate", "junior", "intern", "entry level", "student"]
    )
    min_exp = job.min_experience_years if job.min_experience_years is not None else (0.0 if is_fresher_job else 5.0)
    max_exp = job.max_experience_years if job.max_experience_years is not None else (3.0 if is_fresher_job else 9.0)
    weights["experience_band"] = {
        "min": min_exp,
        "max": max_exp
    }

    if is_fresher_job:
        weights["future_fit_weights"] = {
            "st": 0.50,
            "as": 0.50,
            "cv": 0.00
        }

    is_ml_job = any(
        re.search(r"\b" + re.escape(k) + r"\b", job.title.lower())
        for k in ["ai", "ml", "search", "retrieval", "machine learning", "founding team", "recommender"]
    )
    if not is_ml_job:
        cw = weights.get("composite_weights", {})
        if cw:
            ir_weight = cw.get("career_ir_signal", 0.10)
            cw["s_current"] = cw.get("s_current", 0.12) + ir_weight
            cw["career_ir_signal"] = 0.0


    if progress_callback:
        progress_callback(0.08, "Collecting candidate skills from pool...")
    cache = Path("data/embeddings/skill_vectors.npz")
    all_skills = _collect_skills_from_jd_and_iter(
        candidates_path, job.required_skills + job.preferred_skills
    )
    
    if progress_callback:
        progress_callback(0.25, "Bootstrapping skill vectors...")
    vectors = ensure_skill_vectors(
        all_skills,
        weights.get("embedding_model", "all-MiniLM-L6-v2"),
        cache,
        offline=offline,
    )

    if progress_callback:
        progress_callback(0.45, "Loading candidates & calculating pool statistics...")
    
    candidates: list[CandidateRecord] = []
    cv_vals = []
    as_vals = []
    fp_counts: dict[str, int] = {}
    
    # Pass 1: Stream candidates from disk once, caching records in memory and building stats
    for rec in iter_candidates(candidates_path, validate=False):
        candidates.append(rec)
        cv_vals.append(career_velocity_raw(rec, weights))
        as_vals.append(float(adaptability_count(rec)))
        fp = signal_fingerprint(rec)
        fp_counts[fp] = fp_counts.get(fp, 0) + 1
        
    cv_min, cv_max = (min(cv_vals), max(cv_vals)) if cv_vals else (0.0, 1.0)
    as_min, as_max = (min(as_vals), max(as_vals)) if as_vals else (0.0, 1.0)
    total_candidates = len(candidates)

    if progress_callback:
        progress_callback(0.65, "Scoring and ranking candidates...")
    heap: list[tuple] = []
    
    # Pass 2: Score cached candidates in memory
    for count, rec in enumerate(candidates, 1):
        if progress_callback and total_candidates > 0 and count % max(1, total_candidates // 10) == 0:
            pct = 0.65 + 0.30 * (count / total_candidates)
            progress_callback(pct, f"Scoring candidate {count}/{total_candidates}...")
            
        bundle = score_candidate(
            job,
            rec,
            weights,
            vectors,
            cv_min,
            cv_max,
            as_min,
            as_max,
            signal_fingerprints=fp_counts,
        )
        # Skip honeypots entirely to ensure a 0% honeypot rate
        if bundle.honeypot:
            continue
            
        # Min-heap of size top_n: root = lowest composite among kept set.
        entry = (bundle.composite, rec.candidate_id, rec, bundle)
        if len(heap) < top_n:
            heapq.heappush(heap, entry)
        elif entry[0] > heap[0][0] or (
            entry[0] == heap[0][0] and entry[1] < heap[0][1]
        ):
            heapq.heapreplace(heap, entry)

    if progress_callback:
        progress_callback(0.95, "Analyzing results & attaching reasoning...")
    top = sorted(heap, key=lambda x: (-x[0], x[1]))
    pairs = [(rec, bundle) for _, _, rec, bundle in top]
    ranked = attach_reasoning(pairs, job)

    composites = [r.bundle.composite for r in ranked]
    c_min, c_max = min(composites), max(composites)

    def to_score(composite: float) -> float:
        if c_max <= c_min:
            return 1.0
        return 0.41 + 0.58 * (composite - c_min) / (c_max - c_min)

    prev_score = 1.01
    for r in ranked:
        s = round(to_score(r.bundle.composite), 4)
        if s >= prev_score:
            s = round(prev_score - 0.0001, 4)
        r.score = max(0.41, s)
        prev_score = r.score

    if validate_ids is not None:
        for r in ranked:
            if r.candidate_id not in validate_ids:
                raise ValueError(f"Unknown candidate_id in output: {r.candidate_id}")

    if progress_callback:
        progress_callback(0.98, "Writing output reports...")
    
    # Ensure parent output directories exist
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    write_submission_csv(ranked, out_path)

    if analytics_path:
        analytics_path.parent.mkdir(parents=True, exist_ok=True)
        write_analytics_csv(ranked, analytics_path)
    if results_path:
        results_path.parent.mkdir(parents=True, exist_ok=True)
        write_results_json(ranked, results_path, job.title)

    _print_honeypot_audit(ranked)
    print_decision_cards(ranked, limit=3)

    if progress_callback:
        progress_callback(1.0, "Done!")
    return ranked


def _print_honeypot_audit(ranked: list[RankedCandidate]) -> None:
    honeypots = [r for r in ranked if r.bundle.honeypot]
    rate = len(honeypots) / max(len(ranked), 1) * 100
    print(
        f"Honeypot audit: {len(honeypots)}/{len(ranked)} in top-{len(ranked)} "
        f"({rate:.1f}%) — must stay <= 10% for submission"
    )
    if rate > 10:
        print("WARNING: honeypot rate exceeds 10% disqualification threshold")


def write_submission_csv(ranked: list[RankedCandidate], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["candidate_id", "rank", "score", "reasoning"])
        for r in ranked:
            w.writerow([r.candidate_id, r.rank, r.score, r.reasoning])


def write_analytics_csv(ranked: list[RankedCandidate], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "rank",
        "candidate_id",
        "score",
        "s_current",
        "future_fit",
        "hidden_gem",
        "opportunity",
        "confidence",
        "hiring_risk",
        "quadrant",
        "honeypot",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in ranked:
            b = r.bundle
            w.writerow(
                {
                    "rank": r.rank,
                    "candidate_id": r.candidate_id,
                    "score": r.score,
                    "s_current": b.s_current,
                    "future_fit": b.future_fit,
                    "hidden_gem": b.hidden_gem,
                    "opportunity": b.opportunity,
                    "confidence": b.confidence,
                    "hiring_risk": b.hiring_risk,
                    "quadrant": b.quadrant,
                    "honeypot": b.honeypot,
                }
            )


def write_results_json(ranked: list[RankedCandidate], path: Path, job_title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "job_title": job_title,
        "candidates": [
            {
                "rank": r.rank,
                "candidate_id": r.candidate_id,
                "score": r.score,
                "reasoning": r.reasoning,
                "metrics": r.bundle.model_dump(),
                "profile": {
                    "title": r.record.profile.current_title,
                    "name": r.record.profile.anonymized_name,
                    "years": r.record.profile.years_of_experience,
                    "location": r.record.profile.location,
                },
            }
            for r in ranked
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
