"""Orchestrator: two-pass streaming rank over candidate pool."""

from __future__ import annotations

import csv
import heapq
import json
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
    for rec in iter_candidates(path, validate=False):
        skills.update(rec.skills)
    return skills


def _pass1_stats(path: Path, weights: dict) -> tuple[float, float, float, float, dict[str, int]]:
    cv_vals = []
    as_vals = []
    fp_counts: dict[str, int] = {}
    for rec in iter_candidates(path, validate=False):
        cv_vals.append(career_velocity_raw(rec, weights))
        as_vals.append(float(adaptability_count(rec)))
        fp = signal_fingerprint(rec)
        fp_counts[fp] = fp_counts.get(fp, 0) + 1
    cv_min, cv_max = (min(cv_vals), max(cv_vals)) if cv_vals else (0.0, 1.0)
    as_min, as_max = (min(as_vals), max(as_vals)) if as_vals else (0.0, 1.0)
    return cv_min, cv_max, as_min, as_max, fp_counts


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
) -> list[RankedCandidate]:
    weights = load_weights(weights_path)
    schema = load_schema(schema_path) if schema_path.exists() else None
    job = load_job_description(jd_path, weights)

    cache = Path("data/embeddings/skill_vectors.npz")
    all_skills = _collect_skills_from_jd_and_iter(
        candidates_path, job.required_skills + job.preferred_skills
    )
    vectors = ensure_skill_vectors(
        all_skills,
        weights.get("embedding_model", "all-MiniLM-L6-v2"),
        cache,
        offline=offline,
    )

    cv_min, cv_max, as_min, as_max, signal_fingerprints = _pass1_stats(
        candidates_path, weights
    )

    heap: list[tuple] = []
    for rec in iter_candidates(candidates_path, schema=schema):
        bundle = score_candidate(
            job,
            rec,
            weights,
            vectors,
            cv_min,
            cv_max,
            as_min,
            as_max,
            signal_fingerprints=signal_fingerprints,
        )
        # Min-heap of size top_n: root = lowest composite among kept set.
        entry = (bundle.composite, rec.candidate_id, rec, bundle)
        if len(heap) < top_n:
            heapq.heappush(heap, entry)
        elif entry[0] > heap[0][0] or (
            entry[0] == heap[0][0] and entry[1] < heap[0][1]
        ):
            heapq.heapreplace(heap, entry)

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

    write_submission_csv(ranked, out_path)

    if analytics_path:
        write_analytics_csv(ranked, analytics_path)
    if results_path:
        write_results_json(ranked, results_path, job.title)

    _print_honeypot_audit(ranked)
    print_decision_cards(ranked, limit=3)

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
