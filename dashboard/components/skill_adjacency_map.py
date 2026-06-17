"""Skill Adjacency Map Component - Visualizes JD skills matching coverage (Direct vs Adjacent vs Gap)."""

from __future__ import annotations
import streamlit as st

SKILL_ADJACENCY: dict[str, list[str]] = {
    "kubernetes": ["docker", "helm", "terraform", "aws ecs", "containerd"],
    "docker": ["kubernetes", "podman", "containerd", "ci/cd"],
    "terraform": ["aws", "gcp", "azure", "pulumi", "ansible"],
    "react": ["next.js", "remix", "vue", "svelte", "typescript"],
    "next.js": ["react", "remix", "tanstack start", "vercel"],
    "typescript": ["javascript", "react", "node.js"],
    "python": ["fastapi", "django", "flask", "pandas", "numpy"],
    "pytorch": ["tensorflow", "jax", "numpy", "python"],
    "tensorflow": ["pytorch", "keras", "jax", "python"],
    "pandas": ["numpy", "python", "polars", "spark"],
    "node.js": ["typescript", "express", "fastify", "nest.js"],
    "postgres": ["mysql", "sqlite", "supabase", "sql"],
    "aws": ["gcp", "azure", "terraform", "cloudformation"],
    "graphql": ["rest", "apollo", "trpc"],
    "rust": ["go", "c++", "wasm"],
    "go": ["rust", "java", "c++"],
    "langchain": ["llamaindex", "openai api", "python", "rag"],
    "rag": ["langchain", "vector db", "embeddings", "openai api"],
    "vector db": ["pinecone", "weaviate", "qdrant", "pgvector"],
    "spark": ["hadoop", "pandas", "scala", "databricks"],
    "airflow": ["dagster", "prefect", "luigi"],
    "fastapi": ["flask", "django", "python", "starlette"],
}

def clean_html(html: str) -> str:
    return "\n".join(line.strip() for line in html.splitlines())


def get_adjacent_skills(skill: str) -> list[str]:
    return SKILL_ADJACENCY.get(skill.lower(), [])

def render_skill_adjacency_map(jd_required: list[str], jd_preferred: list[str], candidates: list[dict]) -> None:
    """Renders the HTML-based stacked bar visualization for skill coverage."""
    total = max(len(candidates), 1)
    
    rows = []
    
    # Process required and preferred skills
    for skill, kind in ([(s, "required") for s in jd_required] + [(s, "preferred") for s in jd_preferred]):
        key = skill.lower()
        neighbors = get_adjacent_skills(key)
        
        direct_count = 0
        adjacent_count = 0
        adjacent_by = set()
        
        for c in candidates:
            c_skills = set()
            for s in c.get("skills", []):
                if isinstance(s, dict) and "name" in s:
                    c_skills.add(s["name"].lower())
                elif isinstance(s, str):
                    c_skills.add(s.lower())
            
            if key in c_skills:
                direct_count += 1
            else:
                hits = [n for n in neighbors if n in c_skills]
                if hits:
                    adjacent_count += 1
                    for h in hits:
                        adjacent_by.add(h)
                        
        coverage_pct = ((direct_count + adjacent_count) / total) * 100
        direct_pct = (direct_count / total) * 100
        adj_pct = (adjacent_count / total) * 100
        gap_pct = 100 - direct_pct - adj_pct
        
        rows.append({
            "skill": skill,
            "kind": kind,
            "direct_count": direct_count,
            "adjacent_count": adjacent_count,
            "adjacent_by": list(adjacent_by)[:6],
            "direct_pct": direct_pct,
            "adj_pct": adj_pct,
            "gap_pct": gap_pct,
            "coverage_pct": coverage_pct
        })
        
    if not rows:
        st.markdown(
            '<div style="font-size: 13px; color: #94a3b8; border: 1px dashed rgba(255,255,255,0.08); padding: 16px; border-radius: 8px;">'
            'No skills defined on this job yet.'
            '</div>', 
            unsafe_allow_html=True
        )
        return

    # Legend HTML
    legend_html = """
    <div style="display: flex; gap: 20px; font-family: monospace; font-size: 11px; color: #94a3b8; margin-bottom: 15px;">
        <div style="display: flex; items-center: center; gap: 6px;">
            <span style="display: inline-block; width: 10px; height: 10px; border-radius: 2px; background: #22c55e;"></span>
            <span>Direct match</span>
        </div>
        <div style="display: flex; items-center: center; gap: 6px;">
            <span style="display: inline-block; width: 10px; height: 10px; border-radius: 2px; background: #fbbf24;"></span>
            <span>Adjacent bridge</span>
        </div>
        <div style="display: flex; items-center: center; gap: 6px;">
            <span style="display: inline-block; width: 10px; height: 10px; border-radius: 2px; background: rgba(255,255,255,0.1);"></span>
            <span>Gap</span>
        </div>
    </div>
    """
    
    # Rows rendering HTML
    rows_html = []
    for r in rows:
        kind_color = "#38bdf8" if r["kind"] == "required" else "#fbbf24"
        
        bridges_html = ""
        if r["adjacent_by"]:
            badges = "".join([
                f'<span style="padding: 1px 6px; border-radius: 4px; background: rgba(251, 191, 36, 0.1); border: 1px solid rgba(251, 191, 36, 0.3); color: #fbbf24; font-size: 9px; margin-right: 5px;">{b}</span>'
                for b in r["adjacent_by"]
            ])
            bridges_html = f"""
            <div style="grid-column: 1 / -1; margin-left: 172px; margin-top: -4px; font-size: 10px; color: #94a3b8; font-family: monospace;">
                <span style="margin-right: 6px;">bridges via:</span>
                {badges}
            </div>
            """
            
        row_style = f"""
        <div style="display: grid; grid-template-columns: 160px 1fr 120px; gap: 12px; align-items: center; margin-bottom: 12px;">
            <!-- Skill info -->
            <div style="min-width: 0;">
                <div style="font-family: monospace; font-size: 13px; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{r['skill']}</div>
                <div style="font-family: monospace; font-size: 10px; text-transform: uppercase; color: {kind_color}; letter-spacing: 1px;">{r['kind']}</div>
            </div>
            
            <!-- Progress Bar -->
            <div style="position: relative; height: 24px; border-radius: 6px; overflow: hidden; border: 1px solid rgba(255, 255, 255, 0.08); background: rgba(15, 23, 42, 0.4);">
                <div style="position: absolute; top: 0; bottom: 0; left: 0; width: {r['direct_pct']}%; background: rgba(34, 197, 94, 0.7);" title="{r['direct_count']} direct matches"></div>
                <div style="position: absolute; top: 0; bottom: 0; left: {r['direct_pct']}%; width: {r['adj_pct']}%; background: rgba(251, 191, 36, 0.7);" title="{r['adjacent_count']} adjacent bridges"></div>
                <div style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px; font-family: monospace; font-size: 10px; color: rgba(255, 255, 255, 0.9); pointer-events: none;">
                    {r['coverage_pct']:.0f}% covered
                </div>
            </div>
            
            <!-- Counter details -->
            <div style="font-family: monospace; font-size: 12px; text-align: right; color: #94a3b8;">
                <span style="color: #22c55e;">{r['direct_count']}</span>
                <span> + </span>
                <span style="color: #fbbf24;">{r['adjacent_count']}</span>
                <span> / {total}</span>
            </div>
            
            <!-- Adjacency details -->
            {bridges_html}
        </div>
        """
        rows_html.append(row_style)
        
    full_html = f"""
    <div style="display: flex; flex-direction: column;">
        {legend_html}
        {"".join(rows_html)}
    </div>
    """
    
    st.markdown(clean_html(full_html), unsafe_allow_html=True)
