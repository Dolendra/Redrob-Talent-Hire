import { useMemo } from "react";

import type { Candidate, JobDescription } from "@/lib/scoring/types";
import { getAdjacentSkills } from "@/lib/scoring/skillAdjacency";

interface Props {
  jd: JobDescription;
  candidates: Candidate[];
}

type Row = {
  skill: string;
  kind: "required" | "preferred";
  directCount: number;
  adjacentCount: number;
  adjacentBy: string[];
  coverage: number; // 0..1
};

/**
 * Skill Adjacency Visualization — for every JD skill, show how many
 * candidates have it directly and how many have a structurally adjacent
 * skill. Visualises the "bridge skills" that ATS systems miss.
 */
export function SkillAdjacencyMap({ jd, candidates }: Props) {
  const rows = useMemo<Row[]>(() => {
    const total = Math.max(candidates.length, 1);
    const build = (skill: string, kind: "required" | "preferred"): Row => {
      const key = skill.toLowerCase();
      const neighbors = getAdjacentSkills(key);
      let direct = 0;
      let adjacent = 0;
      const adjacentBy = new Set<string>();
      for (const c of candidates) {
        const set = new Set(c.skills.map((s) => s.name.toLowerCase()));
        if (set.has(key)) {
          direct++;
        } else {
          const hit = neighbors.filter((n) => set.has(n));
          if (hit.length > 0) {
            adjacent++;
            hit.forEach((h) => adjacentBy.add(h));
          }
        }
      }
      return {
        skill,
        kind,
        directCount: direct,
        adjacentCount: adjacent,
        adjacentBy: Array.from(adjacentBy).slice(0, 6),
        coverage: (direct + adjacent) / total,
      };
    };
    return [
      ...jd.requiredSkills.map((s) => build(s, "required")),
      ...jd.preferredSkills.map((s) => build(s, "preferred")),
    ];
  }, [jd, candidates]);

  if (rows.length === 0) {
    return (
      <div className="text-xs text-muted-foreground border border-dashed border-border rounded-md p-4">
        No skills defined on this job yet.
      </div>
    );
  }

  const total = Math.max(candidates.length, 1);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4 text-[10px] uppercase tracking-[0.2em] font-mono text-muted-foreground">
        <LegendDot color="var(--color-safe)" label="Direct match" />
        <LegendDot color="var(--color-gem)" label="Adjacent bridge" />
        <LegendDot color="var(--color-border)" label="Gap" />
      </div>

      <div className="space-y-2">
        {rows.map((r) => {
          const directPct = (r.directCount / total) * 100;
          const adjPct = (r.adjacentCount / total) * 100;
          const gapPct = 100 - directPct - adjPct;
          return (
            <div key={`${r.kind}-${r.skill}`} className="grid grid-cols-[160px_1fr_120px] gap-3 items-center">
              <div className="min-w-0">
                <div className="font-mono text-xs truncate">{r.skill}</div>
                <div
                  className={`text-[10px] uppercase tracking-wider font-mono ${
                    r.kind === "required" ? "text-primary" : "text-gem"
                  }`}
                >
                  {r.kind}
                </div>
              </div>

              <div className="relative h-6 rounded-md overflow-hidden border border-border/60 bg-background/40">
                <div
                  className="absolute inset-y-0 left-0 bg-safe/70"
                  style={{ width: `${directPct}%` }}
                  title={`${r.directCount} direct matches`}
                />
                <div
                  className="absolute inset-y-0 bg-gem/70"
                  style={{ left: `${directPct}%`, width: `${adjPct}%` }}
                  title={`${r.adjacentCount} adjacent bridges`}
                />
                <div className="absolute inset-0 flex items-center justify-end pr-2 font-mono text-[10px] text-foreground/80">
                  {Math.round((directPct + adjPct))}% covered
                </div>
                {gapPct > 0 && (
                  <div
                    className="absolute inset-y-0 right-0 bg-muted/30"
                    style={{ width: `${gapPct}%` }}
                  />
                )}
              </div>

              <div className="font-mono text-[11px] text-right">
                <span className="text-safe">{r.directCount}</span>
                <span className="text-muted-foreground"> + </span>
                <span className="text-gem">{r.adjacentCount}</span>
                <span className="text-muted-foreground"> / {total}</span>
              </div>

              {r.adjacentBy.length > 0 && (
                <div className="col-span-3 -mt-1 ml-[172px] flex flex-wrap items-center gap-1.5 text-[10px] font-mono text-muted-foreground">
                  <span>bridges via:</span>
                  {r.adjacentBy.map((b) => (
                    <span
                      key={b}
                      className="px-1.5 py-0.5 rounded bg-gem/10 border border-gem/30 text-gem"
                    >
                      {b}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="h-2 w-2 rounded-sm" style={{ background: color }} />
      <span>{label}</span>
    </div>
  );
}
