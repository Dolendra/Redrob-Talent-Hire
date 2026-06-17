import { createFileRoute, Link, useParams } from "@tanstack/react-router";
import { ArrowLeft, Sparkles, AlertTriangle, Clock, TrendingUp, Github } from "lucide-react";
import { useMemo } from "react";

import { useCandidate, useJob } from "@/lib/store";
import { scoreCandidate } from "@/lib/scoring/engine";
import { PageHeader } from "@/components/talent/page-header";
import { ScoreGauge } from "@/components/talent/score-gauge";
import { RecommendationBadge } from "@/components/talent/badges";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/jobs/$jobId/candidates/$candidateId")({
  head: () => ({
    meta: [
      { title: "TalentDNA Report" },
      { name: "description", content: "30-second TalentDNA report for this candidate." },
    ],
  }),
  component: CandidateReport,
});

function CandidateReport() {
  const { jobId, candidateId } = useParams({
    from: "/jobs/$jobId/candidates/$candidateId",
  });
  const job = useJob(jobId);
  const cand = useCandidate(candidateId);

  const score = useMemo(() => (cand && job ? scoreCandidate(cand, job) : undefined), [cand, job]);

  if (!cand || !job || !score) {
    return (
      <div className="p-10">
        <p className="text-sm text-muted-foreground">Candidate or job not found.</p>
        <Button asChild variant="link" className="mt-2">
          <Link to="/">Back to dashboard</Link>
        </Button>
      </div>
    );
  }

  const recVariant =
    score.recommendation === "strong_hire" ? "safe" : score.recommendation === "consider" ? "stretch" : "pass";

  return (
    <div>
      <PageHeader
        eyebrow={`${job.title} · ${job.company}`}
        title={
          <span className="flex items-center gap-3 flex-wrap">
            {cand.name}
            <RecommendationBadge value={score.recommendation} />
          </span>
        }
        description={`${cand.headline} · ${cand.location} · ${cand.yearsOfExperience}y experience`}
        actions={
          <Button variant="ghost" asChild>
            <Link to="/jobs/$jobId" params={{ jobId: job.id }}>
              <ArrowLeft className="h-4 w-4 mr-1" /> Back to pool
            </Link>
          </Button>
        }
      />

      <div className="px-6 lg:px-10 py-6 space-y-6">
        {/* HERO: gauges + ATS vs DNA */}
        <div className="grid grid-cols-1 lg:grid-cols-[auto_auto_1fr] gap-6 surface-card rounded-xl p-6">
          <ScoreGauge value={score.currentFit} label="Current Fit" sublabel="direct skill match" variant="primary" size="lg" />
          <ScoreGauge value={score.futureFit} label="Future Fit" sublabel="with adjacency & velocity" variant={recVariant} size="lg" />
          <div className="flex flex-col justify-center min-w-0">
            <div className="text-[10px] uppercase tracking-[0.22em] font-mono text-gem mb-2">
              Why ATS missed this candidate
            </div>
            <div className="flex items-center gap-4 mb-4">
              <div>
                <div className="text-[10px] font-mono uppercase text-muted-foreground">ATS</div>
                <div className="font-display text-3xl font-semibold text-destructive tabular-nums">
                  {cand.atsScore}
                </div>
              </div>
              <div className="text-2xl text-muted-foreground">→</div>
              <div>
                <div className="text-[10px] font-mono uppercase text-muted-foreground">TalentDNA</div>
                <div className={cn("font-display text-3xl font-semibold tabular-nums", score.futureFit > cand.atsScore ? "text-gem" : "text-foreground")}>
                  {score.futureFit}
                </div>
              </div>
              <div className="ml-4 text-xs font-mono text-muted-foreground">
                <span className={score.futureFit > cand.atsScore ? "text-gem" : ""}>
                  {score.futureFit > cand.atsScore ? "+" : ""}
                  {score.futureFit - cand.atsScore}
                </span>{" "}
                point delta
              </div>
            </div>
            <ul className="space-y-2">
              {score.whyAtsMissed.map((line, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <Sparkles className="h-4 w-4 text-gem mt-0.5 shrink-0" />
                  <span className="text-foreground/90">{line}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Secondary stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard
            icon={<TrendingUp className="h-4 w-4" />}
            label="Growth Velocity"
            value={`${Math.round(score.growthVelocity * 100)}%`}
            hint={score.growthVelocity >= 0.7 ? "top quartile" : score.growthVelocity >= 0.5 ? "above average" : "steady"}
            accent={score.growthVelocity >= 0.7 ? "safe" : score.growthVelocity >= 0.5 ? "primary" : "stretch"}
          />
          <StatCard
            icon={<AlertTriangle className="h-4 w-4" />}
            label="Risk Score"
            value={score.riskScore}
            hint={
              score.riskScore >= 60
                ? "elevated risk"
                : score.riskScore >= 30
                ? "moderate"
                : "low risk"
            }
            accent={score.riskScore >= 60 ? "stretch" : score.riskScore >= 30 ? "primary" : "safe"}
            breakdown={[
              { label: "Job hopping", value: Math.min(60, cand.career.filter((e) => e.durationMonths < 12).length * 20) },
              { label: "Ghosting", value: Math.round((1 - cand.signals.recruiterResponseRate) * 40) },
              { label: "Drop-off", value: Math.round((1 - cand.signals.interviewCompletionRate) * 40) },
            ]}
          />
          <StatCard
            icon={<Clock className="h-4 w-4" />}
            label="Onboarding cost"
            value={`${score.onboardingWeeks}w`}
            hint="weeks to productivity"
            accent={score.onboardingWeeks <= 3 ? "safe" : score.onboardingWeeks <= 6 ? "primary" : "stretch"}
          />
        </div>

        {/* Skills adjacency + signals */}
        <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-6">
          <div className="surface-card rounded-xl p-5">
            <div className="text-[10px] uppercase tracking-[0.22em] font-mono text-muted-foreground mb-3">
              Skill DNA · required vs candidate
            </div>
            <div className="space-y-2.5">
              {job.requiredSkills.map((req) => {
                const matched = score.matchedRequired.includes(req.toLowerCase());
                const bridge = score.adjacentBridges.find((b) => b.missing === req.toLowerCase());
                return (
                  <div
                    key={req}
                    className={cn(
                      "flex items-center gap-3 p-2.5 rounded-md border",
                      matched
                        ? "border-safe/40 bg-safe/5"
                        : bridge
                        ? "border-gem/40 bg-gem/5"
                        : "border-destructive/30 bg-destructive/5",
                    )}
                  >
                    <span
                      className={cn(
                        "h-2 w-2 rounded-full shrink-0",
                        matched ? "bg-safe" : bridge ? "bg-gem" : "bg-destructive",
                      )}
                    />
                    <span className="font-mono text-sm">{req}</span>
                    <div className="ml-auto text-xs text-muted-foreground font-mono">
                      {matched ? (
                        <span className="text-safe">direct match</span>
                      ) : bridge ? (
                        <span className="text-gem">≈ {bridge.bridges.slice(0, 3).join(", ")}</span>
                      ) : (
                        <span className="text-destructive">not found</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {score.matchedPreferred.length > 0 && (
              <div className="mt-5">
                <div className="text-[10px] uppercase tracking-[0.22em] font-mono text-muted-foreground mb-2">
                  Preferred matches
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {score.matchedPreferred.map((p) => (
                    <Badge key={p} variant="outline" className="bg-gem/10 border-gem/40 text-gem font-mono">
                      {p}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-5">
              <div className="text-[10px] uppercase tracking-[0.22em] font-mono text-muted-foreground mb-2">
                All candidate skills
              </div>
              <div className="flex flex-wrap gap-1.5">
                {cand.skills.map((s) => (
                  <Badge key={s.name} variant="outline" className="font-mono text-xs">
                    {s.name}
                    <span className="ml-1 text-muted-foreground">· {s.proficiency}</span>
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          <div className="surface-card rounded-xl p-5">
            <div className="text-[10px] uppercase tracking-[0.22em] font-mono text-muted-foreground mb-3">
              Redrob signals
            </div>
            <div className="space-y-3">
              <SignalBar label="Profile completeness" value={cand.signals.profileCompleteness} max={100} />
              <SignalBar label="Recruiter response" value={cand.signals.recruiterResponseRate * 100} max={100} />
              <SignalBar label="Interview completion" value={cand.signals.interviewCompletionRate * 100} max={100} />
              <SignalBar
                label="Github activity"
                value={cand.signals.githubActivityScore}
                max={100}
                icon={<Github className="h-3 w-3" />}
              />
              {cand.signals.assessmentScores.codingProficiency != null && (
                <SignalBar
                  label="Coding assessment"
                  value={cand.signals.assessmentScores.codingProficiency}
                  max={100}
                />
              )}
              {cand.signals.assessmentScores.systemDesign != null && (
                <SignalBar
                  label="System design"
                  value={cand.signals.assessmentScores.systemDesign}
                  max={100}
                />
              )}
            </div>
          </div>
        </div>

        {/* Career timeline */}
        <div className="surface-card rounded-xl p-5">
          <div className="text-[10px] uppercase tracking-[0.22em] font-mono text-muted-foreground mb-4">
            Career trajectory
          </div>
          <div className="relative pl-6 border-l border-border space-y-5">
            {[...cand.career]
              .sort((a, b) => b.startDate.localeCompare(a.startDate))
              .map((e, i) => (
                <div key={i} className="relative">
                  <div className="absolute -left-[28px] top-1.5 h-3 w-3 rounded-full bg-primary shadow-[0_0_12px_var(--color-primary)]" />
                  <div className="flex flex-wrap items-baseline gap-x-2">
                    <span className="font-medium text-sm">{e.title}</span>
                    <span className="text-muted-foreground text-sm">@ {e.company}</span>
                    <Badge variant="outline" className="font-mono text-[10px] ml-1">
                      {e.level}
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground font-mono mt-0.5">
                    {e.startDate} → {e.endDate} · {e.durationMonths}mo
                    {e.durationMonths < 12 && (
                      <span className="ml-2 text-stretch">⚠ short tenure</span>
                    )}
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  hint,
  accent,
  breakdown,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  hint?: string;
  accent: "primary" | "gem" | "safe" | "stretch";
  breakdown?: { label: string; value: number }[];
}) {
  const accentText = {
    primary: "text-primary",
    gem: "text-gem",
    safe: "text-safe",
    stretch: "text-stretch",
  }[accent];
  return (
    <div className="surface-card rounded-xl p-5">
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.22em] font-mono text-muted-foreground">
        <span className={accentText}>{icon}</span>
        {label}
      </div>
      <div className={cn("font-display text-3xl font-semibold mt-2 tabular-nums", accentText)}>
        {value}
      </div>
      {hint && <div className="text-xs text-muted-foreground mt-1">{hint}</div>}
      {breakdown && (
        <div className="mt-3 space-y-1.5 pt-3 border-t border-border/60">
          {breakdown.map((b) => (
            <div key={b.label} className="flex items-center justify-between text-xs font-mono">
              <span className="text-muted-foreground">{b.label}</span>
              <span className="tabular-nums">{b.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SignalBar({
  label,
  value,
  max,
  icon,
}: {
  label: string;
  value: number;
  max: number;
  icon?: React.ReactNode;
}) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1.5">
        <span className="flex items-center gap-1.5 text-muted-foreground">
          {icon}
          {label}
        </span>
        <span className="font-mono tabular-nums">{Math.round(value)}</span>
      </div>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className={cn(
            "h-full transition-all duration-700",
            pct >= 75 ? "bg-safe" : pct >= 50 ? "bg-primary" : pct >= 25 ? "bg-stretch" : "bg-destructive",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
