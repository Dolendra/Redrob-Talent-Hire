#!/usr/bin/env python3
"""Offline: build skill embedding cache from full candidate pool."""

from __future__ import annotations

import os
# Prevent OpenBLAS memory allocation errors on Windows or high-thread systems
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parser import iter_candidates, load_job_description, load_weights
from src.scoring import ensure_skill_vectors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, default=Path("data/candidates.jsonl"))
    parser.add_argument("--jd", type=Path, default=Path("data/job_description.md"))
    parser.add_argument("--weights", type=Path, default=Path("config/weights.json"))
    parser.add_argument("--save-model", action="store_true", help="Snapshot model to data/embeddings/model/")
    args = parser.parse_args()

    weights = load_weights(args.weights)
    job = load_job_description(args.jd, weights)
    skills = set(job.required_skills + job.preferred_skills)
    for rec in iter_candidates(args.candidates, validate=False):
        skills.update(rec.skills)

    cache = Path("data/embeddings/skill_vectors.npz")
    model_name = weights.get("embedding_model", "all-MiniLM-L6-v2")
    ensure_skill_vectors(skills, model_name, cache, offline=False)
    print(f"Cached {len(skills)} unique skill vectors -> {cache}")

    if args.save_model:
        from sentence_transformers import SentenceTransformer

        model_dir = Path("data/embeddings/model")
        model_dir.mkdir(parents=True, exist_ok=True)
        model = SentenceTransformer(model_name)
        model.save(str(model_dir))
        print(f"Saved model snapshot -> {model_dir}")


if __name__ == "__main__":
    main()
