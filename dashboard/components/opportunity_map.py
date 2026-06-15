"""Plotly Talent Opportunity Map — Current Fit × Future Fit."""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


QUADRANT_COLORS = {
    "Safe Hire": "#22c55e",
    "Hidden Gem": "#a855f7",
    "Overrated": "#f59e0b",
    "Unaligned": "#94a3b8",
}


def build_opportunity_map(df: pd.DataFrame, selected_id: str | None = None) -> go.Figure:

    import streamlit as st

    st.error("OPPORTUNITY MAP FILE EXECUTED")

    import streamlit as st

    st.write("Rows in opportunity map:", len(df))
    
    st.dataframe(
        df[["candidate_id", "s_current", "future_fit", "quadrant"]]
    )
    # Ensure all 4 quadrants are represented in the DataFrame so they always show in the legend
    print("===== OPPORTUNITY MAP =====")
    print("Rows:", len(df))
    print("Columns:", df.columns.tolist())

    try:
        print(df[["candidate_id", "s_current", "future_fit", "quadrant"]].head(20))
    except Exception as e:
        print("Error printing dataframe:", e)

    print("===========================")

    
    all_quadrants = ["Safe Hire", "Hidden Gem", "Overrated", "Unaligned"]
    present_quadrants = set(df["quadrant"].dropna().unique())
    missing_quadrants = [q for q in all_quadrants if q not in present_quadrants]
    
    if missing_quadrants:
        ghost_rows = pd.DataFrame([
            {
                "s_current": None,
                "future_fit": None,
                "quadrant": q,
                "candidate_id": f"GHOST_{i}",
                "rank": None,
                "score": None,
                "hidden_gem": None,
            }
            for i, q in enumerate(missing_quadrants)
        ])
        df = pd.concat([df, ghost_rows], ignore_index=True)

    fig = px.scatter(
        df,
        x="s_current",
        y="future_fit",
        color="quadrant",
        color_discrete_map=QUADRANT_COLORS,
        category_orders={"quadrant": all_quadrants},
        hover_data=["candidate_id", "rank", "score", "hidden_gem"],
        custom_data=["candidate_id"],
        labels={"s_current": "Current Fit", "future_fit": "Future Fit"},
        title="Talent Opportunity Map",
        height=520,
        render_mode="svg",
    )
    fig.add_hline(y=50, line_dash="dash", line_color="#cbd5e1", line_width=1)
    fig.add_vline(x=50, line_dash="dash", line_color="#cbd5e1", line_width=1)
    fig.add_annotation(x=75, y=75, text="Safe Hire", showarrow=False, font=dict(size=11, color="#64748b"))
    fig.add_annotation(x=25, y=75, text="Hidden Gem", showarrow=False, font=dict(size=11, color="#64748b"))
    fig.add_annotation(x=75, y=25, text="Overrated", showarrow=False, font=dict(size=11, color="#64748b"))
    fig.add_annotation(x=25, y=25, text="Unaligned", showarrow=False, font=dict(size=11, color="#64748b"))

    if selected_id and selected_id in set(df["candidate_id"]):
        row = df[df["candidate_id"] == selected_id].iloc[0]
        fig.add_trace(
            go.Scatter(
                x=[row["s_current"]],
                y=[row["future_fit"]],
                mode="markers",
                marker=dict(size=16, color="#ef4444", line=dict(width=2, color="white")),
                name="Selected",
                hoverinfo="skip",
            )
        )
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return fig
