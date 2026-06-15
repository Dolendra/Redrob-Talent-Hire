"""Layer 2: feature engineering — ST inputs, AS, CV, risk, traps."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from src.models import CandidateRecord, JobDescription

TECH_TOKEN_RE = re.compile(
    r"\b(?:Python|Java|Scala|Spark|Kafka|Airflow|SQL|Docker|Kubernetes|K8s|"
    r"Terraform|Helm|AWS|GCP|Azure|FAISS|Milvus|Pinecone|Qdrant|Elasticsearch|"
    r"OpenSearch|PyTorch|TensorFlow|XGBoost|Redis|Postgres|MongoDB|dbt|"
    r"Snowflake|BigQuery|Flask|FastAPI|React|TypeScript|Rust|Go|RAG|LLM|"
    r"embeddings|retrieval|ranking|NDCG|MAP|MRR|recommendation)\b",
    re.IGNORECASE,
)
CV_ONLY_SKILLS = {
    "opencv",
    "gan",
    "gans",
    "speech recognition",
    "tts",
    "robotics",
    "object detection",
    "yolo",
    "image classification",
}
NLP_IR_SKILLS = {
    "nlp",
    "embeddings",
    "retrieval",
    "faiss",
    "milvus",
    "ranking",
    "rag",
    "bm25",
    "ndcg",
    "map",
    "mrr",
    "recommendation systems",
}
IR_TIMELINE_RE = re.compile(
    r"\b(recommendation|ranking|retrieval|semantic search|vector search|"
    r"embedding|recsys|re-?rank|learning to rank|search relevance|"
    r"information retrieval|candidate matching|hybrid search)\b",
    re.IGNORECASE,
)
TRAP_TITLE_FRAGMENTS = (
    "marketing manager",
    "marketing ",
    "hr manager",
    "human resources",
    "customer support",
    "sales executive",
    "sales ",
    "content writer",
    "graphic designer",
    "accountant",
    "operations manager",
    "project manager",
    "mechanical engineer",
    "legal counsel",
    "recruiter",
)
STRONG_ML_TITLES = (
    "machine learning engineer",
    "ml engineer",
    "ai engineer",
    "research scientist",
    "applied scientist",
    "nlp engineer",
    "data scientist",
)
GOOD_ENG_TITLES = (
    "software engineer",
    "backend engineer",
    "data engineer",
    "full stack",
    "platform engineer",
    "site reliability",
    "devops",
)


def title_weight(title: str, weights: dict) -> int:
    tw = weights.get("title_weights", {})
    default = weights.get("default_title_weight", 2)
    lower = title.lower()
    best = default
    for key, val in tw.items():
        if key.replace("_", " ") in lower or key in lower:
            best = max(best, val)
    if "principal" in lower or "staff" in lower:
        best = max(best, 4)
    if "senior" in lower:
        best = max(best, 3)
    if "lead" in lower:
        best = max(best, 4)
    if "junior" in lower or "associate" in lower:
        best = min(best, 1) if best == default else best
    return best


def career_velocity_raw(record: CandidateRecord, weights: dict) -> float:
    if not record.experience_timeline:
        return 0.0
    years = max(record.profile.years_of_experience, 0.1)
    earliest = record.experience_timeline[0]
    recent = record.experience_timeline[-1]
    w0 = title_weight(earliest.title, weights)
    w1 = title_weight(recent.title, weights)
    return max(0.0, (w1 - w0) / years)


def adaptability_count(record: CandidateRecord, months: int = 36) -> int:
    """Count distinct tech tokens first seen in roles within last N months."""
    if not record.experience_timeline:
        return 0
    now = datetime.utcnow()
    seen_earlier: set[str] = set()
    new_recent: set[str] = set()

    for entry in record.experience_timeline:
        start = datetime.strptime(entry.start_date, "%Y-%m-%d")
        end = (
            datetime.strptime(entry.end_date, "%Y-%m-%d")
            if entry.end_date
            else now
        )
        tokens = {t.lower() for t in TECH_TOKEN_RE.findall(entry.description)}
        tokens.update(s.name.lower() for s in record.skill_details)

        months_ago_end = (now - end).days / 30.44
        if months_ago_end <= months:
            for t in tokens:
                if t not in seen_earlier:
                    new_recent.add(t)
        else:
            seen_earlier.update(tokens)

    return len(new_recent)


def title_relevance(title: str) -> float:
    """How aligned the current title is with an applied ML / IR engineering role."""
    t = title.lower()
    for s in STRONG_ML_TITLES:
        if s in t:
            return 1.0
    for g in GOOD_ENG_TITLES:
        if g in t:
            return 0.92
    for trap in TRAP_TITLE_FRAGMENTS:
        if trap in t:
            return 0.28
    if any(k in t for k in ("engineer", "developer", "scientist", "architect")):
        return 0.82
    return 0.40


def career_ir_signal(record: CandidateRecord, weights: dict) -> float:
    """Timeline evidence of ranking / retrieval / recommendation work (JD intent)."""
    consulting = set(weights.get("consulting_firms", []))
    score = 0.0
    for entry in record.experience_timeline:
        desc = entry.description
        hits = len(IR_TIMELINE_RE.findall(desc))
        if not hits:
            continue
        role_score = min(35.0, hits * 12.0)
        is_product = not any(c in entry.company for c in consulting)
        if is_product:
            role_score *= 1.25
        score += role_score
    return min(100.0, score)


def timeline_fractures(record: CandidateRecord, weights: dict) -> float:
    rw = weights.get("risk_weights", {})
    short_m = rw.get("short_tenure_months", 12)
    short_p = rw.get("short_tenure_penalty", 20)
    gap_m = rw.get("gap_months", 6)
    gap_p = rw.get("gap_penalty", 15)

    score = 0.0
    timeline = record.experience_timeline
    for entry in timeline:
        if entry.duration_months < short_m:
            score += short_p

    for i in range(len(timeline) - 1):
        cur = timeline[i]
        nxt = timeline[i + 1]
        if cur.end_date and nxt.start_date:
            end = datetime.strptime(cur.end_date, "%Y-%m-%d")
            start = datetime.strptime(nxt.start_date, "%Y-%m-%d")
            gap_months = (start - end).days / 30.44
            if gap_months > gap_m:
                score += gap_p
    return score


def hiring_risk(record: CandidateRecord, weights: dict) -> float:
    rw = weights.get("risk_weights", {})
    fractures = timeline_fractures(record, weights)
    sig = record.redrob_signals
    r_rate = max(0.0, min(1.0, sig.recruiter_response_rate))
    i_rate = max(0.0, min(1.0, sig.interview_completion_rate))
    behavioral = (1 - r_rate) * rw.get("response_weight", 30) + (
        1 - i_rate
    ) * rw.get("interview_weight", 35)
    return min(100.0, fractures + behavioral)


def detect_keyword_stuffer(record: CandidateRecord) -> bool:
    """High skill count with shallow duration / weak assessments."""
    if len(record.skill_details) < 8:
        return False
    avg_dur = sum(s.duration_months for s in record.skill_details) / len(
        record.skill_details
    )
    expert_short = sum(
        1
        for s in record.skill_details
        if s.proficiency in ("advanced", "expert") and s.duration_months < 6
    )
    assessments = record.redrob_signals.skill_assessment_scores
    weak_assess = not assessments or max(assessments.values()) < 55
    return avg_dur < 12 and expert_short >= 2 and weak_assess


def education_tier(record: CandidateRecord) -> str:
    tiers = [e.get("tier", "unknown") for e in record.education if e.get("tier")]
    if not tiers:
        return "unknown"
    order = {"tier_1": 1, "tier_2": 2, "tier_3": 3, "tier_4": 4, "unknown": 5}
    return min(tiers, key=lambda t: order.get(t, 5))


def detect_tier5_plain_language(record: CandidateRecord) -> bool:
    """tier_4 education + non-ML title + keyword-heavy skills, weak career ML signal."""
    if education_tier(record) not in ("tier_4", "unknown"):
        return False
    title = record.profile.current_title.lower()
    if any(k in title for k in ("engineer", "scientist", "developer", "architect")):
        return False
    ml_in_timeline = any(
        TECH_TOKEN_RE.search(e.description)
        for e in record.experience_timeline
    )
    ai_skills = sum(
        1
        for s in record.skills
        if any(x in s.lower() for x in ("ml", "ai", "nlp", "rag", "embedding", "pytorch"))
    )
    return ai_skills >= 4 and not ml_in_timeline


def signal_fingerprint(record: CandidateRecord) -> str:
    s = record.redrob_signals
    return "|".join(
        [
            f"rr{round(s.recruiter_response_rate, 3)}",
            f"ic{round(s.interview_completion_rate, 3)}",
            f"pv{s.profile_views_received_30d}",
            f"sa{s.applications_submitted_30d}",
            f"sr{s.search_appearance_30d}",
            f"sb{s.saved_by_recruiters_30d}",
            f"np{s.notice_period_days}",
            f"pc{round(s.profile_completeness_score, 1)}",
        ]
    )


def behavioral_twin_count(record: CandidateRecord, counts: dict[str, int]) -> bool:
    """True when this signal envelope appears on multiple candidates in the pool."""
    return counts.get(signal_fingerprint(record), 0) > 1


def detect_honeypot(record: CandidateRecord) -> bool:
    """Hard contradictions typical of honeypot profiles (~80 in 100K pool)."""
    if not record.experience_timeline:
        return False

    total_months = sum(e.duration_months for e in record.experience_timeline)
    expected = record.profile.years_of_experience * 12
    if expected > 24 and total_months > expected * 2.25:
        return True

    zero_expert = sum(
        1
        for s in record.skill_details
        if s.proficiency in ("advanced", "expert") and s.duration_months == 0
    )
    if zero_expert >= 2:
        return True

    micro_expert = sum(
        1
        for s in record.skill_details
        if s.proficiency == "expert" and s.duration_months < 3
    )
    if micro_expert >= 8:
        return True

    return False


def disqualifier_penalty(
    record: CandidateRecord, job: JobDescription, weights: dict
) -> float:
    penalties = weights.get("disqualifier_penalties", {})
    total = 0.0

    short_roles = sum(
        1 for e in record.experience_timeline if e.duration_months < 18
    )
    if short_roles >= 3:
        total += penalties.get("title_chaser", 0.15)

    consulting = set(weights.get("consulting_firms", []))
    companies = [e.company for e in record.experience_timeline]
    if companies and all(any(c in co for c in consulting) for co in companies):
        total += penalties.get("consulting_only", 0.20)

    ml_kw = weights.get("ml_title_keywords", [])
    title_lower = record.profile.current_title.lower()
    is_ml_title = any(k in title_lower for k in ml_kw)
    ai_skill_count = sum(
        1
        for s in record.skills
        if any(
            x in s.lower()
            for x in ("ml", "ai", "nlp", "llm", "rag", "embedding", "pytorch", "tensorflow")
        )
    )
    trap_penalties = []
    if not is_ml_title and ai_skill_count >= 3:
        trap_penalties.append(penalties.get("role_skill_mismatch", 0.35))

    title_rel = title_relevance(record.profile.current_title)
    if title_rel <= 0.30 and ai_skill_count >= 4:
        trap_penalties.append(penalties.get("non_technical_keyword_trap", 0.35))

    if detect_keyword_stuffer(record):
        trap_penalties.append(penalties.get("keyword_stuffer", 0.25))

    if detect_tier5_plain_language(record):
        trap_penalties.append(penalties.get("tier5_plain_language", 0.20))

    if trap_penalties:
        total += max(trap_penalties)

    skill_lower = {s.lower() for s in record.skills}
    cv_hits = sum(1 for s in skill_lower if s in CV_ONLY_SKILLS or "opencv" in s)
    nlp_hits = sum(
        1
        for s in skill_lower
        if any(n in s for n in NLP_IR_SKILLS)
    )
    if cv_hits >= 2 and nlp_hits == 0:
        total += penalties.get("cv_only", 0.10)

    sig = record.redrob_signals
    try:
        last_active = datetime.strptime(sig.last_active_date, "%Y-%m-%d")
        days_inactive = (datetime.utcnow() - last_active).days
    except (ValueError, TypeError):
        days_inactive = 0
    if days_inactive > 180 or sig.recruiter_response_rate < 0.10:
        total += penalties.get("inactive", 0.15)

    return min(total, 0.55)


def location_fit(record: CandidateRecord, weights: dict) -> float:
    country = (record.profile.country or "").lower()
    loc = (record.profile.location or "").lower()
    preferred = [p.lower() for p in weights.get("india_preferred_locations", [])]

    if country == "india":
        if any(p in loc for p in preferred):
            return 1.0
        return 0.5
    return 0.2


def experience_band_score(record: CandidateRecord, weights: dict) -> float:
    band = weights.get("experience_band", {})
    lo, hi = band.get("min", 5), band.get("max", 9)
    y = record.profile.years_of_experience
    if lo <= y <= hi:
        return 1.0
    if lo - 1 <= y <= hi + 1:
        return 0.7
    if y < 3 or y > 12:
        return 0.3
    return 0.5


def confidence_score(record: CandidateRecord, weights: dict) -> float:
    cw = weights.get("confidence_weights", {})
    sig = record.redrob_signals

    parts = []
    weights_used = []

    parts.append(sig.profile_completeness_score)
    weights_used.append(cw.get("profile_completeness", 0.20))

    depth = min(100.0, len(record.experience_timeline) * 25)
    parts.append(depth)
    weights_used.append(cw.get("timeline_depth", 0.15))

    if sig.skill_assessment_scores:
        parts.append(
            sum(sig.skill_assessment_scores.values())
            / len(sig.skill_assessment_scores)
        )
    else:
        parts.append(40.0)
    weights_used.append(cw.get("skill_assessments", 0.20))

    parts.append(sig.recruiter_response_rate * 100)
    weights_used.append(cw.get("recruiter_response_rate", 0.20))

    try:
        last_active = datetime.strptime(sig.last_active_date, "%Y-%m-%d")
        days = (datetime.utcnow() - last_active).days
        recency = max(0.0, 100.0 - days / 3.65)
    except (ValueError, TypeError):
        recency = 50.0
    parts.append(recency)
    weights_used.append(cw.get("last_active_recency", 0.15))

    parts.append(100.0 if sig.open_to_work_flag else 30.0)
    weights_used.append(cw.get("open_to_work", 0.10))

    wsum = sum(weights_used)
    score = sum(p * w for p, w in zip(parts, weights_used)) / wsum

    if detect_keyword_stuffer(record):
        score *= 0.65
    if record.skill_details:
        trust = sum(
            min(1.0, s.endorsements / 10) * min(1.0, s.duration_months / 24)
            for s in record.skill_details
        ) / len(record.skill_details)
        score *= 0.7 + 0.3 * trust

    return score
