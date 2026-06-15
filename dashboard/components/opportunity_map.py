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
    fig = go.Figure()

    # Add reference lines and annotations
    fig.add_hline(y=50, line_dash="dash", line_color="#cbd5e1", line_width=1)
    fig.add_vline(x=50, line_dash="dash", line_color="#cbd5e1", line_width=1)
    fig.add_annotation(x=75, y=75, text="Safe Hire", showarrow=False, font=dict(size=11, color="#64748b"))
    fig.add_annotation(x=25, y=75, text="Hidden Gem", showarrow=False, font=dict(size=11, color="#64748b"))
    fig.add_annotation(x=75, y=25, text="Overrated", showarrow=False, font=dict(size=11, color="#64748b"))
    fig.add_annotation(x=25, y=25, text="Unaligned", showarrow=False, font=dict(size=11, color="#64748b"))

    all_quadrants = ["Safe Hire", "Hidden Gem", "Overrated", "Unaligned"]

    # Loop through quadrants and build traces manually with debug prints
    for quadrant in all_quadrants:
        qdf = df[df["quadrant"] == quadrant]
        
        # Debug prints as requested
        print(f"Quadrant: {quadrant}")
        print(qdf[["s_current", "future_fit"]].head())

        x_vals = qdf["s_current"].tolist() if not qdf.empty else []
        y_vals = qdf["future_fit"].tolist() if not qdf.empty else []
        
        hover_text = []
        for _, row in qdf.iterrows():
            hover_text.append(
                f"candidate_id: {row['candidate_id']}<br>"
                f"rank: {row['rank']}<br>"
                f"score: {row['score']}<br>"
                f"hidden_gem: {row['hidden_gem']}"
            )

        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="markers",
                marker=dict(
                    color=QUADRANT_COLORS[quadrant],
                    size=8,
                ),
                name=quadrant,
                text=hover_text,
                hoverinfo="text" if hover_text else "skip",
            )
        )

    # Add Selected Candidate highlight
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
        title="Talent Opportunity Map",
        xaxis=dict(title="Current Fit", range=[20, 80]),
        yaxis=dict(title="Future Fit", range=[20, 80]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
        height=520,
    )
    return fig
