"""Layer 1: parse job description and candidate JSONL."""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from typing import Iterator, Optional

import jsonschema

from src.models import (
    CandidateProfile,
    CandidateRecord,
    ExperienceEntry,
    JobDescription,
    RedrobSignals,
    SkillDetail,
)

CANDIDATE_ID_RE = re.compile(r"^CAND_[0-9]{7}$")
SECTION_MARKERS = {
    "required": [
        "things you absolutely need",
        "absolutely need",
        "required skills",
        "must have",
    ],
    "preferred": [
        "things we'd like you to have",
        "we'd like you to have",
        "nice to have",
        "preferred",
    ],
    "disqualifiers": [
        "things we explicitly do not want",
        "explicitly do not want",
    ],
}
BULLET_RE = re.compile(r"^[\s]*[-•*]\s+(.+)$", re.MULTILINE)
EXPERIENCE_RE = re.compile(
    r"(\d+)\s*[–-]\s*(\d+)\s*years?", re.IGNORECASE
)


def load_weights(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_schema(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _open_text(path: Path):
    path = Path(path)
    if path.suffix == ".gz" or path.name.endswith(".jsonl.gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def _read_jd_text(path: Path) -> str:
    path = Path(path)
    if path.suffix.lower() == ".docx":
        try:
            from docx import Document
        except ImportError as e:
            raise ImportError("python-docx required for .docx JD files") from e
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return path.read_text(encoding="utf-8")


def _split_hackathon_meta(text: str, marker: str) -> tuple[str, str]:
    idx = text.lower().find(marker.lower())
    if idx == -1:
        return text, ""
    return text[:idx].strip(), text[idx:].strip()


def _extract_bullets(section_text: str) -> list[str]:
    items = []
    for line in section_text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^[-•*][\s\t]+(.+)$", line)
        if m:
            items.append(m.group(1).strip())
    return items


def _harvest_skill_tokens(text: str) -> list[str]:
    """Pull parenthetical tech names and comma-separated tokens from bullet text."""
    found: list[str] = []
    paren = re.findall(r"\(([^)]+)\)", text)
    for group in paren:
        for part in re.split(r"[,/]", group):
            token = part.strip()
            if token and len(token) < 60:
                found.append(token)
    for token in re.findall(
        r"\b(?:Python|FAISS|Milvus|Pinecone|Qdrant|Weaviate|OpenSearch|Elasticsearch|"
        r"BGE|E5|NDCG|MRR|MAP|LoRA|QLoRA|PEFT|XGBoost|Kubernetes|Docker|Helm|Terraform)\b",
        text,
        re.IGNORECASE,
    ):
        found.append(token)
    return found


def _section_slice(text: str, start_markers: list[str], end_markers: list[str]) -> str:
    lower = text.lower()
    start = -1
    for m in start_markers:
        i = lower.find(m.lower())
        if i != -1:
            start = i + len(m)
            break
    if start == -1:
        return ""
    end = len(text)
    for m in end_markers:
        i = lower.find(m.lower(), start)
        if i != -1:
            end = min(end, i)
    return text[start:end]


def load_job_description(path: Path, weights: Optional[dict] = None) -> JobDescription:
    weights = weights or {}
    raw = _read_jd_text(path)
    marker = weights.get("hackathon_meta_marker", "Final note for the participants")
    ranking_text, hackathon_meta = _split_hackathon_meta(raw, marker)

    title_m = re.search(
        r"Job Description:\s*(.+?)(?:\n|$)", ranking_text, re.IGNORECASE
    )
    title = title_m.group(1).strip() if title_m else "Senior AI Engineer"

    exp_m = EXPERIENCE_RE.search(ranking_text)
    min_exp = float(exp_m.group(1)) if exp_m else None
    max_exp = float(exp_m.group(2)) if exp_m else None

    all_markers = [m for group in SECTION_MARKERS.values() for m in group]
    req_section = _section_slice(
        ranking_text,
        SECTION_MARKERS["required"],
        SECTION_MARKERS["preferred"] + SECTION_MARKERS["disqualifiers"],
    )
    pref_section = _section_slice(
        ranking_text,
        SECTION_MARKERS["preferred"],
        SECTION_MARKERS["disqualifiers"] + ["on location", "the vibe check"],
    )

    required: set[str] = set(weights.get("jd_skill_seeds", {}).get("required", []))
    preferred: set[str] = set(weights.get("jd_skill_seeds", {}).get("preferred", []))

    for bullet in _extract_bullets(req_section):
        required.update(_harvest_skill_tokens(bullet))
    for bullet in _extract_bullets(pref_section):
        preferred.update(_harvest_skill_tokens(bullet))

    loc_m = re.search(r"Location:\s*(.+?)(?:\n|$)", ranking_text, re.IGNORECASE)
    locations = []
    if loc_m:
        locations = [p.strip() for p in re.split(r"[,|]", loc_m.group(1)) if p.strip()]

    return JobDescription(
        title=title,
        raw_text=raw,
        ranking_text=ranking_text,
        hackathon_meta=hackathon_meta,
        required_skills=sorted(required),
        preferred_skills=sorted(preferred - required),
        min_experience_years=min_exp,
        max_experience_years=max_exp,
        locations=locations,
    )


def _normalize_signals(raw: dict) -> RedrobSignals:
    signals = dict(raw)
    for key in ("recruiter_response_rate", "interview_completion_rate", "offer_acceptance_rate"):
        if key in signals and signals[key] is not None:
            v = float(signals[key])
            if v < 0:
                signals[key] = -1.0
            else:
                signals[key] = max(0.0, min(1.0, v))
    if signals.get("github_activity_score", 0) < 0:
        signals["github_activity_score"] = -1.0
    return RedrobSignals(**signals)


def normalize_candidate(raw: dict) -> CandidateRecord:
    history = raw.get("career_history", [])
    timeline = sorted(
        [ExperienceEntry(**entry) for entry in history],
        key=lambda e: e.start_date,
    )
    skill_details = [SkillDetail(**s) for s in raw.get("skills", [])]
    skills = [s.name for s in skill_details]

    return CandidateRecord(
        candidate_id=raw["candidate_id"],
        profile=CandidateProfile(**raw["profile"]),
        experience_timeline=timeline,
        skills=skills,
        skill_details=skill_details,
        redrob_signals=_normalize_signals(raw.get("redrob_signals", {})),
        education=raw.get("education", []),
        certifications=raw.get("certifications", []),
        languages=raw.get("languages", []),
    )


def iter_candidates(
    path: Path,
    schema: Optional[dict] = None,
    validate: bool = True,
) -> Iterator[CandidateRecord]:
    path = Path(path)
    if path.suffix.lower() == ".json":
        for rec in load_candidates_json(path):
            yield rec
        return
    with _open_text(path) as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            if validate and schema is not None:
                jsonschema.validate(raw, schema)
            if not CANDIDATE_ID_RE.match(raw.get("candidate_id", "")):
                raise ValueError(
                    f"Line {line_no}: invalid candidate_id {raw.get('candidate_id')!r}"
                )
            yield normalize_candidate(raw)


def load_candidates_json(path: Path) -> list[CandidateRecord]:
    """Load pretty-printed JSON array (sample_candidates.json)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [data]
    return [normalize_candidate(r) for r in data]


def count_candidates(path: Path) -> int:
    n = 0
    for _ in iter_candidates(path, validate=False):
        n += 1
    return n


def collect_valid_ids(path: Path) -> set[str]:
    return {c.candidate_id for c in iter_candidates(path, validate=False)}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Redrob-Talent-Hire parser smoke test")
    parser.add_argument("--candidates", type=Path, default=Path("data/candidates.jsonl"))
    parser.add_argument("--jd", type=Path, default=Path("data/job_description.md"))
    parser.add_argument("--weights", type=Path, default=Path("config/weights.json"))
    parser.add_argument("--schema", type=Path, default=Path("config/candidate_schema.json"))
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    weights = load_weights(args.weights)
    schema = load_schema(args.schema) if args.schema.exists() else None
    job = load_job_description(args.jd, weights)

    print(f"JD title: {job.title}")
    print(f"Required skills ({len(job.required_skills)}): {job.required_skills[:8]}...")
    print(f"Preferred skills ({len(job.preferred_skills)}): {job.preferred_skills[:5]}...")

    if args.candidates.exists():
        total = count_candidates(args.candidates)
        print(f"Candidates in pool: {total}")
        for i, cand in enumerate(iter_candidates(args.candidates, schema)):
            if i >= args.limit:
                break
            print(
                f"  {cand.candidate_id} | {cand.profile.current_title} | "
                f"{len(cand.skills)} skills | {len(cand.experience_timeline)} roles"
            )
    else:
        print(f"Candidates file not found: {args.candidates}")
