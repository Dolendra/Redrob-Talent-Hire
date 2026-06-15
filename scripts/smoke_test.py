#!/usr/bin/env python3
"""Plan smoke tests: JD parse, pool size, trap ordering."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.parser import (
    count_candidates,
    iter_candidates,
    load_job_description,
    load_weights,
)
from src.scoring import ensure_skill_vectors, score_candidate


def main() -> int:
    errors: list[str] = []
    weights = load_weights(ROOT / "config" / "weights.json")
    jd_path = ROOT / "data" / "job_description.md"
    job = load_job_description(jd_path, weights)

    if len(job.required_skills) < 15:
        errors.append(f"JD required_skills={len(job.required_skills)} (expected >= 15)")
    if not job.hackathon_meta:
        errors.append("Hackathon appendix not split from ranking text")
    print(f"JD: {job.title}, required_skills={len(job.required_skills)}")

    pool = ROOT / "data" / "candidates.jsonl"
    if pool.exists():
        n = count_candidates(pool)
        print(f"Pool size: {n}")
        if n != 100_000:
            errors.append(f"Expected 100000 candidates, got {n}")
    else:
        print("SKIP: data/candidates.jsonl not found (pool count)")

    sample = ROOT / "data" / "sample_candidates.json"
    if not sample.exists():
        errors.append("Missing data/sample_candidates.json")
        return 1

    cache = ROOT / "data" / "embeddings" / "skill_vectors.npz"
    all_skills = set(job.required_skills)
    for rec in iter_candidates(sample, validate=False):
        all_skills.update(rec.skills)
    vectors = ensure_skill_vectors(
        all_skills,
        weights.get("embedding_model", "all-MiniLM-L6-v2"),
        cache,
        offline=cache.exists(),
    )

    cv_vals, as_vals = [], []
    records = list(iter_candidates(sample, validate=False))
    from src.features import adaptability_count, career_velocity_raw

    for rec in records:
        cv_vals.append(career_velocity_raw(rec, weights))
        as_vals.append(float(adaptability_count(rec)))
    cv_min, cv_max = min(cv_vals), max(cv_vals)
    as_min, as_max = min(as_vals), max(as_vals)

    scores: dict[str, float] = {}
    targets = {"CAND_0000001", "CAND_0000030", "CAND_0000031"}
    for rec in records:
        if rec.candidate_id in targets:
            b = score_candidate(
                job, rec, weights, vectors, cv_min, cv_max, as_min, as_max
            )
            scores[rec.candidate_id] = b.future_fit
            print(
                f"  {rec.candidate_id} ({rec.profile.current_title}): "
                f"FutureFit={b.future_fit:.1f} CurrentFit={b.s_current:.1f}"
            )

    if scores.get("CAND_0000001", 0) <= scores.get("CAND_0000030", 100):
        errors.append(
            "CAND_0000001 should beat Marketing Manager trap CAND_0000030 on Future Fit"
        )
    if scores.get("CAND_0000031", 0) <= scores.get("CAND_0000030", 100):
        errors.append(
            "Recommendation engineer CAND_0000031 should beat Marketing Manager trap"
        )

    if errors:
        print("\nSMOKE TEST FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\nAll smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
