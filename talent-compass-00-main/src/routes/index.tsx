import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import {
  Briefcase,
  Sparkles,
  Users,
  Gauge,
  ArrowUpRight,
  Plus,
} from "lucide-react";

import { useCandidates, useJobs, useHydrated } from "@/lib/store";
import { scoreCandidate, quadrantOf } from "@/lib/scoring/engine";
import { PageHeader } from "@/components/talent/page-header";
import { KpiCard } from "@/components/talent/kpi-card";
import { TalentOpportunityMap } from "@/components/talent/opportunity-map";
import { QuadrantBadge, RecommendationBadge } from "@/components/talent/badges";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard · TalentDNA" },
      {
        name: "description",
        content:
          "Recruiter command center. Track open requisitions, surface hidden gems and triage your candidate pipeline.",
      },
      { property: "og:title", content: "Dashboard · TalentDNA" },
    ],
  }),
  component: DashboardPage,
});

function DashboardPage() {
  const hydrated = useHydrated();
  const jobs = useJobs();
  const candidates = useCandidates();
  const [activeJobId, setActiveJobId] = useState<string | undefined>(undefined);
  const navigate = useNavigate();

  const activeJob = jobs.find((j) => j.id === activeJobId) ?? jobs[0];




  const scored = useMemo(() => {
    if (!activeJob) return [];
    return candidates
      .map((c) => ({ c, s: scoreCandidate(c, activeJob), q: quadrantOf(scoreCandidate(c, activeJob)) }))
      .sort((a, b) => b.s.futureFit - a.s.futureFit);
  }, [candidates, activeJob]);

  const gems = scored.filter((x) => x.q === "gem").sort((a, b) => b.s.hiddenGem - a.s.hiddenGem);
  const safe = scored.filter((x) => x.q === "safe");
  const avgFuture =
    scored.length > 0
      ? Math.round(scored.reduce((acc, x) => acc + x.s.futureFit, 0) / scored.length)
      : 0;

  return (
    <div>
      <PageHeader
        eyebrow={`Live · ${jobs.length} requisitions`}
        title={
          <>
            Recruiter <span className="text-gradient-primary">Command Center</span>
          </>
        }
        description="One pane for every open role. Click any point on the Talent Opportunity Map to open that candidate's TalentDNA report."
        actions={
          <Button asChild className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-[var(--shadow-glow-primary)]">
            <Link to="/jobs/new">
              <Plus className="h-4 w-4 mr-1" /> New Job
            </Link>
          </Button>
        }
      />

      <div className="px-6 lg:px-10 py-6 space-y-6">
        {/* KPI strip */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="Active requisitions"
            value={jobs.length}
            hint="across teams"
            icon={<Briefcase className="h-4 w-4" />}
          />
          <KpiCard
            label="Tracked candidates"
            value={candidates.length.toLocaleString()}
            delta="+12 this week"
            icon={<Users className="h-4 w-4" />}
          />
          <KpiCard
            label="Hidden gems surfaced"
            value={gems.length}
            hint="missed by ATS"
            accent="gem"
            icon={<Sparkles className="h-4 w-4" />}
          />
          <KpiCard
            label="Pool avg Future Fit"
            value={avgFuture}
            hint="for selected JD"
            accent="safe"
            icon={<Gauge className="h-4 w-4" />}
          />
        </div>

        {/* Main grid */}
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-6">
          {/* Opportunity map */}
          <div className="surface-card rounded-xl p-5">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <div className="text-[10px] uppercase tracking-[0.22em] font-mono text-muted-foreground">
                  Talent Opportunity Map
                </div>
                <h2 className="font-display text-lg font-semibold mt-1">
                  {activeJob?.title ?? "Select a job"}
                </h2>
                <p className="text-xs text-muted-foreground mt-1">
                  {safe.length} safe hires · <span className="text-gem">{gems.length} hidden gems</span> ·{" "}
                  {scored.length} candidates plotted
                </p>
              </div>
              <Select value={activeJob?.id} onValueChange={(v) => setActiveJobId(v)}>
                <SelectTrigger className="w-[260px]">
                  <SelectValue placeholder="Select requisition" />
                </SelectTrigger>
                <SelectContent>
                  {jobs.map((j) => (
                    <SelectItem key={j.id} value={j.id}>
                      {j.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {activeJob && hydrated ? (
              <TalentOpportunityMap jd={activeJob} candidates={candidates} />
            ) : (
              <div className="h-[460px] grid-bg rounded-md animate-pulse" />
            )}
          </div>

          {/* Hidden gems panel */}
          <div className="surface-card rounded-xl p-5 flex flex-col">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="text-[10px] uppercase tracking-[0.22em] font-mono text-gem">
                  ◆ Hidden gems
                </div>
                <h2 className="font-display text-lg font-semibold mt-1">
                  Why ATS missed these
                </h2>
              </div>
            </div>

            <div className="space-y-3 flex-1">
              {hydrated && gems.length === 0 && (
                <div className="text-sm text-muted-foreground border border-dashed border-border rounded-md p-4">
                  No hidden gems in this pool yet. Upload more candidates or relax the JD's required skills.
                </div>
              )}
              {gems.slice(0, 5).map(({ c, s }) => (
                <button
                  key={c.id}
                  className="group w-full text-left rounded-lg border border-border/60 hover:border-gem/60 bg-background/40 p-3 transition"
                  onClick={() =>
                    navigate({
                      to: "/jobs/$jobId/candidates/$candidateId",
                      params: { jobId: activeJob!.id, candidateId: c.id },
                    })
                  }
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="font-medium text-sm truncate">{c.name}</div>
                      <div className="text-xs text-muted-foreground truncate">{c.headline}</div>
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-gem transition" />
                  </div>
                  <div className="mt-3 flex items-center gap-2 flex-wrap">
                    <RecommendationBadge value={s.recommendation} />
                    <QuadrantBadge q="gem" />
                    <div className="ml-auto font-mono text-[11px] text-muted-foreground">
                      ATS <span className="text-destructive">{c.atsScore}</span>
                      <span className="mx-1">→</span>
                      DNA <span className="text-gem">{s.futureFit}</span>
                    </div>
                  </div>
                  {s.whyAtsMissed[0] && (
                    <div className="mt-2 text-[11px] text-muted-foreground line-clamp-2">
                      {s.whyAtsMissed[0]}
                    </div>
                  )}
                </button>
              ))}
            </div>

            {activeJob && (
              <Button asChild variant="ghost" className="mt-3 justify-between">
                <Link to="/jobs/$jobId" params={{ jobId: activeJob.id }}>
                  View full ranking
                  <ArrowUpRight className="h-4 w-4" />
                </Link>
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
