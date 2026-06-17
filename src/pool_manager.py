# src/pool_manager.py
import json
import os
import gzip
from pathlib import Path
from typing import Iterator, Dict, Any, List, Optional, Callable, Tuple
import jsonschema

from src.resume_parser import ResumeParser
from src.parser import _open_text, normalize_candidate
from src.models import CandidateRecord

class PoolManager:
    def __init__(self, schema_path: Path):
        self.schema_path = schema_path
        self.parser = ResumeParser(schema_path=schema_path)
        with open(schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)
        self.candidates: List[Dict[str, Any]] = []
        self.stats = {
            "total": 0,
            "from_jsonl": 0,
            "from_resume": 0,
            "errors": 0,
            "error_details": []
        }

    def load_jsonl(self, path: Path, progress_cb: Optional[Callable[[float, str], None]] = None) -> Iterator[Dict[str, Any]]:
        """Streams a JSONL or JSONL.gz file line by line memory-safely, with fallback for standard JSON files."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Candidate pool file not found: {path}")

        file_size = os.path.getsize(path)
        bytes_read = 0
        
        self.candidates = []
        self.stats = {
            "total": 0,
            "from_jsonl": 0,
            "from_resume": 0,
            "errors": 0,
            "error_details": []
        }
        
        if progress_cb:
            progress_cb(0.01, f"Opening candidate pool {path.name}...")

        # Detect if it's a standard JSON file (array or object) instead of JSONL
        is_standard_json = False
        first_line_parsed = None
        try:
            with _open_text(path) as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        stripped_clean = stripped.lstrip('\ufeff')
                        try:
                            first_line_parsed = json.loads(stripped_clean)
                            # Successfully parsed first line, so it's a valid single-line JSON.
                            is_standard_json = False
                        except Exception:
                            # Failed to parse first line (e.g. it is just '{' or incomplete),
                            # meaning it's a pretty-printed multi-line JSON.
                            is_standard_json = True
                        break
        except Exception:
            pass

        if is_standard_json:
            try:
                # For safety, avoid loading massive formatted files fully into memory
                if file_size > 50 * 1024 * 1024:
                    raise ValueError(f"Formatted JSON file size {file_size} bytes exceeds safety limit of 50MB.")
                with _open_text(path) as f:
                    content = f.read()
                data = json.loads(content)
                if isinstance(data, dict):
                    raw_list = [data]
                elif isinstance(data, list):
                    raw_list = data
                else:
                    raw_list = []
                
                for idx, raw in enumerate(raw_list, 1):
                    errors = self.validate_candidate(raw)
                    if errors:
                        self.stats["errors"] += 1
                        self.stats["error_details"].append(f"Candidate {idx}: {', '.join(errors[:2])}")
                        raw, _ = self.parser.validate_and_fix(raw, self.schema)
                    
                    self.candidates.append(raw)
                    self.stats["total"] += 1
                    self.stats["from_jsonl"] += 1
                    yield raw
                
                if progress_cb:
                    progress_cb(1.0, f"Successfully loaded {self.stats['total']} candidates ({self.stats['errors']} errors).")
                return
            except Exception as e:
                self.stats["errors"] += 1
                self.stats["error_details"].append(f"JSON Parse Error: {str(e)}")
                if progress_cb:
                    progress_cb(1.0, f"Failed to load: {str(e)}")
                return

        if not is_standard_json and isinstance(first_line_parsed, list):
            # Handle the case where the first line is a complete, single-line JSON array
            for idx, raw in enumerate(first_line_parsed, 1):
                errors = self.validate_candidate(raw)
                if errors:
                    self.stats["errors"] += 1
                    self.stats["error_details"].append(f"Candidate {idx}: {', '.join(errors[:2])}")
                    raw, _ = self.parser.validate_and_fix(raw, self.schema)
                
                self.candidates.append(raw)
                self.stats["total"] += 1
                self.stats["from_jsonl"] += 1
                yield raw
            
            if progress_cb:
                progress_cb(1.0, f"Successfully loaded {self.stats['total']} candidates ({self.stats['errors']} errors).")
            return

        # standard or gzip open (JSONL streaming)
        with _open_text(path) as f:
            for line_no, line in enumerate(f, 1):
                bytes_read += len(line.encode("utf-8"))
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    # Validate
                    errors = self.validate_candidate(raw)
                    if errors:
                        self.stats["errors"] += 1
                        self.stats["error_details"].append(f"Line {line_no}: {', '.join(errors[:2])}")
                        raw, _ = self.parser.validate_and_fix(raw, self.schema)
                    
                    self.candidates.append(raw)
                    self.stats["total"] += 1
                    self.stats["from_jsonl"] += 1
                    
                    yield raw
                except Exception as e:
                    self.stats["errors"] += 1
                    self.stats["error_details"].append(f"Line {line_no} Parse Error: {str(e)}")
                
                # Report progress
                if progress_cb and line_no % 1000 == 0:
                    pct = min(0.99, bytes_read / file_size)
                    progress_cb(pct, f"Loaded {line_no} candidates...")
                    
        if progress_cb:
            progress_cb(1.0, f"Successfully loaded {self.stats['total']} candidates ({self.stats['errors']} errors).")

    def add_resume(self, filename: str, text: str, vocab: List[str]) -> Tuple[Dict[str, Any], List[str]]:
        """Compiles a candidate resume, validates it against the schema, fixes errors, and appends it to the pool."""
        raw_candidate = self.parser.compile(filename, text, vocab)
        fixed_candidate, errors = self.parser.validate_and_fix(raw_candidate, self.schema)
        
        self.candidates.append(fixed_candidate)
        self.stats["total"] += 1
        self.stats["from_resume"] += 1
        if errors:
            self.stats["errors"] += 1
            self.stats["error_details"].append(f"Resume {filename}: {', '.join(errors[:2])}")
            
        return fixed_candidate, errors

    def export_jsonl(self, out_path: Path) -> None:
        """Writes the current pool of candidates as a schema-valid JSONL file."""
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for cand in self.candidates:
                f.write(json.dumps(cand) + "\n")

    def validate_candidate(self, raw: Dict[str, Any]) -> List[str]:
        """Validates a single raw candidate dictionary against the JSON schema."""
        errors = []
        validator = jsonschema.Draft7Validator(self.schema)
        for error in validator.iter_errors(raw):
            errors.append(f"{'.'.join(str(p) for p in error.path)}: {error.message}")
        return errors

    def get_stats(self) -> Dict[str, Any]:
        """Gathers aggregate statistics about the candidate pool."""
        titles = {}
        locations = {}
        experience_years = []
        
        for cand in self.candidates:
            prof = cand.get("profile", {})
            title = prof.get("current_title", "Unknown")
            loc = prof.get("location", "Unknown")
            yexp = prof.get("years_of_experience", 0.0)
            
            titles[title] = titles.get(title, 0) + 1
            locations[loc] = locations.get(loc, 0) + 1
            experience_years.append(yexp)
            
        avg_exp = sum(experience_years) / len(experience_years) if experience_years else 0.0
        
        # Sort maps by count descending
        sorted_titles = sorted(titles.items(), key=lambda x: x[1], reverse=True)
        sorted_locations = sorted(locations.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "total": self.stats["total"],
            "from_jsonl": self.stats["from_jsonl"],
            "from_resume": self.stats["from_resume"],
            "errors": self.stats["errors"],
            "error_details": self.stats["error_details"][:20],  # cap details to avoid bloating
            "average_experience": round(avg_exp, 1),
            "top_titles": sorted_titles[:10],
            "top_locations": sorted_locations[:10]
        }
