"""Layer 3: embedding-backed scoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np

from src.features import (
    adaptability_count,
    behavioral_twin_count,
    career_ir_signal,
    career_velocity_raw,
    confidence_score,
    detect_honeypot,
    detect_keyword_stuffer,
    detect_tier5_plain_language,
    disqualifier_penalty,
    experience_band_score,
    hiring_risk,
    location_fit,
    title_relevance,
)
from src.models import CandidateRecord, JobDescription, ScoreBundle

_MODEL = None
_SKILL_VECTORS: dict[str, np.ndarray] = {}
_OFFLINE = False


def set_offline_mode(enabled: bool = True) -> None:
    global _OFFLINE
    _OFFLINE = enabled
    if enabled:
        import os

        os.environ["HF_HUB_OFFLINE"] = "1"


def _get_model(model_name: str):
    global _MODEL
    if _MODEL is None:
        import os

        if _OFFLINE:
            os.environ["HF_HUB_OFFLINE"] = "1"
        from sentence_transformers import SentenceTransformer

        local = Path("data/embeddings/model")
        if local.exists() and (local / "config.json").exists():
            _MODEL = SentenceTransformer(str(local))
        elif _OFFLINE:
            raise RuntimeError(
                "Offline ranking requires data/embeddings/model/ or precomputed "
                "skill_vectors.npz covering all skills. Run scripts/precompute_embeddings.py first."
            )
        else:
            _MODEL = SentenceTransformer(model_name)
    return _MODEL


def _normalize_skill(name: str) -> str:
    return name.strip().lower()


def load_skill_vectors(path: Path) -> dict[str, np.ndarray]:
    global _SKILL_VECTORS
    if path.exists():
        data = np.load(path, allow_pickle=True)
        names = list(data["names"])
        vectors = data["vectors"]
        _SKILL_VECTORS = {n: vectors[i] for i, n in enumerate(names)}
    return _SKILL_VECTORS


def save_skill_vectors(path: Path, vectors: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = sorted(vectors.keys())
    arr = np.stack([vectors[n] for n in names]).astype(np.float16)
    np.savez_compressed(path, names=np.array(names), vectors=arr)


def ensure_skill_vectors(
    skills: set[str],
    model_name: str,
    cache_path: Path,
    offline: bool = False,
) -> dict[str, np.ndarray]:
    if offline:
        set_offline_mode(True)
    load_skill_vectors(cache_path)
    missing = {_normalize_skill(s) for s in skills} - set(_SKILL_VECTORS.keys())
    if missing:
        if offline:
            raise RuntimeError(
                f"Missing {len(missing)} skill vectors in {cache_path} (offline mode). "
                f"Examples: {sorted(missing)[:5]}. "
                "Run: python scripts/precompute_embeddings.py --candidates <pool.jsonl>"
            )
        model = _get_model(model_name)
        encoded = model.encode(
            sorted(missing), normalize_embeddings=True, show_progress_bar=False
        )
        for name, vec in zip(sorted(missing), encoded):
            _SKILL_VECTORS[name] = np.asarray(vec, dtype=np.float32)
        save_skill_vectors(cache_path, _SKILL_VECTORS)
    return _SKILL_VECTORS


def _vec(skill: str, vectors: dict[str, np.ndarray], model_name: str) -> Optional[np.ndarray]:
    key = _normalize_skill(skill)
    if key in vectors:
        return vectors[key]
    if _OFFLINE:
        return None
    model = _get_model(model_name)
    v = model.encode([skill], normalize_embeddings=True)[0]
    vectors[key] = np.asarray(v, dtype=np.float32)
    return vectors[key]


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def current_fit(
    job: JobDescription,
    record: CandidateRecord,
    vectors: dict[str, np.ndarray],
    model_name: str,
) -> tuple[float, list[str]]:
    j_skills = job.required_skills or job.preferred_skills
    if not j_skills:
        text = f"{record.profile.headline} {record.profile.summary}"
        j_vec = _get_model(model_name).encode([job.ranking_text[:2000]], normalize_embeddings=True)[0]
        c_vec = _get_model(model_name).encode([text[:1500]], normalize_embeddings=True)[0]
        return _cos(j_vec, c_vec) * 100, []

    c_set = {_normalize_skill(s) for s in record.skills}
    sims = []
    missing = []
    for j in j_skills:
        jv = _vec(j, vectors, model_name)
        if jv is None:
            continue
        if _normalize_skill(j) in c_set:
            sims.append(1.0)
            continue
        best = 0.0
        for c in record.skills:
            cv = _vec(c, vectors, model_name)
            if cv is not None:
                best = max(best, _cos(jv, cv))
        if best < 0.55:
            missing.append(j)
        sims.append(best)
    return (sum(sims) / len(sims) * 100 if sims else 0.0), missing


def skill_transferability(
    job: JobDescription,
    record: CandidateRecord,
    vectors: dict[str, np.ndarray],
    model_name: str,
) -> tuple[float, list[str]]:
    j_skills = job.required_skills
    c_set = {_normalize_skill(s) for s in record.skills}
    if not j_skills:
        return 0.0, []

    sims = []
    adjacent: list[str] = []
    for j in j_skills:
        jn = _normalize_skill(j)
        if jn in c_set:
            sims.append(1.0)
            continue
        jv = _vec(j, vectors, model_name)
        if jv is None:
            continue
        best = 0.0
        best_skill = ""
        for c in record.skills:
            cv = _vec(c, vectors, model_name)
            if cv is not None:
                s = _cos(jv, cv)
                if s > best:
                    best = s
                    best_skill = c
        sims.append(best)
        if best >= 0.45 and best_skill:
            adjacent.append(best_skill)
    st = sum(sims) / len(sims) * 100 if sims else 0.0
    return st, list(dict.fromkeys(adjacent))[:5]


def min_max_norm(value: float, vmin: float, vmax: float) -> float:
    if vmax <= vmin:
        return 50.0
    return (value - vmin) / (vmax - vmin) * 100.0


def onboarding_label(st: float) -> str:
    if st >= 70:
        return "2 weeks"
    if st >= 45:
        return "4-6 weeks"
    return "8+ weeks"


def quadrant_label(s_current: float, future_fit: float) -> str:
    smed, fmed = 50.0, 50.0
    high_s, high_f = s_current >= smed, future_fit >= fmed
    if high_s and high_f:
        return "Safe Hire"
    if not high_s and high_f:
        return "Hidden Gem"
    if high_s and not high_f:
        return "Overrated"
    return "Unaligned"


def score_candidate(
    job: JobDescription,
    record: CandidateRecord,
    weights: dict,
    vectors: dict[str, np.ndarray],
    cv_min: float,
    cv_max: float,
    as_min: float,
    as_max: float,
    signal_fingerprints: Optional[dict[str, int]] = None,
) -> ScoreBundle:
    model_name = weights.get("embedding_model", "all-MiniLM-L6-v2")

    s_current, missing = current_fit(job, record, vectors, model_name)
    st, adjacent = skill_transferability(job, record, vectors, model_name)
    as_raw = float(adaptability_count(record))
    as_norm = min_max_norm(as_raw, as_min, as_max)
    cv_raw = career_velocity_raw(record, weights)
    cv_norm = min_max_norm(cv_raw, cv_min, cv_max)

    ff_w = weights.get("future_fit_weights", {})
    future_fit = min(
        100.0,
        ff_w.get("st", 0.4) * st
        + ff_w.get("as", 0.3) * as_norm
        + ff_w.get("cv", 0.3) * cv_norm,
    )

    conf = confidence_score(record, weights)
    ats_miss = max(0.0, future_fit - s_current)
    hidden_gem = future_fit * conf * ats_miss / 100.0

    sig = record.redrob_signals
    opp = future_fit * sig.recruiter_response_rate * sig.interview_completion_rate / 100.0

    risk = hiring_risk(record, weights)
    honeypot = detect_honeypot(record)
    disq = disqualifier_penalty(record, job, weights)
    loc = location_fit(record, weights) * 100
    exp_band = experience_band_score(record, weights) * 100
    title_rel = title_relevance(record.profile.current_title)
    ir_signal = career_ir_signal(record, weights)

    cw = weights.get("composite_weights", {})
    composite = (
        cw.get("s_current", 0.14) * s_current / 100
        + cw.get("future_fit", 0.34) * future_fit / 100
        + cw.get("hidden_gem", 0.18) * min(hidden_gem, 100) / 100
        + cw.get("opportunity", 0.10) * opp / 100
        + cw.get("confidence", 0.08) * conf / 100
        + cw.get("location_fit", 0.04) * loc / 100
        + cw.get("experience_band", 0.04) * exp_band / 100
        + cw.get("career_ir_signal", 0.12) * ir_signal / 100
        - cw.get("risk", 0.10) * risk / 100
        - disq
    )
    composite *= 0.35 + 0.65 * title_rel
    if title_rel >= 0.92:
        composite += 0.05 * (ir_signal / 100.0)
    if title_rel >= 1.0:
        composite += 0.03
    if honeypot:
        composite -= cw.get("honeypot", 0.35)
    if signal_fingerprints is not None and behavioral_twin_count(
        record, signal_fingerprints
    ):
        composite -= 0.05
    composite = max(0.0, composite)

    return ScoreBundle(
        candidate_id=record.candidate_id,
        s_current=round(s_current, 2),
        st=round(st, 2),
        as_score=round(as_norm, 2),
        cv_raw=round(cv_raw, 4),
        cv_norm=round(cv_norm, 2),
        future_fit=round(future_fit, 2),
        confidence=round(conf, 2),
        hidden_gem=round(hidden_gem, 2),
        opportunity=round(opp, 2),
        hiring_risk=round(risk, 2),
        composite=composite,
        location_fit=round(loc, 2),
        experience_band=round(exp_band, 2),
        honeypot=honeypot,
        disqualifier_penalty=round(disq, 4),
        missing_skills=missing[:5],
        adjacent_skills=adjacent,
        adaptability_count=int(as_raw),
        onboarding_weeks=onboarding_label(st),
        quadrant=quadrant_label(s_current, future_fit),
    )
