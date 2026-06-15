"""ATS Failed vs Redrob-Talent-Hire Selected contrast card (Visual Persona Card)."""

from __future__ import annotations

import streamlit as st
from src.models import CandidateRecord, ScoreBundle


def get_candidate_archetype(record: CandidateRecord, bundle: ScoreBundle) -> str:
    """Classify candidate into a memorable recruiter archetype."""
    # 1. Gather all texts from profile and timeline
    texts = [record.profile.headline or "", record.profile.summary or ""]
    for entry in record.experience_timeline:
        texts.append(entry.title or "")
        texts.append(entry.description or "")
    full_text = " ".join(texts).lower()

    # 2. Score text against archetype keywords
    researcher_words = ["research", "publication", "academic", "phd", "paper", "arxiv", "scientific", "thesis", "researcher"]
    researcher_count = sum(full_text.count(w) for w in researcher_words)

    scaler_words = ["scale", "cluster", "optim", "high load", "throughput", "latency", "performance", "distributed", "concurrency", "bottleneck"]
    scaler_count = sum(full_text.count(w) for w in scaler_words)

    builder_words = ["architect", "initiate", "migrate", "design", "built", "develop", "create", "launch", "prototype", "builder", "implemented"]
    builder_count = sum(full_text.count(w) for w in builder_words)

    if researcher_count > max(scaler_count, builder_count, 2):
        return "🔬 THE RESEARCHER"
    elif scaler_count > max(researcher_count, builder_count, 2):
        return "⚡ THE SCALER"
    elif builder_count > max(researcher_count, scaler_count, 2):
        return "🚀 THE BUILDER"
    elif bundle.adaptability_count >= 5:
        return "🧬 THE SHAPESHIFTER"
    else:
        if record.profile.years_of_experience >= 8:
            return "🛡️ THE VETERAN"
        else:
            return "🌟 THE SHIPPER"


def get_skill_evolution_timeline(record: CandidateRecord) -> list[tuple[int, list[str]]]:
    """Extract a chronological timeline of when unique skills were first used in their roles."""
    def parse_start_year(entry_start: str) -> int:
        try:
            return int(entry_start.split("-")[0])
        except (ValueError, IndexError):
            return 2020

    timeline = sorted(record.experience_timeline, key=lambda e: parse_start_year(e.start_date))
    year_to_skills: dict[int, set[str]] = {}

    for entry in timeline:
        year = parse_start_year(entry.start_date)
        entry_text = ((entry.title or "") + " " + (entry.description or "")).lower()

        matched = []
        for s in record.skills:
            if s.lower() in entry_text:
                matched.append(s)

        if matched:
            if year not in year_to_skills:
                year_to_skills[year] = set()
            year_to_skills[year].update(matched)

    evolution = []
    seen_skills = set()
    for y in sorted(year_to_skills.keys()):
        y_skills = year_to_skills[y]
        new_skills = [s for s in y_skills if s not in seen_skills]
        if new_skills:
            evolution.append((y, new_skills[:3]))
            seen_skills.update(new_skills)

    return evolution


def render_contrast_card(record: CandidateRecord, bundle: ScoreBundle, reasoning: str) -> None:
    """Render the candidate information as a premium visual persona card."""
    # Classify candidate and gather details
    archetype = get_candidate_archetype(record, bundle)
    evolution = get_skill_evolution_timeline(record)

    # Format timeline HTML
    timeline_nodes = []
    for year, skills in evolution:
        skills_str = ", ".join(skills)
        timeline_nodes.append(f'<div class="timeline-node"><b>{year}</b>: {skills_str}</div>')

    if not timeline_nodes:
        skills = record.skills
        if len(skills) >= 6:
            timeline_nodes.append(f'<div class="timeline-node"><b>Core</b>: {", ".join(skills[:3])}</div>')
            timeline_nodes.append(f'<div class="timeline-node"><b>Support</b>: {", ".join(skills[3:6])}</div>')
        elif skills:
            timeline_nodes.append(f'<div class="timeline-node"><b>Skills</b>: {", ".join(skills[:5])}</div>')
        else:
            timeline_nodes.append('<div class="timeline-node">No skill history found</div>')

    timeline_html = ' <span class="timeline-arrow">──&gt;</span> '.join(timeline_nodes)

    # Build executive bullets
    bullets = []
    if bundle.missing_skills:
        bullets.append(f"Lacks explicit <b>{', '.join(bundle.missing_skills[:2])}</b> keyword tags (causes standard ATS rejection).")
    else:
        bullets.append("Excellent raw keyword overlap with the JD required skills.")

    if bundle.adjacent_skills:
        bullets.append(f"Identified strong sibling skill adjacency: <b>{', '.join(bundle.adjacent_skills[:2])}</b>, minimizing tech transition friction.")
    else:
        bullets.append("General adjacent tech stack aligns well with the requirements.")

    if bundle.adaptability_count >= 3:
        bullets.append(f"Demonstrates high learning adaptability, adopting <b>{bundle.adaptability_count}</b> new technologies across recent roles.")
    elif bundle.cv_norm >= 60:
        bullets.append("High Career Velocity score indicates fast promotional history and ownership growth.")
    else:
        bullets.append("Stable career progression with consistent longevity in team environments.")

    bullets_html = "".join([f"<li>{b}</li>" for b in bullets])

    # Determine Recruiter Action Simulation status
    if bundle.hiring_risk < 30:
        risk_label = "LOW"
        risk_color = "🟢"
        risk_class = "text-green"
    elif bundle.hiring_risk < 60:
        risk_label = "MEDIUM"
        risk_color = "🟡"
        risk_class = "text-yellow"
    else:
        risk_label = "HIGH"
        risk_color = "🔴"
        risk_class = "text-red"

    if bundle.hiring_risk < 60 and bundle.opportunity >= 40:
        action_text = "🟢 CALL NEXT (High Priority)"
        action_class = "action-yes"
    elif bundle.hiring_risk < 60 and bundle.opportunity >= 20:
        action_text = "🟡 CALL (Standard Priority)"
        action_class = "action-maybe"
    else:
        action_text = "🔴 PASS (Review Later)"
        action_class = "action-pass"

    # Check for Hidden Gem banner
    hidden_gem_banner_html = ""
    if bundle.quadrant == "Hidden Gem":
        hidden_gem_banner_html = """
        <div class="hidden-gem-banner">
            <span>🚀 HIDDEN GEM DETECTED: IMMENSE FUTURE FIT WITH MODEST KEYWORD ALIGNMENT</span>
        </div>
        """

    # HTML Output
    html = f"""
    <style>
        .persona-card {{
            background: linear-gradient(135deg, #151528 0%, #0d0d1a 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            color: #e2e8f0;
            padding: 24px;
            margin: 16px 0;
            overflow: hidden;
        }}
        .hidden-gem-banner {{
            background: linear-gradient(90deg, #7c3aed 0%, #db2777 100%);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 10px;
            color: #ffffff;
            font-weight: 800;
            text-align: center;
            padding: 12px;
            margin-bottom: 20px;
            font-size: 0.9rem;
            letter-spacing: 0.05em;
            box-shadow: 0 0 20px rgba(124, 58, 237, 0.4);
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.01); }}
            100% {{ transform: scale(1); }}
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding-bottom: 16px;
            margin-bottom: 20px;
        }}
        .candidate-meta {{
            display: flex;
            flex-direction: column;
        }}
        .candidate-id {{
            font-size: 0.8rem;
            color: #94a3b8;
            letter-spacing: 0.05em;
            font-weight: 600;
        }}
        .candidate-name {{
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(90deg, #3b82f6, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .archetype-badge {{
            background: rgba(168, 85, 247, 0.15);
            border: 1px solid rgba(168, 85, 247, 0.3);
            color: #d8b4fe;
            font-weight: 700;
            font-size: 0.85rem;
            padding: 6px 14px;
            border-radius: 9999px;
            box-shadow: 0 0 15px rgba(168, 85, 247, 0.25);
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: 1.2fr 0.8fr;
            gap: 24px;
            margin-bottom: 24px;
        }}
        @media (max-width: 768px) {{
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        .heatmap-section h3, 
        .timeline-section h3, 
        .summary-section h3 {{
            font-size: 0.85rem;
            font-weight: 700;
            color: #64748b;
            letter-spacing: 0.1em;
            margin-top: 0;
            margin-bottom: 12px;
        }}
        .progress-item {{
            margin-bottom: 16px;
        }}
        .label-row {{
            display: flex;
            justify-content: space-between;
            font-size: 0.9rem;
            margin-bottom: 6px;
        }}
        .progress-bar-container {{
            height: 8px;
            background: rgba(255, 255, 255, 0.06);
            border-radius: 4px;
            overflow: hidden;
        }}
        .progress-bar-fill {{
            height: 100%;
            border-radius: 4px;
        }}
        .technical-fill {{
            background: linear-gradient(90deg, #ef4444, #f59e0b);
        }}
        .velocity-fill {{
            background: linear-gradient(90deg, #3b82f6, #06b6d4);
        }}
        .confidence-fill {{
            background: linear-gradient(90deg, #10b981, #3b82f6);
        }}
        .badges-section {{
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 12px;
        }}
        .info-badge {{
            display: flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 12px;
        }}
        .badge-icon {{
            font-size: 1.5rem;
            margin-right: 12px;
        }}
        .badge-text {{
            display: flex;
            flex-direction: column;
        }}
        .badge-label {{
            font-size: 0.75rem;
            color: #64748b;
        }}
        .badge-value {{
            font-size: 0.95rem;
            font-weight: 600;
            color: #f1f5f9;
        }}
        .text-green {{ color: #10b981; }}
        .text-yellow {{ color: #f59e0b; }}
        .text-red {{ color: #ef4444; }}
        
        .timeline-section {{
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            padding-top: 20px;
            margin-bottom: 24px;
        }}
        .timeline-flow {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 10px;
            padding: 16px;
            border: 1px solid rgba(255, 255, 255, 0.03);
        }}
        .timeline-node {{
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.25);
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.85rem;
            color: #93c5fd;
        }}
        .timeline-arrow {{
            color: #475569;
            font-weight: bold;
        }}
        .summary-section {{
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            padding-top: 20px;
            margin-bottom: 24px;
        }}
        .summary-bullets {{
            list-style: none;
            padding-left: 0;
            margin: 0;
        }}
        .summary-bullets li {{
            position: relative;
            padding-left: 20px;
            margin-bottom: 8px;
            font-size: 0.95rem;
            line-height: 1.5;
            color: #cbd5e1;
        }}
        .summary-bullets li::before {{
            content: "•";
            position: absolute;
            left: 0;
            color: #a855f7;
            font-weight: bold;
            font-size: 1.2rem;
            top: -2px;
        }}
        .action-banner {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 20px;
            border-radius: 10px;
            font-weight: 700;
            letter-spacing: 0.02em;
            font-size: 0.95rem;
        }}
        .action-yes {{
            background: linear-gradient(90deg, rgba(16, 185, 129, 0.15) 0%, rgba(59, 130, 246, 0.15) 100%);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #34d399;
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.1);
        }}
        .action-maybe {{
            background: linear-gradient(90deg, rgba(245, 158, 11, 0.15) 0%, rgba(59, 130, 246, 0.15) 100%);
            border: 1px solid rgba(245, 158, 11, 0.3);
            color: #fbbf24;
            box-shadow: 0 0 15px rgba(245, 158, 11, 0.1);
        }}
        .action-pass {{
            background: rgba(239, 68, 68, 0.12);
            border: 1px solid rgba(239, 68, 68, 0.25);
            color: #fca5a5;
        }}
    </style>

    <div class="persona-card">
        {hidden_gem_banner_html}
        <div class="card-header">
            <div class="candidate-meta">
                <span class="candidate-id">ID: {candidate_id}</span>
                <span class="candidate-name">{name}</span>
            </div>
            <div class="archetype-badge">{archetype}</div>
        </div>
        
        <div class="card-body">
            <div class="metrics-grid">
                <div class="heatmap-section">
                    <h3>TALENT DNA HEATMAP</h3>
                    
                    <div class="progress-item">
                        <div class="label-row">
                            <span>Technical Fit (Current ATS)</span>
                            <span>{bundle.s_current:.0f}%</span>
                        </div>
                        <div class="progress-bar-container">
                            <div class="progress-bar-fill technical-fill" style="width: {bundle.s_current}%"></div>
                        </div>
                    </div>
                    
                    <div class="progress-item">
                        <div class="label-row">
                            <span>Future Fit (Adjacency &amp; Trajectory)</span>
                            <span>{bundle.future_fit:.0f}%</span>
                        </div>
                        <div class="progress-bar-container">
                            <div class="progress-bar-fill velocity-fill" style="width: {bundle.future_fit}%"></div>
                        </div>
                    </div>
                    
                    <div class="progress-item">
                        <div class="label-row">
                            <span>Confidence Score</span>
                            <span>{bundle.confidence:.0f}%</span>
                        </div>
                        <div class="progress-bar-container">
                            <div class="progress-bar-fill confidence-fill" style="width: {bundle.confidence}%"></div>
                        </div>
                    </div>
                </div>
                
                <div class="badges-section">
                    <div class="info-badge">
                        <div class="badge-icon">🕒</div>
                        <div class="badge-text">
                            <span class="badge-label">Time-to-Productivity</span>
                            <span class="badge-value">{bundle.onboarding_weeks}</span>
                        </div>
                    </div>
                    
                    <div class="info-badge">
                        <div class="badge-icon">💎</div>
                        <div class="badge-text">
                            <span class="badge-label">Interview Value (Opp. Cost)</span>
                            <span class="badge-value">{bundle.opportunity:.1f} / 100</span>
                        </div>
                    </div>
                    
                    <div class="info-badge">
                        <div class="badge-icon">{risk_color}</div>
                        <div class="badge-text">
                            <span class="badge-label">Hiring Risk</span>
                            <span class="badge-value"><span class="{risk_class}">{risk_label}</span> ({bundle.hiring_risk:.0f}%)</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="timeline-section">
                <h3>SKILL EVOLUTION TIMELINE</h3>
                <div class="timeline-flow">
                    {timeline_html}
                </div>
            </div>
            
            <div class="summary-section">
                <h3>EXECUTIVE TL;DR REPORT</h3>
                <ul class="summary-bullets">
                    {bullets_html}
                </ul>
            </div>
            
            <div class="action-banner {action_class}">
                <span class="action-label">RECRUITER ACTION SIMULATOR:</span>
                <span class="action-value">{action_text}</span>
            </div>
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)
    
    st.markdown("**Reasoning (submission style)**")
    st.info(reasoning)
