// Parse a free-form job description blob into structured fields.
// Used by the Create New Job page (paste / file upload).

import { extractText } from "@/lib/ingestion";

const SKILL_VOCAB = [
  "python","javascript","typescript","react","vue","svelte","next.js","node.js","fastapi","django","flask",
  "pytorch","tensorflow","jax","keras","langchain","llamaindex","rag","vector db","pinecone","weaviate","qdrant","pgvector","openai api",
  "kubernetes","docker","helm","terraform","pulumi","ansible","ci/cd","aws","gcp","azure","containerd",
  "postgres","mysql","sqlite","supabase","sql","graphql","rest","apollo","trpc",
  "rust","go","java","c++","scala","spark","hadoop","airflow","dagster","prefect",
  "pandas","numpy","polars","databricks","tailwindcss",
];

export interface ParsedJd {
  title?: string;
  company?: string;
  location?: string;
  minExperienceYears?: number;
  requiredSkills: string[];
  preferredSkills: string[];
  description: string;
}

function findInLine(text: string, label: RegExp): string | undefined {
  const m = text.match(label);
  return m?.[1]?.trim();
}

function scanSkills(text: string): string[] {
  const lower = text.toLowerCase();
  const out: string[] = [];
  for (const s of SKILL_VOCAB) {
    const safe = s.replace(/[+.]/g, "\\$&");
    const pattern = new RegExp(`(^|[^a-z0-9])${safe}([^a-z0-9]|$)`, "i");
    if (pattern.test(lower)) out.push(s);
  }
  return Array.from(new Set(out));
}

export function parseJdText(text: string): ParsedJd {
  const clean = text.replace(/\r/g, "");
  const title = findInLine(clean, /(?:^|\n)\s*(?:title|role|position)\s*[:\-]\s*(.+)/i);
  const company = findInLine(clean, /(?:^|\n)\s*(?:company|employer|organization)\s*[:\-]\s*(.+)/i);
  const location = findInLine(clean, /(?:^|\n)\s*(?:location|based in)\s*[:\-]\s*(.+)/i);
  const expMatch =
    clean.match(/(\d+)\+?\s*(?:to\s*\d+\s*)?years?\s*(?:of)?\s*(?:experience|exp)/i) ||
    clean.match(/min(?:imum)?\s*(\d+)\s*years?/i);
  const minExperienceYears = expMatch ? Number(expMatch[1]) : undefined;

  // Split required vs preferred by looking for headings
  const requiredBlock = pickSection(clean, [
    /required(?:\s+skills)?/i,
    /must[\s-]have/i,
    /key skills/i,
  ]);
  const preferredBlock = pickSection(clean, [
    /preferred/i,
    /nice[\s-]to[\s-]have/i,
    /bonus/i,
    /good to have/i,
  ]);

  const requiredSkills = requiredBlock
    ? scanSkills(requiredBlock)
    : scanSkills(clean);
  const preferredSkills = preferredBlock
    ? scanSkills(preferredBlock).filter((s) => !requiredSkills.includes(s))
    : [];

  // Derive a short description from the first meaningful paragraph
  const paragraphs = clean
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter((p) => p.length > 40);
  const description = paragraphs[0] ?? clean.slice(0, 400);

  return {
    title,
    company,
    location,
    minExperienceYears,
    requiredSkills,
    preferredSkills,
    description,
  };
}

function pickSection(text: string, headers: RegExp[]): string | undefined {
  for (const h of headers) {
    const re = new RegExp(`${h.source}\\s*[:\\-]?[\\s\\n]+([\\s\\S]{20,600}?)(?:\\n\\n|$)`, "i");
    const m = text.match(re);
    if (m) return m[1];
  }
  return undefined;
}

export async function parseJdFile(file: File): Promise<ParsedJd> {
  const text = await extractText(file);
  return parseJdText(text);
}
