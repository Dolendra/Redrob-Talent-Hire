from __future__ import annotations
import streamlit as st
import textwrap
from src.models import CandidateRecord, ScoreBundle

def clean_html(html: str) -> str:
    return "\n".join(line.strip() for line in html.splitlines())

# Define UI colors matching our design system
COLORS = {
    "primary": "#38bdf8",     # Cyan
    "gem": "#fbbf24",         # Amber
    "safe": "#22c55e",        # Green
    "stretch": "#f97316",     # Orange
    "pass": "#94a3b8",        # Muted gray-blue
    "destructive": "#f87171"  # Red
}

GLOWS = {
    "primary": "rgba(56, 189, 248, 0.4)",
    "gem": "rgba(251, 191, 36, 0.45)",
    "safe": "rgba(34, 197, 94, 0.4)",
    "stretch": "rgba(249, 115, 22, 0.4)",
    "pass": "rgba(148, 163, 184, 0.2)",
    "destructive": "rgba(248, 113, 113, 0.4)"
}

def render_score_gauge(value: float, label: str, sublabel: str = "", variant: str = "primary", size: str = "md") -> str:
    """Generates the HTML/SVG code for a circular progress gauge with outer glow."""
    dim = 180 if size == "lg" else 140
    stroke = 10 if size == "lg" else 8
    r = (dim - stroke) / 2
    c = 2 * 3.14159265 * r
    pct = max(0.0, min(100.0, value))
    offset = c - (pct / 100.0) * c
    
    color = COLORS.get(variant, COLORS["primary"])
    glow = GLOWS.get(variant, GLOWS["primary"])
    
    return clean_html(f"""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; font-family: sans-serif; margin: 10px;">
        <div style="position: relative; width: {dim}px; height: {dim}px;">
            <svg width="{dim}" height="{dim}" style="transform: rotate(-90deg); filter: drop-shadow(0 0 12px {glow});">
                <!-- Track -->
                <circle cx="{dim/2}" cy="{dim/2}" r="{r}" stroke="rgba(255, 255, 255, 0.05)" stroke-width="{stroke}" fill="none" />
                <!-- Fill -->
                <circle cx="{dim/2}" cy="{dim/2}" r="{r}" stroke="{color}" stroke-width="{stroke}" fill="none" 
                        stroke-linecap="round" stroke-dasharray="{c}" stroke-dashoffset="{offset}" 
                        style="transition: stroke-dashoffset 1s ease-out;" />
            </svg>
            <div style="position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                <span style="font-size: 32px; font-weight: bold; color: #ffffff;">{round(value)}</span>
                <span style="font-size: 10px; color: #94a3b8; font-family: monospace; letter-spacing: 1.5px; margin-top: -2px;">/ 100</span>
            </div>
        </div>
        <div style="margin-top: 12px; font-size: 14px; font-weight: 500; color: #ffffff;">{label}</div>
        {f'<div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">{sublabel}</div>' if sublabel else ''}
    </div>
    """)

def render_signal_bar(label: str, value: float, max_val: float = 100.0, icon_svg: str = "") -> str:
    """Generates the HTML code for a colored progress bar (Signals list)."""
    pct = min(100.0, max(0.0, (value / max_val) * 100.0))
    bar_color = COLORS["safe"] if pct >= 75 else COLORS["primary"] if pct >= 50 else COLORS["stretch"] if pct >= 25 else COLORS["destructive"]
    
    icon_html = f'<span style="margin-right: 6px; display: inline-flex; align-items: center; vertical-align: middle;">{icon_svg}</span>' if icon_svg else ''
    
    return clean_html(f"""
    <div style="margin-bottom: 12px; font-family: sans-serif;">
        <div style="display: flex; align-items: center; justify-content: justify; font-size: 12px; margin-bottom: 6px;">
            <span style="color: #94a3b8; display: flex; align-items: center;">{icon_html}{label}</span>
            <span style="margin-left: auto; font-family: monospace; font-weight: bold; color: #ffffff;">{round(value)}</span>
        </div>
        <div style="height: 6px; border-radius: 3px; background: rgba(255, 255, 255, 0.05); overflow: hidden;">
            <div style="height: 100%; width: {pct}%; background: {bar_color}; border-radius: 3px; transition: width 0.5s ease-out;"></div>
        </div>
    </div>
    """)

def get_reasons_ats_missed(record: CandidateRecord, bundle: ScoreBundle) -> list[str]:
    reasons = []
    if bundle.missing_skills and bundle.adjacent_skills:
        from dashboard.components.skill_adjacency_map import get_adjacent_skills
        lower_cand = {s.lower() for s in record.skills}
        bridges = []
        for m in bundle.missing_skills:
            neighbors = get_adjacent_skills(m)
            matched_neighbors = [n for n in neighbors if n in lower_cand]
            if matched_neighbors:
                bridges.append(f"{m} ≈ {', '.join(matched_neighbors[:2])}")
        if bridges:
            reasons.append(
                f"ATS rejected for missing {', '.join(bundle.missing_skills[:3])} "
                f"— but candidate has structural neighbors: {'; '.join(bridges[:2])}."
            )
            
    if bundle.cv_norm >= 75.0:
        reasons.append(
            f"Career velocity in the top quartile ({bundle.cv_norm:.0f} percentile) — closes the gap fast."
        )
        
    gap = bundle.future_fit - bundle.s_current
    if gap > 15.0:
        reasons.append(
            f"Future Fit is {gap:.0f} pts above Current Fit — keyword matchers can't see this trajectory."
        )
    return reasons

def render_talent_dna_report(record: CandidateRecord, bundle: ScoreBundle, reasoning: str, ats_score: float) -> None:
    """Renders the comprehensive candidate TalentDNA Report (Screen 4 & 5)."""
    
    # 1. Page Header (Candidate Intro)
    st.markdown(clean_html(f"""
        <div style="margin-bottom: 24px;">
            <div style="font-family: monospace; font-size: 11px; color: #38bdf8; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 4px;">TalentDNA Profile Analysis</div>
            <h1 style="margin: 0; font-size: 2.5rem; font-weight: 800; color: #ffffff; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                {record.profile.anonymized_name}
            </h1>
            <p style="margin: 8px 0 0 0; font-size: 1.1rem; color: #cbd5e1;">
                {record.profile.current_title} &middot; {record.profile.location}, {record.profile.country} &middot; {record.profile.years_of_experience:.1f}y experience
            </p>
        </div>
    """), unsafe_allow_html=True)
    
    # Map recommendation and variant
    rec_label = "Strong Hire" if bundle.quadrant == "Safe Hire" else "Strong Hire (Gem)" if bundle.quadrant == "Hidden Gem" else "Consider" if bundle.quadrant == "Overrated" else "Pass"
    rec_variant = "safe" if bundle.quadrant == "Safe Hire" else "gem" if bundle.quadrant == "Hidden Gem" else "stretch" if bundle.quadrant == "Overrated" else "pass"
    
    # 2. Hero Section: Circular gauges + ATS vs DNA delta list
    hero_col1, hero_col2, hero_col3 = st.columns([1, 1, 1.8])
    
    with hero_col1:
        st.markdown(render_score_gauge(bundle.s_current, "Current Fit", "direct skill match", "primary", "lg"), unsafe_allow_html=True)
        
    with hero_col2:
        st.markdown(render_score_gauge(bundle.future_fit, "Future Fit", "with adjacency & velocity", rec_variant, "lg"), unsafe_allow_html=True)
        
    with hero_col3:
        delta = int(bundle.future_fit - ats_score)
        delta_sign = "+" if delta >= 0 else ""
        delta_color = COLORS["safe"] if delta > 0 else COLORS["pass"]
        
        reasons_list_html = "".join([
            f"""
            <li style="display: flex; align-items: flex-start; gap: 10px; font-size: 13px; color: #e2e8f0; margin-bottom: 8px;">
                <span style="color: #fbbf24; margin-top: 2px; font-size: 14px;">✦</span>
                <span>{r}</span>
            </li>
            """ for r in get_reasons_ats_missed(record, bundle) if r
        ]) or f"""
        <li style="display: flex; align-items: flex-start; gap: 10px; font-size: 13px; color: #e2e8f0; margin-bottom: 8px;">
            <span style="color: #22c55e; margin-top: 2px; font-size: 14px;">✔</span>
            <span>Direct skill match was solid enough; no hidden-gem premium applies.</span>
        </li>
        """
        
        st.markdown(clean_html(f"""
            <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px; height: 100%;">
                <div style="font-family: monospace; font-size: 10px; color: #fbbf24; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px;">Why ATS missed this candidate</div>
                <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 16px;">
                    <div>
                        <div style="font-family: monospace; font-size: 10px; color: #94a3b8; text-transform: uppercase;">ATS</div>
                        <div style="font-size: 32px; font-weight: bold; color: {COLORS['destructive']};">{round(ats_score)}</div>
                    </div>
                    <div style="font-size: 24px; color: #94a3b8;">&rarr;</div>
                    <div>
                        <div style="font-family: monospace; font-size: 10px; color: #94a3b8; text-transform: uppercase;">TalentDNA</div>
                        <div style="font-size: 32px; font-weight: bold; color: {COLORS['safe'] if bundle.future_fit > ats_score else '#ffffff'};">{round(bundle.future_fit)}</div>
                    </div>
                    <div style="margin-left: auto; font-family: monospace; font-size: 12px; color: #94a3b8; text-align: right;">
                        <span style="font-size: 16px; font-weight: bold; color: {delta_color};">{delta_sign}{delta}</span>
                        <br>point delta
                    </div>
                </div>
                <ul style="list-style: none; padding: 0; margin: 0;">
                    {reasons_list_html}
                </ul>
            </div>
        """), unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 3. Secondary Stats Cards (Growth Velocity, Risk Score, Onboarding Cost)
    stat_col1, stat_col2, stat_col3 = st.columns(3)
    
    # Growth Velocity Card
    with stat_col1:
        gv_pct = round(bundle.cv_norm)
        gv_label = "top quartile" if gv_pct >= 75 else "above average" if gv_pct >= 50 else "steady"
        gv_color = COLORS["safe"] if gv_pct >= 75 else COLORS["primary"] if gv_pct >= 50 else COLORS["stretch"]
        st.markdown(clean_html(f"""
            <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
                <div style="font-family: monospace; font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px; display: flex; align-items: center; gap: 6px;">
                    <span style="color: {gv_color};">&#9650;</span> GROWTH VELOCITY
                </div>
                <div style="font-size: 36px; font-weight: bold; color: {gv_color}; margin: 10px 0 4px 0;">{gv_pct}%</div>
                <div style="font-size: 12px; color: #94a3b8;">{gv_label}</div>
            </div>
        """), unsafe_allow_html=True)
        
    # Risk Score Card
    with stat_col2:
        risk_val = bundle.hiring_risk
        risk_label = "elevated risk" if risk_val >= 60 else "moderate risk" if risk_val >= 30 else "low risk"
        risk_color = COLORS["destructive"] if risk_val >= 60 else COLORS["stretch"] if risk_val >= 30 else COLORS["safe"]
        
        # Breakdown calculations
        job_hopping = min(60, sum(1 for e in record.experience_timeline if e.duration_months < 12) * 20)
        ghosting = round((1 - record.redrob_signals.recruiter_response_rate) * 40)
        dropoff = round((1 - record.redrob_signals.interview_completion_rate) * 40)
        
        st.markdown(clean_html(f"""
            <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
                <div style="font-family: monospace; font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px; display: flex; align-items: center; gap: 6px;">
                    <span style="color: {risk_color};">&#9888;</span> RISK SCORE
                </div>
                <div style="font-size: 36px; font-weight: bold; color: {risk_color}; margin: 10px 0 4px 0;">{round(risk_val)}</div>
                <div style="font-size: 12px; color: #94a3b8; margin-bottom: 12px;">{risk_label}</div>
                <div style="border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 8px;">
                    <div style="display: flex; justify-content: justify; font-size: 11px; font-family: monospace; color: #94a3b8; margin-bottom: 4px;">
                        <span>Job hopping</span>
                        <span style="margin-left: auto; color: #ffffff;">{job_hopping}</span>
                    </div>
                    <div style="display: flex; justify-content: justify; font-size: 11px; font-family: monospace; color: #94a3b8; margin-bottom: 4px;">
                        <span>Ghosting</span>
                        <span style="margin-left: auto; color: #ffffff;">{ghosting}</span>
                    </div>
                    <div style="display: flex; justify-content: justify; font-size: 11px; font-family: monospace; color: #94a3b8;">
                        <span>Drop-off</span>
                        <span style="margin-left: auto; color: #ffffff;">{dropoff}</span>
                    </div>
                </div>
            </div>
        """), unsafe_allow_html=True)
        
    # Onboarding Cost Card
    with stat_col3:
        st_val = bundle.st
        onboarding_w = bundle.onboarding_weeks
        onboarding_color = COLORS["safe"] if st_val >= 70 else COLORS["primary"] if st_val >= 45 else COLORS["stretch"]
        st.markdown(clean_html(f"""
            <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px; height: 100%;">
                <div style="font-family: monospace; font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px; display: flex; align-items: center; gap: 6px;">
                    <span style="color: {onboarding_color};">&#9201;</span> ONBOARDING COST
                </div>
                <div style="font-size: 36px; font-weight: bold; color: {onboarding_color}; margin: 10px 0 4px 0;">{onboarding_w}</div>
                <div style="font-size: 12px; color: #94a3b8;">weeks to productivity</div>
            </div>
        """), unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 4. Main grid: Skill DNA (left) vs Redrob Signals (right)
    col_left, col_right = st.columns([1.4, 1])
    
    with col_left:
        # Construct Required DNA list
        required_list_html = []
        lower_cand = {s.lower() for s in record.skills}
        
        # Load skill registry to compute adjacencies (or mapping list)
        from dashboard.components.skill_adjacency_map import get_adjacent_skills
        
        # We check adjacent matches
        for req in bundle.missing_skills + list(set(record.skills) - set(bundle.missing_skills)):
            # Check if direct match
            is_direct = req.lower() in lower_cand
            
            # Check if adjacent bridge
            neighbors = get_adjacent_skills(req)
            bridges = [n for n in neighbors if n in lower_cand]
            
            if is_direct:
                border_color = "rgba(34, 197, 94, 0.3)"
                bg_color = "rgba(34, 197, 94, 0.05)"
                dot_color = COLORS["safe"]
                status_text = '<span style="color: #22c55e;">direct match</span>'
            elif bridges:
                border_color = "rgba(251, 191, 36, 0.3)"
                bg_color = "rgba(251, 191, 36, 0.05)"
                dot_color = COLORS["gem"]
                status_text = f'<span style="color: #fbbf24;">&approx; {", ".join(bridges[:3])}</span>'
            else:
                border_color = "rgba(248, 113, 113, 0.2)"
                bg_color = "rgba(248, 113, 113, 0.05)"
                dot_color = COLORS["destructive"]
                status_text = '<span style="color: #f87171;">not found</span>'
                
            required_list_html.append(clean_html(f"""
                <div style="display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 6px; border: 1px solid {border_color}; background: {bg_color}; margin-bottom: 8px;">
                    <span style="width: 8px; height: 8px; border-radius: 50%; background: {dot_color}; flex-shrink: 0;"></span>
                    <span style="font-family: monospace; font-size: 13px; color: #ffffff;">{req}</span>
                    <span style="margin-left: auto; font-family: monospace; font-size: 11px;">{status_text}</span>
                </div>
            """))
            
        # Preferred skills badges
        pref_badges_html = "".join([
            f'<span style="padding: 2px 8px; border-radius: 12px; background: rgba(251, 191, 36, 0.1); border: 1px solid rgba(251, 191, 36, 0.3); color: #fbbf24; font-family: monospace; font-size: 11px; margin-right: 6px; margin-bottom: 6px; display: inline-block;">{s}</span>'
            for s in record.skills if s.lower() not in bundle.missing_skills
        ]) or '<span style="font-size: 12px; color: #94a3b8;">None</span>'
        
        # All candidate skills badges
        all_skills_badges_html = "".join([
            f'<span style="padding: 2px 8px; border-radius: 12px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: #e2e8f0; font-family: monospace; font-size: 11px; margin-right: 6px; margin-bottom: 6px; display: inline-block;">{s.name} <span style="color: #94a3b8; font-size: 10px;">&middot; {s.proficiency}</span></span>'
            for s in record.skill_details
        ])
        
        st.markdown(clean_html(f"""
            <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px; height: 100%;">
                <div style="font-family: monospace; font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 12px;">Skill DNA &middot; required vs candidate</div>
                <div style="margin-bottom: 20px;">
                    {"".join(required_list_html)}
                </div>
                
                <div style="margin-bottom: 20px;">
                    <div style="font-family: monospace; font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px;">Preferred matches</div>
                    <div>{pref_badges_html}</div>
                </div>
                
                <div>
                    <div style="font-family: monospace; font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px;">All candidate skills</div>
                    <div>{all_skills_badges_html}</div>
                </div>
            </div>
        """), unsafe_allow_html=True)
        
    with col_right:
        # Redrob Signals list
        sig = record.redrob_signals
        
        github_icon = """<svg style="width: 12px; height: 12px; fill: currentColor;" viewBox="0 0 16 16"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>"""
        
        signals_bars_html = [
            render_signal_bar("Profile completeness", sig.profile_completeness_score),
            render_signal_bar("Recruiter response", sig.recruiter_response_rate * 100),
            render_signal_bar("Interview completion", sig.interview_completion_rate * 100),
            render_signal_bar("Github activity", sig.github_activity_score if sig.github_activity_score >= 0 else 0, icon_svg=github_icon)
        ]
        
        # Assessments
        if sig.skill_assessment_scores:
            for skill_name, score_val in sig.skill_assessment_scores.items():
                signals_bars_html.append(render_signal_bar(f"{skill_name} assessment", score_val))
                
        st.markdown(clean_html(f"""
            <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px; height: 100%;">
                <div style="font-family: monospace; font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 16px;">Redrob signals</div>
                {"".join(signals_bars_html)}
            </div>
        """), unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 5. Career Timeline
    timeline_items = []
    sorted_career = sorted(record.experience_timeline, key=lambda x: x.start_date, reverse=True)
    
    for idx, job in enumerate(sorted_career):
        warning_html = ""
        if job.duration_months < 12:
            warning_html = f'<span style="color: {COLORS["stretch"]}; font-size: 10px; font-family: monospace; margin-left: 10px;">&#9888; short tenure ({job.duration_months} mo)</span>'
            
        end_date_str = job.end_date if job.end_date else "present"
        
        timeline_items.append(clean_html(f"""
            <div style="position: relative; padding-left: 28px; margin-bottom: 24px;">
                <!-- Connector Dot -->
                <div style="position: absolute; left: -5px; top: 4px; width: 10px; height: 10px; border-radius: 50%; background: #38bdf8; box-shadow: 0 0 8px #38bdf8;"></div>
                
                <div style="display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px;">
                    <span style="font-size: 14px; font-weight: bold; color: #ffffff;">{job.title}</span>
                    <span style="font-size: 14px; color: #94a3b8;">@ {job.company}</span>
                    <span style="font-family: monospace; font-size: 10px; padding: 1px 6px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.15); color: #cbd5e1; margin-left: 6px;">{job.company_size if job.company_size else "Mid"}</span>
                </div>
                
                <div style="font-family: monospace; font-size: 11px; color: #94a3b8; margin-top: 4px;">
                    {job.start_date} &rarr; {end_date_str} &middot; {job.duration_months}mo
                    {warning_html}
                </div>
                
                {f'<div style="font-size: 12px; color: #cbd5e1; margin-top: 6px; line-height: 1.4;">{job.description}</div>' if job.description else ''}
            </div>
        """))
        
    st.markdown(clean_html(f"""
        <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
            <div style="font-family: monospace; font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 20px;">Career trajectory</div>
            <div style="position: relative; border-left: 1px solid rgba(255, 255, 255, 0.1); margin-left: 4px; padding-bottom: 1px;">
                {"".join(timeline_items)}
            </div>
        </div>
    """), unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Submission Narrative Reasoning")
    st.markdown(render_deconstructed_reasoning_html(reasoning), unsafe_allow_html=True)

def parse_reasoning(reasoning: str) -> dict[str, str]:
    parts = [p.strip() for p in reasoning.split(";")]
    res = {
        "profile": "",      # Opener & background
        "matching": "",     # asked/matching skills
        "missing": "",      # missing/ATS flag
        "adjacent": "",     # adjacent stack
        "adoption": "",     # adopted tech/adaptability
        "fit": "",          # fit comparison
        "concerns": ""      # risk/concerns
    }
    for p in parts:
        p_lower = p.lower()
        if "matching jd skills" in p_lower:
            res["matching"] = p.replace("matching JD skills include", "").strip()
        elif "keyword ats would flag missing" in p_lower or "keyword ats flag missing" in p_lower or ("missing" in p_lower and "ats" in p_lower):
            res["missing"] = p.replace("keyword ATS would flag missing", "").replace("keyword ATS flag missing", "").strip()
        elif "adjacent stack:" in p_lower:
            res["adjacent"] = p.replace("adjacent stack:", "").strip()
        elif "adopted" in p_lower and ("new tech" in p_lower or "technologies" in p_lower):
            res["adoption"] = p
        elif "fit" in p_lower and "vs" in p_lower:
            res["fit"] = p
        elif "concerns:" in p_lower:
            res["concerns"] = p.replace("concerns:", "").strip()
        else:
            if not res["profile"]:
                res["profile"] = p
            else:
                res["profile"] += "; " + p
    return res

def make_badges(skills_str: str, color_class: str) -> str:
    if not skills_str or skills_str.strip().lower() in ["none", ""]:
        return '<span style="color: #64748b; font-style: italic; font-size: 11px;">None</span>'
    
    # Split by comma
    skills = [s.strip() for s in skills_str.split(",") if s.strip()]
    if not skills:
        return '<span style="color: #64748b; font-style: italic; font-size: 11px;">None</span>'
        
    bg = "rgba(34, 197, 94, 0.08)" if color_class == "green" else "rgba(239, 68, 68, 0.08)" if color_class == "red" else "rgba(245, 158, 11, 0.08)"
    text_color = "#4ade80" if color_class == "green" else "#f87171" if color_class == "red" else "#fbbf24"
    border = "rgba(34, 197, 94, 0.25)" if color_class == "green" else "rgba(239, 68, 68, 0.25)" if color_class == "red" else "rgba(245, 158, 11, 0.25)"
    
    badges = []
    for s in skills:
        badges.append(f'<span style="display: inline-block; background: {bg}; color: {text_color}; border: 1px solid {border}; border-radius: 4px; padding: 2px 8px; margin-right: 6px; margin-bottom: 6px; font-size: 11px; font-family: monospace; font-weight: 500;">{s}</span>')
    return "".join(badges)

def render_deconstructed_reasoning_html(reasoning: str) -> str:
    parsed = parse_reasoning(reasoning)
    
    matching_html = make_badges(parsed["matching"], "green")
    missing_html = make_badges(parsed["missing"], "red")
    adjacent_html = make_badges(parsed["adjacent"], "yellow")
    
    adoption_html = ""
    if parsed["adoption"]:
        adoption_html = f"""
        <div style="display: flex; align-items: center; gap: 6px;">
            <span style="color: #c084fc; font-size: 14px;">⚡</span>
            <span style="color: #cbd5e1; font-weight: 500;">{parsed["adoption"]}</span>
        </div>
        """
        
    fit_html = ""
    if parsed["fit"]:
        fit_html = f"""
        <div style="display: flex; align-items: center; gap: 6px;">
            <span style="color: #38bdf8; font-size: 14px;">📈</span>
            <span style="color: #cbd5e1; font-weight: 500;">{parsed["fit"]}</span>
        </div>
        """
        
    concerns_html = ""
    if parsed["concerns"]:
        concerns_html = f"""
        <div style="display: flex; align-items: center; gap: 6px; margin-left: auto;">
            <span style="color: #f87171; font-size: 14px;">⚠️</span>
            <span style="color: #fca5a5; font-weight: 500;">Risk: {parsed["concerns"]}</span>
        </div>
        """
        
    html = f"""
    <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 14px; margin-top: 10px; font-family: sans-serif;">
        <div style="font-family: monospace; font-size: 10.5px; color: #38bdf8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 12px; font-weight: bold; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 6px; display: flex; align-items: center; gap: 6px;">
            🧬 DECISION DECONSTRUCTION (ADVAIT.CSV REASONING SPEC)
        </div>
        
        <div style="font-size: 12.5px; color: #cbd5e1; line-height: 1.4; margin-bottom: 12px; padding: 8px 12px; background: rgba(255,255,255,0.02); border-radius: 6px; border-left: 3px solid #38bdf8; font-style: italic;">
            "{parsed["profile"]}"
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 12px;">
            <!-- Asked Skills -->
            <div style="background: rgba(34, 197, 94, 0.03); border: 1px solid rgba(34, 197, 94, 0.12); border-radius: 8px; padding: 8px 10px;">
                <div style="font-size: 9px; color: #4ade80; font-family: monospace; font-weight: bold; letter-spacing: 1px; margin-bottom: 6px;">🟢 ASKED (MATCHING JD)</div>
                {matching_html}
            </div>
            
            <!-- Missing Skills -->
            <div style="background: rgba(239, 68, 68, 0.03); border: 1px solid rgba(239, 68, 68, 0.12); border-radius: 8px; padding: 8px 10px;">
                <div style="font-size: 9px; color: #f87171; font-family: monospace; font-weight: bold; letter-spacing: 1px; margin-bottom: 6px;">🔴 MISSING (ATS FLAG)</div>
                {missing_html}
            </div>
            
            <!-- Adjacent Stack -->
            <div style="background: rgba(245, 158, 11, 0.03); border: 1px solid rgba(245, 158, 11, 0.12); border-radius: 8px; padding: 8px 10px;">
                <div style="font-size: 9px; color: #fbbf24; font-family: monospace; font-weight: bold; letter-spacing: 1px; margin-bottom: 6px;">🟡 ADJACENT (TRANSFERABLE)</div>
                {adjacent_html}
            </div>
        </div>
        
        <div style="display: flex; flex-wrap: wrap; gap: 16px; border-top: 1px solid rgba(255, 255, 255, 0.06); padding-top: 8px; font-size: 11px;">
            {adoption_html}
            {fit_html}
            {concerns_html}
        </div>
    </div>
    """
    return "\n".join(line.strip() for line in html.splitlines())


