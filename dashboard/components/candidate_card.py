"""ATS Failed vs TalentDNA Selected contrast card."""

from __future__ import annotations

import streamlit as st

from src.explainability import contrast_card
from src.models import CandidateRecord, ScoreBundle


def render_contrast_card(record: CandidateRecord, bundle: ScoreBundle, reasoning: str) -> None:
    card = contrast_card(record, bundle)
    st.subheader(f"{card['name']} — {card['title']}")
    st.caption(f"Quadrant: **{card['quadrant']}** | Rank #{getattr(bundle, 'rank', '—')}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Why ATS Failed")
        st.metric("Current Fit", f"{card['ats_failed']['current_fit']:.0f}%")
        missing = card["ats_failed"]["missing_keywords"]
        if missing:
            st.write("Missing keywords:", ", ".join(missing[:5]))
        else:
            st.write("Keyword overlap looks strong — ATS might pass this profile.")

    with col_b:
        st.markdown("#### Why TalentDNA Selected")
        sel = card["talentdna_selected"]
        st.metric("Future Fit", f"{sel['future_fit']:.0f}%")
        st.metric("Hidden Gem Score", f"{sel['hidden_gem']:.1f}")
        if sel["adjacent_skills"]:
            st.write("Adjacent stack:", ", ".join(sel["adjacent_skills"]))
        st.write(
            f"Adaptability: {sel['adaptability_count']} new tech signals | "
            f"Onboarding: ~{sel['onboarding_weeks']}"
        )
        st.write(f"Opportunity index: {sel['opportunity_index']:.1f}")

    st.markdown("**Reasoning (submission style)**")
    st.info(reasoning)
