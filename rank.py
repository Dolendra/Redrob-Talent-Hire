#!/usr/bin/env python3
"""Public CLI entrypoint — matches submission_metadata reproduce_command."""

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

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.main import run_ranking
from src.parser import collect_valid_ids
from src.scoring import set_offline_mode


def main() -> None:
    parser = argparse.ArgumentParser(description="Redrob-Talent-Hire ranker")
    parser.add_argument(
        "--candidates",
        type=Path,
        default=Path("candidates.jsonl"),
        help="Path to candidates.jsonl or .jsonl.gz",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("submission.csv"),
        help="Output submission CSV path",
    )
    parser.add_argument("--jd", type=Path, default=Path("data/job_description.md"))
    parser.add_argument("--weights", type=Path, default=Path("config/weights.json"))
    parser.add_argument("--schema", type=Path, default=Path("config/candidate_schema.json"))
    parser.add_argument("--top-n", type=int, default=100)
    parser.add_argument("--validate", action="store_true", help="Run validate_submission.py after write")
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Allow downloading/encoding skills at rank time (not for submission)",
    )
    args = parser.parse_args()

    if not args.allow_network:
        set_offline_mode(True)

    if not args.candidates.exists():
        alt = Path("data") / args.candidates.name
        if alt.exists():
            args.candidates = alt
        else:
            print(f"Candidates file not found: {args.candidates}", file=sys.stderr)
            sys.exit(1)

    valid_ids = collect_valid_ids(args.candidates)
    print(f"Loaded candidate ID index: {len(valid_ids)} records")

    ranked = run_ranking(
        candidates_path=args.candidates,
        out_path=args.out,
        jd_path=args.jd,
        weights_path=args.weights,
        schema_path=args.schema,
        top_n=args.top_n,
        validate_ids=valid_ids,
        offline=not args.allow_network,
    )
    print(f"Wrote top {len(ranked)} to {args.out}")
    print(f"Top candidate: {ranked[0].candidate_id} (score={ranked[0].score})")

    if args.validate:
        from validate_submission import validate_submission

        errors = validate_submission(str(args.out))
        if errors:
            print("Validation failed:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        print("Submission is valid.")


if __name__ == "__main__":
    main()
