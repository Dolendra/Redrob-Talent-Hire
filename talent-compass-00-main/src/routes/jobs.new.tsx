import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMemo, useRef, useState } from "react";
import { ArrowLeft, X, Wand2, Upload, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { saveJob } from "@/lib/store";
import { parseJdText, parseJdFile, type ParsedJd } from "@/lib/jdParser";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/talent/page-header";
import type { JobDescription } from "@/lib/scoring/types";

export const Route = createFileRoute("/jobs/new")({
  head: () => ({
    meta: [
      { title: "New job · TalentDNA" },
      { name: "description", content: "Create a new requisition and define its TalentDNA matrix." },
      { property: "og:title", content: "Create new job · TalentDNA" },
    ],
  }),
  component: NewJobPage,
});

function NewJobPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("Redrob AI");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("Remote");
  const [minExp, setMinExp] = useState(3);
  const [required, setRequired] = useState<string[]>([]);
  const [preferred, setPreferred] = useState<string[]>([]);
  const [reqInput, setReqInput] = useState("");
  const [prefInput, setPrefInput] = useState("");
  const [jdBlob, setJdBlob] = useState("");
  const [parsing, setParsing] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  function applyParsed(p: ParsedJd) {
    if (p.title) setTitle(p.title);
    if (p.company) setCompany(p.company);
    if (p.location) setLocation(p.location);
    if (typeof p.minExperienceYears === "number") setMinExp(p.minExperienceYears);
    if (p.description) setDescription(p.description);
    setRequired((prev) => Array.from(new Set([...prev, ...p.requiredSkills])));
    setPreferred((prev) =>
      Array.from(new Set([...prev, ...p.preferredSkills.filter((s) => !p.requiredSkills.includes(s))])),
    );
    toast.success(
      `Parsed JD · ${p.requiredSkills.length} required, ${p.preferredSkills.length} preferred skills`,
    );
  }

  function parsePaste() {
    if (!jdBlob.trim()) {
      toast.error("Paste a job description first");
      return;
    }
    applyParsed(parseJdText(jdBlob));
  }

  async function parseFile(f: File) {
    setParsing(true);
    try {
      const parsed = await parseJdFile(f);
      if (!jdBlob) setJdBlob(parsed.description);
      applyParsed(parsed);
    } catch (err) {
      console.error(err);
      toast.error("Couldn't parse that file");
    } finally {
      setParsing(false);
    }
  }

  const id = useMemo(() => `JOB_${Date.now().toString(36).toUpperCase()}`, []);

  function addTag(value: string, list: string[], setList: (v: string[]) => void, clear: () => void) {
    const v = value.trim().toLowerCase();
    if (!v) return;
    if (!list.includes(v)) setList([...list, v]);
    clear();
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      toast.error("Job title is required");
      return;
    }
    const jd: JobDescription = {
      id,
      title: title.trim(),
      company: company.trim(),
      description: description.trim(),
      requiredSkills: required,
      preferredSkills: preferred,
      minExperienceYears: minExp,
      location: location.trim(),
      createdAt: new Date().toISOString().slice(0, 10),
    };
    saveJob(jd);
    toast.success("Job deployed to the requisition registry");
    navigate({ to: "/jobs/$jobId", params: { jobId: id } });
  }

  return (
    <div>
      <PageHeader
        eyebrow="New requisition"
        title="Author a TalentDNA matrix"
        description="Define what success looks like. TalentDNA scores candidates on this matrix the moment they land in your pool."
        actions={
          <Button variant="ghost" asChild>
            <Link to="/">
              <ArrowLeft className="h-4 w-4 mr-1" /> Cancel
            </Link>
          </Button>
        }
      />

      <form onSubmit={submit} className="px-6 lg:px-10 py-6 grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6">
        {/* Form */}
        <div className="space-y-6">
        <div className="surface-card rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-[10px] uppercase tracking-[0.22em] font-mono text-primary">
                One-click JD intake
              </div>
              <h3 className="font-display text-base font-semibold mt-0.5">
                Paste or drop a JD — we extract the matrix
              </h3>
            </div>
            <input
              ref={fileRef}
              type="file"
              hidden
              accept=".pdf,.docx,.txt"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) parseFile(f);
              }}
            />
            <Button type="button" variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
              {parsing ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Upload className="h-4 w-4 mr-1" />}
              Upload .pdf / .docx
            </Button>
          </div>
          <Textarea
            value={jdBlob}
            onChange={(e) => setJdBlob(e.target.value)}
            placeholder="Paste the full job description here. We'll detect title, company, required vs preferred skills, and min years of experience."
            className="min-h-[120px] font-mono text-xs"
          />
          <div className="flex justify-end">
            <Button type="button" size="sm" variant="secondary" onClick={parsePaste}>
              <Wand2 className="h-4 w-4 mr-1" /> Parse into form
            </Button>
          </div>
        </div>

        <div className="surface-card rounded-xl p-6 space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label className="text-xs uppercase tracking-wider font-mono">Title</Label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Senior ML Engineer"
                className="mt-1.5"
              />
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wider font-mono">Company</Label>
              <Input
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                className="mt-1.5"
              />
            </div>
          </div>

          <div>
            <Label className="text-xs uppercase tracking-wider font-mono">Job description</Label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What this role owns, the team, the impact..."
              className="mt-1.5 min-h-[120px]"
            />
          </div>

          <TagInput
            label="Required skills"
            list={required}
            onRemove={(t) => setRequired(required.filter((x) => x !== t))}
            input={reqInput}
            setInput={setReqInput}
            onAdd={(v) => addTag(v, required, setRequired, () => setReqInput(""))}
            accent="primary"
            placeholder="python, kubernetes, rag..."
          />

          <TagInput
            label="Preferred skills"
            list={preferred}
            onRemove={(t) => setPreferred(preferred.filter((x) => x !== t))}
            input={prefInput}
            setInput={setPrefInput}
            onAdd={(v) => addTag(v, preferred, setPreferred, () => setPrefInput(""))}
            accent="gem"
            placeholder="langchain, spark..."
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label className="text-xs uppercase tracking-wider font-mono">Min experience (years)</Label>
              <Input
                type="number"
                min={0}
                value={minExp}
                onChange={(e) => setMinExp(Number(e.target.value))}
                className="mt-1.5"
              />
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wider font-mono">Location</Label>
              <Input
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="mt-1.5"
              />
            </div>
          </div>

          <div className="pt-2 flex items-center justify-end gap-3 border-t border-border/60">
            <Button type="button" variant="ghost" asChild>
              <Link to="/">Cancel</Link>
            </Button>
            <Button
              type="submit"
              className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-[var(--shadow-glow-primary)]"
            >
              Deploy requisition
            </Button>
          </div>
        </div>

        </div>

        {/* Preview */}
        <div className="space-y-4">
          <div className="surface-card rounded-xl p-5">
            <div className="text-[10px] uppercase tracking-[0.22em] font-mono text-primary">
              Live preview
            </div>
            <div className="mt-3 font-display text-xl font-semibold">
              {title || "Job title"}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              {company || "Company"} · {location || "Location"}
            </div>
            <div className="mt-4 space-y-3">
              <div>
                <div className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground mb-1.5">
                  Required DNA
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {required.length === 0 ? (
                    <span className="text-xs text-muted-foreground">No required skills yet</span>
                  ) : (
                    required.map((t) => (
                      <Badge key={t} variant="outline" className="bg-primary/10 border-primary/40 text-primary font-mono">
                        {t}
                      </Badge>
                    ))
                  )}
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider font-mono text-muted-foreground mb-1.5">
                  Preferred DNA
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {preferred.length === 0 ? (
                    <span className="text-xs text-muted-foreground">None</span>
                  ) : (
                    preferred.map((t) => (
                      <Badge key={t} variant="outline" className="bg-gem/10 border-gem/40 text-gem font-mono">
                        {t}
                      </Badge>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
          <div className="text-xs text-muted-foreground px-1 leading-relaxed">
            Skills are matched against the canonical taxonomy. Missing skills are forgiven if the
            candidate has structural neighbours (Kubernetes ≈ Docker + Helm + Terraform).
          </div>
        </div>
      </form>
    </div>
  );
}

interface TagInputProps {
  label: string;
  list: string[];
  input: string;
  setInput: (v: string) => void;
  onAdd: (v: string) => void;
  onRemove: (t: string) => void;
  accent: "primary" | "gem";
  placeholder?: string;
}
function TagInput({ label, list, input, setInput, onAdd, onRemove, accent, placeholder }: TagInputProps) {
  const accentCls =
    accent === "primary"
      ? "bg-primary/10 border-primary/40 text-primary"
      : "bg-gem/10 border-gem/40 text-gem";
  return (
    <div>
      <Label className="text-xs uppercase tracking-wider font-mono">{label}</Label>
      <div className="mt-1.5 flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              onAdd(input);
            }
          }}
          placeholder={placeholder}
        />
        <Button type="button" variant="secondary" onClick={() => onAdd(input)}>
          Add
        </Button>
      </div>
      {list.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {list.map((t) => (
            <Badge
              key={t}
              variant="outline"
              className={`${accentCls} font-mono gap-1 pr-1`}
            >
              {t}
              <button
                type="button"
                onClick={() => onRemove(t)}
                className="hover:opacity-70 p-0.5 -mr-0.5"
                aria-label={`Remove ${t}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
