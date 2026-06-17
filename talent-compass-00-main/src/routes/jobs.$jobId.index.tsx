import { createFileRoute, Link, useNavigate, useParams } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { ArrowLeft, Filter, Search, ArrowUpRight, FileJson, FileDown } from "lucide-react";
import { toast } from "sonner";

import { useCandidates, useJob } from "@/lib/store";
import { scoreCandidate, quadrantOf } from "@/lib/scoring/engine";
import { exportJobJson, exportJobPdf } from "@/lib/export";
import { PageHeader } from "@/components/talent/page-header";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { QuadrantBadge, RecommendationBadge } from "@/components/talent/badges";
import { TalentOpportunityMap } from "@/components/talent/opportunity-map";
import { SkillAdjacencyMap } from "@/components/talent/skill-adjacency-map";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

export const Route = createFileRoute("/jobs/$jobId/")({
  head: () => ({
    meta: [
      { title: "Job · TalentDNA" },
      { name: "description", content: "Ranked candidate pool for this requisition." },
    ],
  }),
  component: JobPage,
  notFoundComponent: () => (
    <div className="p-10 text-sm text-muted-foreground">Job not found.</div>
  ),
});

function JobPage() {
  const { jobId } = useParams({ from: "/jobs/$jobId/" });
  const job = useJob(jobId);
  const candidates = useCandidates();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<"all" | "safe" | "gem" | "stretch" | "pass">("all");

  const scored = useMemo(() => {
    if (!job) return [];
    return candidates
      .map((c) => {
        const s = scoreCandidate(c, job);
        return { c, s, q: quadrantOf(s) };
      })
      .filter((x) => filter === "all" || x.q === filter)
      .filter((x) => {
        if (!q.trim()) return true;
        const t = q.toLowerCase();
        return (
          x.c.name.toLowerCase().includes(t) ||
          x.c.headline.toLowerCase().includes(t) ||
          x.c.skills.some((s) => s.name.toLowerCase().includes(t))
        );
      })
      .sort((a, b) => b.s.futureFit - a.s.futureFit);
  }, [candidates, job, q, filter]);

  if (!job) {
    return (
      <div className="p-10">
        <p className="text-sm text-muted-foreground">Job not found.</p>
        <Button asChild variant="link" className="mt-2">
          <Link to="/">Back to dashboard</Link>
        </Button>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        eyebrow={`${job.company} · ${job.location}`}
        title={job.title}
        description={job.description || "No description provided."}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                exportJobJson(job, candidates);
                toast.success("JSON summary downloaded");
              }}
            >
              <FileJson className="h-4 w-4 mr-1" /> JSON
            </Button>
            <Button
              size="sm"
              className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-[var(--shadow-glow-primary)]"
              onClick={() => {
                exportJobPdf(job, candidates);
                toast.success("PDF report downloaded");
              }}
            >
              <FileDown className="h-4 w-4 mr-1" /> Export PDF
            </Button>
            <Button variant="ghost" asChild>
              <Link to="/">
                <ArrowLeft className="h-4 w-4 mr-1" /> Dashboard
              </Link>
            </Button>
          </div>
        }
      />

      <div className="px-6 lg:px-10 py-6 space-y-6">
        {/* Required skills strip */}
        <div className="surface-card rounded-xl p-4 flex flex-wrap items-center gap-3">
          <div className="text-[10px] uppercase tracking-[0.22em] font-mono text-muted-foreground">
            Required DNA
          </div>
          {job.requiredSkills.map((s) => (
            <Badge key={s} variant="outline" className="bg-primary/10 border-primary/40 text-primary font-mono">
              {s}
            </Badge>
          ))}
          {job.preferredSkills.length > 0 && (
            <>
              <div className="ml-4 text-[10px] uppercase tracking-[0.22em] font-mono text-muted-foreground">
                Preferred
              </div>
              {job.preferredSkills.map((s) => (
                <Badge key={s} variant="outline" className="bg-gem/10 border-gem/40 text-gem font-mono">
                  {s}
                </Badge>
              ))}
            </>
          )}
          <div className="ml-auto text-xs text-muted-foreground font-mono">
            min {job.minExperienceYears}y · {scored.length} candidates
          </div>
        </div>

        <Tabs defaultValue="ranked">
          <TabsList>
            <TabsTrigger value="ranked">Ranked List</TabsTrigger>
            <TabsTrigger value="map">Opportunity Map</TabsTrigger>
            <TabsTrigger value="adjacency">Skill Adjacency</TabsTrigger>
          </TabsList>

          <TabsContent value="ranked" className="mt-4">
            {/* Filter bar */}
            <div className="flex flex-wrap items-center gap-2 mb-4">
              <div className="relative flex-1 min-w-[220px] max-w-md">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Search name, skill, headline..."
                  className="pl-8"
                />
              </div>
              <div className="flex items-center gap-1 ml-auto">
                <Filter className="h-3.5 w-3.5 text-muted-foreground mr-1" />
                {(["all", "gem", "safe", "stretch", "pass"] as const).map((f) => (
                  <Button
                    key={f}
                    size="sm"
                    variant={filter === f ? "secondary" : "ghost"}
                    onClick={() => setFilter(f)}
                    className="font-mono text-xs uppercase"
                  >
                    {f}
                  </Button>
                ))}
              </div>
            </div>

            {/* Table */}
            <div className="surface-card rounded-xl overflow-hidden">
              <div className="grid grid-cols-[1.6fr_1fr_repeat(5,0.7fr)_auto] gap-3 px-4 py-3 text-[10px] uppercase tracking-[0.18em] font-mono text-muted-foreground border-b border-border/60">
                <div>Candidate</div>
                <div>Status</div>
                <div className="text-right">Current</div>
                <div className="text-right">Future</div>
                <div className="text-right">Risk</div>
                <div className="text-right">Onboard</div>
                <div className="text-right">ATS → DNA</div>
                <div />
              </div>
              {scored.map(({ c, s, q: qq }) => (
                <button
                  key={c.id}
                  onClick={() =>
                    navigate({
                      to: "/jobs/$jobId/candidates/$candidateId",
                      params: { jobId: job.id, candidateId: c.id },
                    })
                  }
                  className="grid grid-cols-[1.6fr_1fr_repeat(5,0.7fr)_auto] gap-3 px-4 py-3 items-center text-left border-b border-border/40 last:border-0 hover:bg-secondary/40 transition group"
                >
                  <div className="min-w-0">
                    <div className="font-medium text-sm truncate">{c.name}</div>
                    <div className="text-xs text-muted-foreground truncate">{c.headline}</div>
                  </div>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <QuadrantBadge q={qq} />
                    <RecommendationBadge value={s.recommendation} />
                  </div>
                  <ScoreCell value={s.currentFit} />
                  <ScoreCell value={s.futureFit} highlight={qq === "gem"} />
                  <ScoreCell value={s.riskScore} invert />
                  <div className="text-right font-mono tabular-nums text-sm">
                    {s.onboardingWeeks}<span className="text-muted-foreground text-xs">w</span>
                  </div>
                  <div className="text-right font-mono text-xs tabular-nums">
                    <span className="text-destructive">{c.atsScore}</span>
                    <span className="text-muted-foreground"> → </span>
                    <span className={qq === "gem" ? "text-gem" : "text-foreground"}>{s.futureFit}</span>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-primary" />
                </button>
              ))}
              {scored.length === 0 && (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  No candidates match your filters.
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="map" className="mt-4">
            <div className="surface-card rounded-xl p-5">
              <TalentOpportunityMap jd={job} candidates={candidates} />
            </div>
          </TabsContent>

          <TabsContent value="adjacency" className="mt-4">
            <div className="surface-card rounded-xl p-5">
              <div className="mb-4">
                <div className="text-[10px] uppercase tracking-[0.22em] font-mono text-muted-foreground">
                  Skill ↔ Candidate map
                </div>
                <h3 className="font-display text-lg font-semibold mt-1">
                  How JD requirements map to your pool
                </h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Green = direct keyword match. Purple = a candidate has a structurally adjacent
                  skill (e.g. Docker + Helm + Terraform bridges Kubernetes).
                </p>
              </div>
              <SkillAdjacencyMap jd={job} candidates={candidates} />
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function ScoreCell({ value, highlight, invert }: { value: number; highlight?: boolean; invert?: boolean }) {
  // For invert (risk): green low, red high. For normal: green high, red low.
  const v = invert ? 100 - value : value;
  const color = v >= 75 ? "text-safe" : v >= 50 ? "text-foreground" : v >= 25 ? "text-stretch" : "text-destructive";
  return (
    <div className={`text-right font-mono tabular-nums text-sm ${highlight ? "text-gem" : color}`}>
      {Math.round(value)}
    </div>
  );
}
