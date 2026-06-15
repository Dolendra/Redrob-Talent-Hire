"""Layer 4: contrastive explainability for submission reasoning and dashboard."""

from __future__ import annotations

import hashlib

from src.models import CandidateRecord, JobDescription, RankedCandidate, ScoreBundle

OPENERS_HIGH = [
    "Strong applied-ML profile:",
    "Production-oriented match:",
    "High Future Fit despite modest keyword overlap:",
]
OPENERS_MID = [
    "Solid adjacent fit:",
    "Good trajectory for the role:",
    "Reasonable match with some gaps:",
]
OPENERS_LOW = [
    "Marginal fit — included for pool coverage:",
    "Limited direct overlap with the JD:",
    "Weak role alignment but some transferable signals:",
]


def _pick_opener(candidate_id: str, pool: list[str]) -> str:
    h = int(hashlib.md5(candidate_id.encode()).hexdigest(), 16)
    return pool[h % len(pool)]


def build_reasoning(
    record: CandidateRecord,
    job: JobDescription,
    bundle: ScoreBundle,
    rank: int,
) -> str:
    title = record.profile.current_title
    years = record.profile.years_of_experience
    company = record.profile.current_company
    sig = record.redrob_signals

    if rank <= 10:
        opener = _pick_opener(record.candidate_id, OPENERS_HIGH)
    elif rank <= 50:
        opener = _pick_opener(record.candidate_id, OPENERS_MID)
    else:
        opener = _pick_opener(record.candidate_id, OPENERS_LOW)

    parts = [f"{opener} {title} with {years:.1f} years"]

    if company:
        parts[0] += f" at {company}"

    match_skills = [
        s for s in record.skills[:12]
        if any(
            m.lower() in s.lower() or s.lower() in m.lower()
            for m in job.required_skills[:15]
        )
    ][:3]
    if match_skills:
        parts.append(f"matching JD skills include {', '.join(match_skills)}")

    if bundle.missing_skills:
        parts.append(
            f"keyword ATS would flag missing {', '.join(bundle.missing_skills[:2])}"
        )

    if bundle.adjacent_skills:
        parts.append(
            f"adjacent stack: {', '.join(bundle.adjacent_skills[:3])}"
        )

    if bundle.adaptability_count:
        parts.append(
            f"adopted {bundle.adaptability_count} new technologies in recent roles"
        )

    parts.append(
        f"Future Fit {bundle.future_fit:.0f}% vs Current Fit {bundle.s_current:.0f}%"
    )

    concerns = []
    if sig.recruiter_response_rate < 0.35:
        concerns.append(
            f"recruiter response rate {sig.recruiter_response_rate:.2f}"
        )
    if sig.notice_period_days > 60:
        concerns.append(f"{sig.notice_period_days}-day notice period")
    if bundle.honeypot:
        concerns.append("timeline/skill consistency flags")
    if concerns:
        parts.append(f"concerns: {'; '.join(concerns[:2])}")

    text = "; ".join(parts)
    if len(text) > 480:
        text = text[:477] + "..."
    return text[0].upper() + text[1:] if text else ""


def contrast_card(
    record: CandidateRecord,
    bundle: ScoreBundle,
) -> dict:
    return {
        "candidate_id": record.candidate_id,
        "name": record.profile.anonymized_name,
        "title": record.profile.current_title,
        "quadrant": bundle.quadrant,
        "ats_failed": {
            "current_fit": bundle.s_current,
            "missing_keywords": bundle.missing_skills,
        },
        "talentdna_selected": {
            "future_fit": bundle.future_fit,
            "hidden_gem": bundle.hidden_gem,
            "adjacent_skills": bundle.adjacent_skills,
            "adaptability_count": bundle.adaptability_count,
            "onboarding_weeks": bundle.onboarding_weeks,
            "opportunity_index": bundle.opportunity,
        },
    }


def ascii_decision_card(
    record: CandidateRecord,
    bundle: ScoreBundle,
    rank: int,
) -> str:
    """Printable ASCII contrast card for CLI demo / README."""
    card = contrast_card(record, bundle)
    missing = card["ats_failed"]["missing_keywords"][:3]
    adj = card["talentdna_selected"]["adjacent_skills"][:3]
    width = 62
    lines = [
        "+" + "-" * width + "+",
        f"| TALENTDNA DECISION CARD  Rank #{rank:<3}  {record.candidate_id:<18}|",
        "+" + "-" * width + "+",
        f"| {record.profile.anonymized_name[:28]:<28} | {record.profile.current_title[:28]:<28}|",
        "+" + "-" * width + "+",
        "| WHY ATS FAILED              | WHY TALENTDNA SELECTED       |",
        f"| Current Fit: {bundle.s_current:5.1f}%           | Future Fit:  {bundle.future_fit:5.1f}%          |",
        f"| Missing: {', '.join(missing)[:24]:<24} | Hidden Gem: {bundle.hidden_gem:5.1f}           |",
        f"| Quadrant: {bundle.quadrant:<17}| Onboarding: ~{bundle.onboarding_weeks:<14}|",
        "+" + "-" * width + "+",
    ]
    if adj:
        lines.insert(-1, f"|                             | Adjacent: {', '.join(adj)[:22]:<22}|")
    return "\n".join(lines)


def print_decision_cards(ranked: list[RankedCandidate], limit: int = 3) -> None:
    for r in ranked[:limit]:
        print(ascii_decision_card(r.record, r.bundle, r.rank))
        print()


def attach_reasoning(
    ranked: list[tuple[CandidateRecord, ScoreBundle]],
    job: JobDescription,
) -> list[RankedCandidate]:
    out: list[RankedCandidate] = []
    for rank, (record, bundle) in enumerate(ranked, start=1):
        reasoning = build_reasoning(record, job, bundle, rank)
        bundle.reasoning = reasoning
        out.append(
            RankedCandidate(
                candidate_id=record.candidate_id,
                rank=rank,
                score=0.0,
                reasoning=reasoning,
                bundle=bundle,
                record=record,
            )
        )
    return out
