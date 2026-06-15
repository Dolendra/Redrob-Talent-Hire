# Redrob Signals Reference (Redrob-Talent-Hire)

Each candidate includes a nested `redrob_signals` object with **22 required fields** (see [`config/candidate_schema.json`](../config/candidate_schema.json)).

## Sentinel values

| Field | Sentinel | Handling |
|-------|----------|----------|
| `github_activity_score` | `-1` | No GitHub linked — exclude from confidence |
| `offer_acceptance_rate` | `-1` | No offer history — exclude from behavioral averages |

## Key signals used by Redrob-Talent-Hire

| Signal | Use in ranker |
|--------|----------------|
| `recruiter_response_rate` | Opportunity Index, hiring risk, confidence |
| `interview_completion_rate` | Opportunity Index, hiring risk |
| `profile_completeness_score` | Confidence score |
| `skill_assessment_scores` | Confidence; keyword-stuffer detection |
| `last_active_date` | Availability / inactive penalty |
| `open_to_work_flag` | Confidence boost |
| `notice_period_days` | Reasoning concerns line |

## Trap classes (~dataset)

| Trap | Detection in Redrob-Talent-Hire |
|------|------------------------|
| **Honeypots (~80)** | Impossible tenure math, expert skills with <6 months, timeline fractures → `detect_honeypot()` + −0.50 composite |
| **Keyword stuffers** | Many skills, low avg `duration_months`, weak assessments → confidence discount + −0.08 composite |
| **Plain-language Tier 5s** | `education.tier` = tier_4, non-ML title, AI keywords without timeline ML signal → −0.06 composite |
| **Behavioral twins** | Identical signal envelope across IDs → −0.04 composite on duplicate fingerprint |

**Disqualification rule:** >10% honeypots in top 100 → submission disqualified. Run `rank.py` and check the honeypot audit line.

## Signal fingerprint (twin detection)

Redrob-Talent-Hire hashes rounded behavioral fields: response rates, profile views, applications, search appearances, notice period, completeness.
