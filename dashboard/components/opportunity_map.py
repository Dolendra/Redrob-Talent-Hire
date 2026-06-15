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
    import pandas as pd
    import plotly.graph_objects as go

    st.error("OPPORTUNITY MAP FILE EXECUTED")

    # =========================
    # DEBUG SECTION
    # =========================

    st.write("Rows in opportunity map:", len(df))

    st.subheader("Raw Data Preview")
    st.dataframe(
        df[
            [
                "candidate_id",
                "s_current",
                "future_fit",
                "quadrant"
            ]
        ].head(20)
    )

    # Force numeric conversion
    df = df.copy()

    df["s_current"] = pd.to_numeric(
        df["s_current"],
        errors="coerce"
    )

    df["future_fit"] = pd.to_numeric(
        df["future_fit"],
        errors="coerce"
    )

    st.subheader("Data Types")
    st.write(
        df[
            ["s_current", "future_fit"]
        ].dtypes
    )

    st.subheader("Null Counts")
    st.write(
        df[
            ["s_current", "future_fit"]
        ].isna().sum()
    )

    st.subheader("Statistics")
    st.dataframe(
        df[
            ["s_current", "future_fit"]
        ].describe()
    )

    # =========================
    # QUADRANTS
    # =========================

    all_quadrants = [
        "Safe Hire",
        "Hidden Gem",
        "Overrated",
        "Unaligned"
    ]

    fig = go.Figure()

    st.subheader("Plotly Trace Debug")

    for quadrant in all_quadrants:

        qdf = df[
            df["quadrant"] == quadrant
        ]

        st.write(
            f"{quadrant}: {len(qdf)} candidates"
        )

        fig.add_trace(
            go.Scatter(
                x=qdf["s_current"],
                y=qdf["future_fit"],
                mode="markers",
                name=quadrant,
                text=qdf["candidate_id"],
                marker=dict(
                    size=18,
                    opacity=1,
                    line=dict(
                        width=2,
                        color="white"
                    )
                ),
                hovertemplate=
                "<b>%{text}</b><br>"
                "Current Fit: %{x}<br>"
                "Future Fit: %{y}<extra></extra>"
            )
        )

    st.write("Total traces:", len(fig.data))

    for i, trace in enumerate(fig.data):
        st.write(
            f"Trace {i}: {trace.name} | Points: {len(trace.x)}"
        )

    # =========================
    # SELECTED CANDIDATE
    # =========================

    if (
        selected_id
        and selected_id in set(df["candidate_id"])
    ):
        row = df[
            df["candidate_id"] == selected_id
        ].iloc[0]

        fig.add_trace(
            go.Scatter(
                x=[row["s_current"]],
                y=[row["future_fit"]],
                mode="markers",
                name="Selected",
                marker=dict(
                    size=22,
                    color="red",
                    line=dict(
                        width=3,
                        color="white"
                    )
                )
            )
        )

    # =========================
    # GUIDE LINES
    # =========================

    fig.add_hline(
        y=50,
        line_dash="dash",
        line_color="white"
    )

    fig.add_vline(
        x=50,
        line_dash="dash",
        line_color="white"
    )

    fig.add_annotation(
        x=75,
        y=75,
        text="Safe Hire",
        showarrow=False
    )

    fig.add_annotation(
        x=25,
        y=75,
        text="Hidden Gem",
        showarrow=False
    )

    fig.add_annotation(
        x=75,
        y=25,
        text="Overrated",
        showarrow=False
    )

    fig.add_annotation(
        x=25,
        y=25,
        text="Unaligned",
        showarrow=False
    )

    fig.update_layout(
        title="Talent Opportunity Map",
        height=600,
        xaxis_title="Current Fit",
        yaxis_title="Future Fit",
        showlegend=True
    )

    return fig
