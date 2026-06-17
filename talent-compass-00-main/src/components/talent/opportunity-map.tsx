import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ReferenceArea,
  ReferenceLine,
  Cell,
} from "recharts";
import { useNavigate } from "@tanstack/react-router";

import type { Candidate } from "@/lib/scoring/types";
import { quadrantOf, scoreCandidate } from "@/lib/scoring/engine";
import type { JobDescription } from "@/lib/scoring/types";

interface MapProps {
  jd: JobDescription;
  candidates: Candidate[];
}

const QUADRANT_COLOR = {
  safe: "var(--color-safe)",
  gem: "var(--color-gem)",
  stretch: "var(--color-stretch)",
  pass: "var(--color-pass)",
} as const;

export function TalentOpportunityMap({ jd, candidates }: MapProps) {
  const navigate = useNavigate();

  const data = candidates.map((c) => {
    const s = scoreCandidate(c, jd);
    const q = quadrantOf(s);
    return {
      x: s.currentFit,
      y: s.futureFit,
      z: 40 + s.confidence * 120,
      name: c.name,
      headline: c.headline,
      candidateId: c.id,
      quadrant: q,
      hidden: s.hiddenGem,
      atsScore: c.atsScore,
      recommendation: s.recommendation,
    };
  });

  return (
    <div className="relative w-full h-[460px]">
      {/* Quadrant labels */}
      <div className="pointer-events-none absolute inset-0 z-10 grid grid-cols-2 grid-rows-2 text-[10px] uppercase tracking-[0.2em] font-mono">
        <div className="p-3 flex items-start text-gem/80">◆ Hidden Gems</div>
        <div className="p-3 flex items-start justify-end text-safe/80">✓ Safe Hires</div>
        <div className="p-3 flex items-end text-muted-foreground">· Pass</div>
        <div className="p-3 flex items-end justify-end text-stretch/80">↗ Stretch</div>
      </div>

      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 24, right: 24, bottom: 36, left: 24 }}>
          <CartesianGrid stroke="var(--color-grid-line)" strokeDasharray="2 4" />
          <ReferenceArea x1={0} x2={60} y1={70} y2={100} fill="var(--color-gem)" fillOpacity={0.06} />
          <ReferenceArea x1={60} x2={100} y1={70} y2={100} fill="var(--color-safe)" fillOpacity={0.06} />
          <ReferenceLine x={60} stroke="var(--color-grid-line)" />
          <ReferenceLine y={70} stroke="var(--color-grid-line)" />
          <XAxis
            type="number"
            dataKey="x"
            domain={[0, 100]}
            tick={{ fill: "var(--color-muted-foreground)", fontSize: 11, fontFamily: "var(--font-mono)" }}
            stroke="var(--color-border)"
            label={{
              value: "Current Fit →",
              position: "insideBottom",
              offset: -16,
              fill: "var(--color-muted-foreground)",
              fontSize: 11,
              fontFamily: "var(--font-mono)",
            }}
          />
          <YAxis
            type="number"
            dataKey="y"
            domain={[0, 100]}
            tick={{ fill: "var(--color-muted-foreground)", fontSize: 11, fontFamily: "var(--font-mono)" }}
            stroke="var(--color-border)"
            label={{
              value: "Future Fit ↑",
              angle: -90,
              position: "insideLeft",
              fill: "var(--color-muted-foreground)",
              fontSize: 11,
              fontFamily: "var(--font-mono)",
            }}
          />
          <ZAxis type="number" dataKey="z" range={[60, 280]} />
          <Tooltip
            cursor={{ strokeDasharray: "3 3", stroke: "var(--color-primary)" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const p = payload[0].payload;
              return (
                <div className="surface-card rounded-md px-3 py-2 text-xs min-w-[200px]">
                  <div className="font-medium text-sm">{p.name}</div>
                  <div className="text-muted-foreground text-[11px]">{p.headline}</div>
                  <div className="mt-2 grid grid-cols-2 gap-y-1 font-mono">
                    <span className="text-muted-foreground">Current</span>
                    <span className="text-right tabular-nums">{Math.round(p.x)}</span>
                    <span className="text-muted-foreground">Future</span>
                    <span className="text-right tabular-nums">{Math.round(p.y)}</span>
                    <span className="text-muted-foreground">ATS</span>
                    <span className="text-right tabular-nums">{p.atsScore}</span>
                    <span className="text-muted-foreground">Gem score</span>
                    <span className="text-right tabular-nums text-gem">{Math.round(p.hidden)}</span>
                  </div>
                </div>
              );
            }}
          />
          <Scatter
            data={data}
            onClick={(d: unknown) => {
              const p = d as { candidateId?: string; payload?: { candidateId: string } };
              const id = p.candidateId ?? p.payload?.candidateId;
              if (!id) return;
              navigate({
                to: "/jobs/$jobId/candidates/$candidateId",
                params: { jobId: jd.id, candidateId: id },
              });
            }}
          >
            {data.map((d, i) => (
              <Cell
                key={i}
                fill={QUADRANT_COLOR[d.quadrant]}
                stroke={d.quadrant === "gem" ? "var(--color-gem)" : "transparent"}
                strokeWidth={d.quadrant === "gem" ? 2 : 0}
                fillOpacity={d.quadrant === "pass" ? 0.5 : 0.85}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
