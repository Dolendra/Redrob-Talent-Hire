"""Plotly Talent Opportunity Map — Current Fit × Future Fit."""

from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd


QUADRANT_COLORS = {
    "Safe Hire": "#22c55e",
    "Hidden Gem": "#a855f7",
    "Overrated": "#f59e0b",
    "Unaligned": "#94a3b8",
}


def build_opportunity_map(df: pd.DataFrame, selected_id: str | None = None) -> go.Figure:
    df = df.copy()

    df["s_current"] = pd.to_numeric(df["s_current"], errors="coerce")
    df["future_fit"] = pd.to_numeric(df["future_fit"], errors="coerce")

    all_quadrants = [
        "Safe Hire",
        "Hidden Gem",
        "Overrated",
        "Unaligned",
    ]

    fig = go.Figure()

    # Loop through quadrants and build traces manually with debug prints
    for quadrant in all_quadrants:
        qdf = df[df["quadrant"] == quadrant]

        # Debug prints as requested
        print(f"Quadrant: {quadrant}")
        print(qdf[["s_current", "future_fit"]].head())

        hover_text = []
        for _, row in qdf.iterrows():
            hover_text.append(
                f"quadrant={quadrant}<br>"
                f"Current Fit={row['s_current']:.2f}<br>"
                f"Future Fit={row['future_fit']:.2f}<br>"
                f"candidate_id={row['candidate_id']}<br>"
                f"rank={row['rank']}<br>"
                f"score={row['score']}<br>"
                f"hidden_gem={row['hidden_gem']:.2f}"
            )

        x_vals = qdf["s_current"].tolist() if not qdf.empty else []
        y_vals = qdf["future_fit"].tolist() if not qdf.empty else []
        c_ids = qdf["candidate_id"].tolist() if not qdf.empty else []

        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="markers",
                name=quadrant,
                text=hover_text,
                hoverinfo="text" if hover_text else "skip",
                customdata=c_ids,
                marker=dict(
                    size=12,
                    color=QUADRANT_COLORS[quadrant],
                    opacity=0.9,
                    line=dict(
                        color="white",
                        width=1,
                    ),
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
        font=dict(size=11, color="#64748b"),
    )

    fig.add_annotation(
        x=25,
        y=75,
        text="Hidden Gem",
        showarrow=False,
        font=dict(size=11, color="#64748b"),
    )

    fig.add_annotation(
        x=75,
        y=25,
        text="Overrated",
        showarrow=False,
        font=dict(size=11, color="#64748b"),
    )

    fig.add_annotation(
        x=25,
        y=25,
        text="Unaligned",
        showarrow=False,
        font=dict(size=11, color="#64748b"),
    )

    fig.update_layout(
        title="Talent Opportunity Map",
        height=600,
        xaxis=dict(title="Current Fit", range=[20, 80]),
        yaxis=dict(title="Future Fit", range=[20, 80]),
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

def build_tree_opportunity_map(df: pd.DataFrame) -> go.Figure:
    import plotly.express as px
    df = df.copy()
    
    # Handle empty DataFrame case safely
    if df.empty:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_annotation(
            text="No candidates available to display in Tree Opportunity Map",
            showarrow=False,
            font=dict(size=14, color="#94a3b8")
        )
        return fig
        
    df["Future Fit Score"] = df["future_fit"].round(1)
    df["Current Fit Score"] = df["s_current"].round(1)
    df["Rank"] = df["rank"]
    
    fig = px.treemap(
        df,
        path=["quadrant", "title", "name"],
        values="future_fit",
        color="quadrant",
        color_discrete_map=QUADRANT_COLORS,
        custom_data=["Rank", "Current Fit Score", "Future Fit Score", "candidate_id"]
    )
    
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br><br>"
                      "Rank: #%{customdata[0]}<br>"
                      "Candidate ID: %{customdata[3]}<br>"
                      "Current Fit Score: %{customdata[1]}%<br>"
                      "Future Fit Score: %{customdata[2]}%<br>"
                      "<extra></extra>"
    )
    
    fig.update_layout(
        margin=dict(t=40, l=10, r=10, b=10),
        height=650,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff")
    )
    return fig

