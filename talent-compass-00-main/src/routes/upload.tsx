import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { Upload, FileText, Loader2, Check, X, ArrowRight } from "lucide-react";
import { toast } from "sonner";

import { useJobs, saveCandidate } from "@/lib/store";
import { extractText, buildCandidate } from "@/lib/ingestion";
import { scoreCandidate } from "@/lib/scoring/engine";
import { PageHeader } from "@/components/talent/page-header";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Candidate } from "@/lib/scoring/types";

export const Route = createFileRoute("/upload")({
  head: () => ({
    meta: [
      { title: "Upload candidates · TalentDNA" },
      { name: "description", content: "Drop one or many resumes — TalentDNA parses, normalizes and scores them in seconds." },
    ],
  }),
  component: UploadPage,
});

type Status = "pending" | "parsing" | "ready" | "added" | "error";
interface Row {
  id: string;
  file: File;
  status: Status;
  candidate?: Candidate;
  error?: string;
  futureFit?: number;
}

function rid() {
  return Math.random().toString(36).slice(2, 9);
}

function UploadPage() {
  const jobs = useJobs();
  const navigate = useNavigate();
  const [jobId, setJobId] = useState(jobs[0]?.id);
  const [rows, setRows] = useState<Row[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const targetJob = jobs.find((j) => j.id === jobId);

  function patch(id: string, p: Partial<Row>) {
    setRows((r) => r.map((x) => (x.id === id ? { ...x, ...p } : x)));
  }

  async function handleFiles(files: FileList | File[]) {
    const list = Array.from(files);
    const newRows: Row[] = list.map((f) => ({ id: rid(), file: f, status: "pending" }));
    setRows((prev) => [...prev, ...newRows]);

    for (const row of newRows) {
      patch(row.id, { status: "parsing" });
      try {
        const text = await extractText(row.file);
        const vocab = targetJob ? [...targetJob.requiredSkills, ...targetJob.preferredSkills] : [];
        const cand = buildCandidate({
          name: row.file.name.replace(/\.(pdf|docx|txt)$/i, "").replace(/[_-]+/g, " "),
          rawText: text,
          jdVocab: vocab,
        });
        const s = targetJob ? scoreCandidate(cand, targetJob) : undefined;
        patch(row.id, { status: "ready", candidate: cand, futureFit: s?.futureFit });
      } catch (err) {
        console.error(err);
        patch(row.id, { status: "error", error: (err as Error).message ?? "parse failed" });
      }
    }
  }

  function commitAll() {
    if (!targetJob) {
      toast.error("Pick a target requisition first");
      return;
    }
    const ready = rows.filter((r) => r.status === "ready" && r.candidate);
    if (ready.length === 0) {
      toast.error("Nothing to add yet");
      return;
    }
    ready.forEach((r) => {
      saveCandidate(r.candidate!);
      patch(r.id, { status: "added" });
    });
    toast.success(`${ready.length} candidate${ready.length === 1 ? "" : "s"} added to ${targetJob.title}`);
  }

  function commitOne(row: Row) {
    if (!targetJob || !row.candidate) return;
    saveCandidate(row.candidate);
    patch(row.id, { status: "added" });
    navigate({
      to: "/jobs/$jobId/candidates/$candidateId",
      params: { jobId: targetJob.id, candidateId: row.candidate.id },
    });
  }

  function remove(id: string) {
    setRows((r) => r.filter((x) => x.id !== id));
  }

  const readyCount = rows.filter((r) => r.status === "ready").length;
  const addedCount = rows.filter((r) => r.status === "added").length;

  return (
    <div>
      <PageHeader
        eyebrow="Bulk ingestion"
        title="Upload candidate resumes"
        description="Drop one or many PDFs / DOCX / TXT. Each resume is parsed in your browser, scored against the selected JD and queued for one-click commit to the dashboard."
      />

      <div className="px-6 lg:px-10 py-6 grid grid-cols-1 lg:grid-cols-[1.1fr_1fr] gap-6">
        {/* Drop zone */}
        <div className="space-y-4">
          <div className="surface-card rounded-xl p-5 space-y-4">
            <div>
              <Label className="text-xs uppercase tracking-wider font-mono">Target requisition</Label>
              <Select value={jobId} onValueChange={setJobId}>
                <SelectTrigger className="mt-1.5">
                  <SelectValue />
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

            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
              }}
              onClick={() => inputRef.current?.click()}
              className={cn(
                "relative rounded-xl border-2 border-dashed transition cursor-pointer group",
                "min-h-[220px] flex flex-col items-center justify-center text-center px-6 py-8",
                dragOver
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/60 hover:bg-secondary/30",
              )}
            >
              <input
                ref={inputRef}
                type="file"
                multiple
                hidden
                accept=".pdf,.docx,.txt"
                onChange={(e) => {
                  if (e.target.files?.length) handleFiles(e.target.files);
                  e.target.value = "";
                }}
              />
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-3 group-hover:scale-110 transition">
                <Upload className="h-6 w-6 text-primary" />
              </div>
              <div className="font-medium">Drop resumes here or click to browse</div>
              <div className="text-xs text-muted-foreground mt-1 font-mono">
                pdf · docx · txt — parsed locally · select multiple
              </div>
            </div>

            {rows.length > 0 && (
              <div className="flex items-center justify-between gap-3 pt-2 border-t border-border/60">
                <div className="text-xs text-muted-foreground font-mono">
                  {rows.length} queued · {readyCount} ready · {addedCount} added
                </div>
                <Button
                  type="button"
                  disabled={readyCount === 0}
                  onClick={commitAll}
                  className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-[var(--shadow-glow-primary)]"
                >
                  Add {readyCount > 0 ? readyCount : ""} to pool
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Queue */}
        <div className="space-y-3">
          {rows.length === 0 ? (
            <div className="surface-card rounded-xl p-6 min-h-[400px] grid-bg flex items-center justify-center">
              <div className="text-center text-muted-foreground">
                <FileText className="h-8 w-8 mx-auto mb-2 opacity-60" />
                <div className="text-sm">Parsed candidates appear here as a queue.</div>
                <div className="text-xs mt-1">Each one is scored against the selected JD.</div>
              </div>
            </div>
          ) : (
            rows.map((r) => (
              <div key={r.id} className="surface-card rounded-xl p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-sm truncate">
                      {r.candidate?.name ?? r.file.name}
                    </div>
                    <div className="text-[11px] text-muted-foreground font-mono truncate">
                      {r.file.name} · {(r.file.size / 1024).toFixed(0)} KB
                    </div>
                  </div>
                  <StatusPill row={r} />
                </div>

                {r.candidate && (
                  <>
                    <div className="mt-3 flex flex-wrap gap-1.5 max-h-[60px] overflow-hidden">
                      {r.candidate.skills.slice(0, 8).map((s) => (
                        <Badge key={s.name} variant="outline" className="font-mono text-[10px]">
                          {s.name}
                        </Badge>
                      ))}
                      {r.candidate.skills.length > 8 && (
                        <Badge variant="outline" className="font-mono text-[10px]">
                          +{r.candidate.skills.length - 8}
                        </Badge>
                      )}
                    </div>
                    <div className="mt-3 flex items-center justify-between gap-3">
                      <div className="font-mono text-[11px] text-muted-foreground">
                        {r.candidate.yearsOfExperience}y exp · ATS {r.candidate.atsScore}
                        {r.futureFit !== undefined && (
                          <>
                            <span className="mx-1">→</span>
                            <span className="text-gem">DNA {r.futureFit}</span>
                          </>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        {r.status !== "added" && (
                          <Button size="sm" variant="ghost" onClick={() => remove(r.id)}>
                            <X className="h-3.5 w-3.5" />
                          </Button>
                        )}
                        {r.status === "ready" && (
                          <Button size="sm" variant="secondary" onClick={() => commitOne(r)}>
                            Open <ArrowRight className="h-3.5 w-3.5 ml-1" />
                          </Button>
                        )}
                        {r.status === "added" && targetJob && (
                          <Button size="sm" variant="ghost" asChild>
                            <Link
                              to="/jobs/$jobId/candidates/$candidateId"
                              params={{ jobId: targetJob.id, candidateId: r.candidate.id }}
                            >
                              View <ArrowRight className="h-3.5 w-3.5 ml-1" />
                            </Link>
                          </Button>
                        )}
                      </div>
                    </div>
                  </>
                )}
                {r.error && (
                  <div className="mt-2 text-xs text-destructive">{r.error}</div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function StatusPill({ row }: { row: Row }) {
  const map: Record<Status, { label: string; cls: string; icon: React.ReactNode }> = {
    pending: { label: "queued", cls: "text-muted-foreground border-border", icon: null },
    parsing: {
      label: "parsing",
      cls: "text-primary border-primary/40",
      icon: <Loader2 className="h-3 w-3 animate-spin" />,
    },
    ready: { label: "ready", cls: "text-gem border-gem/40", icon: null },
    added: {
      label: "added",
      cls: "text-safe border-safe/40",
      icon: <Check className="h-3 w-3" />,
    },
    error: { label: "error", cls: "text-destructive border-destructive/40", icon: null },
  };
  const s = map[row.status];
  return (
    <Badge variant="outline" className={cn("font-mono text-[10px] gap-1 uppercase", s.cls)}>
      {s.icon}
      {s.label}
    </Badge>
  );
}
