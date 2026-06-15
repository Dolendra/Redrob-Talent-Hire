"""ATS Failed vs Redrob-Talent-Hire Selected contrast card."""

from __future__ import annotations

import streamlit as st

from src.explainability import contrast_card
from src.models import CandidateRecord, ScoreBundle


def render_contrast_card(record: CandidateRecord, bundle: ScoreBundle, reasoning: str) -> None:
    card = contrast_card(record, bundle)
    st.subheader(f"{card['name']} — {card['title']}")
    st.caption(f"Quadrant: **{card['quadrant']}** | Rank #{getattr(bundle, 'rank', '—')}")

    sel = card["talentdna_selected"]
    current_fit_val = card['ats_failed']['current_fit']
    future_fit_val = sel['future_fit']

    st.markdown("### Match Summary & Analytics")
    col1, col2, col3, col4 = st.columns(4)
    
    # 1. Current Fit
    col1.metric(
        label="Current Fit Score", 
        value=f"{current_fit_val:.0f}%", 
        delta="Keyword Dropoff" if current_fit_val < 50 else "Strong Keyword Match", 
        delta_color="inverse" if current_fit_val < 50 else "normal"
    )
    
    # 2. Future Fit
    adj_boost = int(future_fit_val - current_fit_val)
    col2.metric(
        label="Future Fit Score", 
        value=f"{future_fit_val:.0f}%", 
        delta=f"+{adj_boost}% Adjacency Boost" if adj_boost > 0 else f"{adj_boost}% Difference"
    )
    
    # 3. Hidden Gem Rating
    hg_val = float(sel['hidden_gem'])
    col3.metric(
        label="Hidden Gem Rating", 
        value=f"{hg_val:.1f}", 
        delta="Top Trajectory" if hg_val > 100 else "Standard Trajectory"
    )
    
    # 4. Estimated Onboarding
    onboarding = sel['onboarding_weeks']
    col4.metric(
        label="Estimated Onboarding", 
        value=onboarding, 
        delta="Low Friction" if onboarding in ["2 weeks", "4-6 weeks"] else "High Friction",
        delta_color="normal" if onboarding in ["2 weeks", "4-6 weeks"] else "inverse"
    )

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Why ATS Failed")
        missing = card["ats_failed"]["missing_keywords"]
        if missing:
            st.markdown(f"❌ **Missing keywords:** {', '.join(missing[:5])}")
        else:
            st.markdown("✅ **Keyword overlap looks strong** — ATS would pass this profile.")

    with col_b:
        st.markdown("#### Why Redrob-Talent-Hire Selected")
        if sel["adjacent_skills"]:
            st.markdown(f"🌟 **Adjacent stack:** {', '.join(sel['adjacent_skills'])}")
        st.markdown(
            f"💡 **Adaptability:** {sel['adaptability_count']} new tech signals | "
            f"📈 **Opportunity index:** {sel['opportunity_index']:.1f}"
        )

    st.markdown("#### Reasoning (submission style)")
    st.info(reasoning)
