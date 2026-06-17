#!/usr/bin/env python3
"""Validate candidate pool file against the JSON schema."""

import argparse
import sys
import json
from pathlib import Path
import jsonschema

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parser import _open_text

def main():
    parser = argparse.ArgumentParser(description="Validate candidate JSONL pool against candidate schema")
    parser.add_argument("--candidates", type=Path, required=True, help="Path to candidates pool file (.jsonl or .jsonl.gz)")
    parser.add_argument("--schema", type=Path, default=Path("config/candidate_schema.json"), help="Path to JSON Schema file")
    args = parser.parse_args()
    
    if not args.candidates.exists():
        print(f"Error: Candidate file not found: {args.candidates}", file=sys.stderr)
        sys.exit(1)
        
    if not args.schema.exists():
        print(f"Error: Schema file not found: {args.schema}", file=sys.stderr)
        sys.exit(1)
        
    with open(args.schema, "r", encoding="utf-8") as f:
        schema = json.load(f)
        
    validator = jsonschema.Draft7Validator(schema)
    
    total = 0
    valid = 0
    invalid = 0
    error_counts = {}
    
    print(f"Scanning pool: {args.candidates.name} against schema: {args.schema.name}...")
    
    with _open_text(args.candidates) as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                raw = json.loads(line)
                errors = list(validator.iter_errors(raw))
                if errors:
                    invalid += 1
                    for error in errors:
                        path_str = ".".join(str(p) for p in error.path)
                        msg = f"{path_str}: {error.message}"
                        error_counts[msg] = error_counts.get(msg, 0) + 1
                        if invalid <= 10:
                            print(f"Invalid candidate at line {line_no} (ID: {raw.get('candidate_id', 'unknown')}): {msg}")
                else:
                    valid += 1
            except Exception as e:
                invalid += 1
                msg = f"JSON Parse Error: {e}"
                error_counts[msg] = error_counts.get(msg, 0) + 1
                if invalid <= 10:
                    print(f"Invalid line {line_no}: JSON Parse Error: {e}")
                    
    print("\n--- SCHEMA VALIDATION REPORT ---")
    print(f"Total processed: {total}")
    print(f"Valid profiles:  {valid} ({valid/total*100:.1f}%)" if total else "Valid profiles: 0")
    print(f"Invalid profiles: {invalid} ({invalid/total*100:.1f}%)" if total else "Invalid profiles: 0")
    
    if invalid > 0:
        print("\n--- ERROR & VIOLATION BREAKDOWN (Top 15) ---")
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        for msg, count in sorted_errors[:15]:
            print(f"  [{count:5d} times] {msg}")
        sys.exit(1)
    else:
        print("\nAll profiles are 100% schema compliant!")
        sys.exit(0)

if __name__ == "__main__":
    main()
