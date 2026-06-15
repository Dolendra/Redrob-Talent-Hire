"""Pydantic models for TalentDNA pipeline."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field


class ExperienceEntry(BaseModel):
    company: str
    title: str
    start_date: str
    end_date: Optional[str] = None
    duration_months: int
    is_current: bool
    industry: str = ""
    company_size: str = ""
    description: str = ""


class SkillDetail(BaseModel):
    name: str
    proficiency: str
    endorsements: int = 0
    duration_months: int = 0


class RedrobSignals(BaseModel):
    profile_completeness_score: float = 0.0
    signup_date: str = ""
    last_active_date: str = ""
    open_to_work_flag: bool = False
    profile_views_received_30d: int = 0
    applications_submitted_30d: int = 0
    recruiter_response_rate: float = 0.0
    avg_response_time_hours: float = 0.0
    skill_assessment_scores: dict[str, float] = Field(default_factory=dict)
    connection_count: int = 0
    endorsements_received: int = 0
    notice_period_days: int = 0
    expected_salary_range_inr_lpa: dict[str, float] = Field(default_factory=dict)
    preferred_work_mode: str = ""
    willing_to_relocate: bool = False
    github_activity_score: float = -1.0
    search_appearance_30d: int = 0
    saved_by_recruiters_30d: int = 0
    interview_completion_rate: float = 0.0
    offer_acceptance_rate: float = -1.0
    verified_email: bool = False
    verified_phone: bool = False
    linkedin_connected: bool = False


class CandidateProfile(BaseModel):
    anonymized_name: str = ""
    headline: str = ""
    summary: str = ""
    location: str = ""
    country: str = ""
    years_of_experience: float = 0.0
    current_title: str = ""
    current_company: str = ""
    current_company_size: str = ""
    current_industry: str = ""


class CandidateRecord(BaseModel):
    candidate_id: str
    profile: CandidateProfile
    experience_timeline: list[ExperienceEntry]
    skills: list[str]
    skill_details: list[SkillDetail]
    redrob_signals: RedrobSignals
    education: list[dict[str, Any]] = Field(default_factory=list)
    certifications: list[dict[str, Any]] = Field(default_factory=list)
    languages: list[dict[str, Any]] = Field(default_factory=list)


class JobDescription(BaseModel):
    title: str
    raw_text: str
    ranking_text: str
    hackathon_meta: str = ""
    required_skills: list[str]
    preferred_skills: list[str]
    min_experience_years: Optional[float] = None
    max_experience_years: Optional[float] = None
    locations: list[str] = Field(default_factory=list)


class ScoreBundle(BaseModel):
    candidate_id: str
    s_current: float = 0.0
    st: float = 0.0
    as_score: float = 0.0
    cv_raw: float = 0.0
    cv_norm: float = 0.0
    future_fit: float = 0.0
    confidence: float = 0.0
    hidden_gem: float = 0.0
    opportunity: float = 0.0
    hiring_risk: float = 0.0
    composite: float = 0.0
    location_fit: float = 0.0
    experience_band: float = 0.0
    honeypot: bool = False
    disqualifier_penalty: float = 0.0
    missing_skills: list[str] = Field(default_factory=list)
    adjacent_skills: list[str] = Field(default_factory=list)
    adaptability_count: int = 0
    onboarding_weeks: str = ""
    quadrant: str = ""
    reasoning: str = ""


class RankedCandidate(BaseModel):
    candidate_id: str
    rank: int
    score: float
    reasoning: str
    bundle: ScoreBundle
    record: CandidateRecord
