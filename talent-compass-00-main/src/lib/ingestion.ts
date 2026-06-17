// Browser-only resume text extraction. Uses pdfjs-dist for PDF and mammoth for DOCX.
// Falls back to FileReader text for .txt / unknown.

import type { Candidate, Skill } from "@/lib/scoring/types";

const SKILL_VOCAB = [
  "python","javascript","typescript","react","vue","svelte","next.js","node.js","fastapi","django","flask",
  "pytorch","tensorflow","jax","keras","langchain","llamaindex","rag","vector db","pinecone","weaviate","qdrant","pgvector","openai api",
  "kubernetes","docker","helm","terraform","pulumi","ansible","ci/cd","aws","gcp","azure","containerd",
  "postgres","mysql","sqlite","supabase","sql","graphql","rest","apollo","trpc",
  "rust","go","java","c++","scala","spark","hadoop","airflow","dagster","prefect",
  "pandas","numpy","polars","databricks","tailwindcss",
];

export async function extractText(file: File): Promise<string> {
  const name = file.name.toLowerCase();
  if (name.endsWith(".pdf")) return extractPdf(file);
  if (name.endsWith(".docx")) return extractDocx(file);
  return await file.text();
}

async function extractPdf(file: File): Promise<string> {
  const buf = await file.arrayBuffer();
  // Lazy-load pdfjs to keep main bundle slim
  const pdfjs = await import("pdfjs-dist");
  const workerSrc = (
    await import("pdfjs-dist/build/pdf.worker.min.mjs?url")
  ).default as string;
  pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;
  const doc = await pdfjs.getDocument({ data: buf }).promise;
  let out = "";
  for (let i = 1; i <= doc.numPages; i++) {
    const page = await doc.getPage(i);
    const content = await page.getTextContent();
    out += content.items.map((it) => ("str" in it ? it.str : "")).join(" ") + "\n";
  }
  return out;
}

async function extractDocx(file: File): Promise<string> {
  const buf = await file.arrayBuffer();
  const mammoth = await import("mammoth/mammoth.browser");
  const res = await mammoth.extractRawText({ arrayBuffer: buf });
  return res.value;
}

/**
 * Rule-based skill extraction. Scans text for canonical vocabulary.
 */
export function extractSkills(text: string, jdVocab: string[] = []): Skill[] {
  const lower = text.toLowerCase();
  const pool = Array.from(new Set([...SKILL_VOCAB, ...jdVocab.map((v) => v.toLowerCase())]));
  const out: Skill[] = [];
  for (const s of pool) {
    const safe = s.replace(/[+.]/g, "\\$&");
    const pattern = new RegExp(`(^|[^a-z0-9])${safe}([^a-z0-9]|$)`, "i");
    if (pattern.test(lower)) {
      // proficiency heuristic: count occurrences
      const count = (lower.match(new RegExp(safe, "gi")) ?? []).length;
      const proficiency: Skill["proficiency"] =
        count >= 5 ? "expert" : count >= 3 ? "advanced" : count >= 2 ? "intermediate" : "beginner";
      out.push({ name: s, proficiency });
    }
  }
  return out;
}

export function extractYearsExperience(text: string): number {
  const m = text.match(/(\d+)\+?\s*years?\s*(of)?\s*(experience|exp)/i);
  if (m) return Number(m[1]);
  const m2 = text.match(/(\d+)\+?\s*yrs?/i);
  if (m2) return Number(m2[1]);
  return 3;
}

export function buildCandidate(args: {
  name: string;
  rawText: string;
  jdVocab: string[];
}): Candidate {
  const skills = extractSkills(args.rawText, args.jdVocab);
  const yoe = extractYearsExperience(args.rawText);
  const id = `CAND_${Date.now().toString(36).toUpperCase()}`;
  return {
    id,
    name: args.name,
    headline: "Newly ingested candidate",
    location: "Unknown",
    yearsOfExperience: yoe,
    skills,
    career: [
      {
        company: "Most recent (auto)",
        title: "Engineer",
        level: yoe >= 7 ? "Senior" : yoe >= 4 ? "Mid" : "Junior",
        startDate: "2023-01",
        endDate: "present",
        durationMonths: Math.max(12, yoe * 12 / 2),
      },
    ],
    education: [],
    signals: {
      profileCompleteness: 70,
      recruiterResponseRate: 0.85,
      interviewCompletionRate: 0.9,
      githubActivityScore: 55,
      assessmentScores: {},
    },
    atsScore: Math.min(80, 30 + skills.length * 4),
  };
}
