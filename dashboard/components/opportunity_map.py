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
    import plotly.graph_objects as go
    import pandas as pd

    df = df.copy()

    df["s_current"] = pd.to_numeric(df["s_current"], errors="coerce")
    df["future_fit"] = pd.to_numeric(df["future_fit"], errors="coerce")

    all_quadrants = [
        "Safe Hire",
        "Hidden Gem",
        "Overrated",
        "Unaligned",
    ]

    COLORS = {
        "Safe Hire": "#22c55e",   # green
        "Hidden Gem": "#a855f7",  # purple
        "Overrated": "#f59e0b",   # orange
        "Unaligned": "#60a5fa",   # bright blue
    }

    fig = go.Figure()

    for quadrant in all_quadrants:
        qdf = df[df["quadrant"] == quadrant]

        if len(qdf) == 0:
            continue

        fig.add_trace(
            go.Scatter(
                x=qdf["s_current"],
                y=qdf["future_fit"],
                mode="markers",
                name=quadrant,
                text=qdf["candidate_id"],
                marker=dict(
                    size=12,
                    color=COLORS[quadrant],
                    opacity=0.9,
                    line=dict(
                        color="white",
                        width=1,
                    ),
                ),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Current Fit: %{x:.2f}<br>"
                    "Future Fit: %{y:.2f}<br>"
                    "<extra></extra>"
                ),
            )
        )

    # Highlight selected candidate
    if selected_id and selected_id in set(df["candidate_id"]):
        row = df[df["candidate_id"] == selected_id].iloc[0]

        fig.add_trace(
            go.Scatter(
                x=[row["s_current"]],
                y=[row["future_fit"]],
                mode="markers",
                name="Selected",
                marker=dict(
                    size=18,
                    color="#ef4444",
                    line=dict(
                        color="white",
                        width=3,
                    ),
                ),
                hoverinfo="skip",
            )
        )

    # Quadrant lines
    fig.add_hline(
        y=50,
        line_dash="dash",
        line_color="#cbd5e1",
        line_width=1,
    )

    fig.add_vline(
        x=50,
        line_dash="dash",
        line_color="#cbd5e1",
        line_width=1,
    )

    # Quadrant labels
    fig.add_annotation(
        x=75,
        y=75,
        text="Safe Hire",
        showarrow=False,
    )

    fig.add_annotation(
        x=25,
        y=75,
        text="Hidden Gem",
        showarrow=False,
    )

    fig.add_annotation(
        x=75,
        y=25,
        text="Overrated",
        showarrow=False,
    )

    fig.add_annotation(
        x=25,
        y=25,
        text="Unaligned",
        showarrow=False,
    )

    fig.update_layout(
        title="Talent Opportunity Map",
        height=600,
        xaxis_title="Current Fit",
        yaxis_title="Future Fit",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(
            l=40,
            r=20,
            t=60,
            b=40,
        ),
    )

    return fig
