import { useEffect, useState, useCallback, useSyncExternalStore } from "react";
import type { Candidate, JobDescription } from "@/lib/scoring/types";
import { MOCK_CANDIDATES, MOCK_JOBS } from "@/data/mockData";

const JOBS_KEY = "talentdna.jobs.v1";
const CANDIDATES_KEY = "talentdna.candidates.v1";

type Listener = () => void;
const listeners = new Set<Listener>();
function emit() {
  listeners.forEach((l) => l());
}
function subscribe(l: Listener) {
  listeners.add(l);
  return () => listeners.delete(l);
}

function safeRead<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}
function safeWrite<T>(key: string, value: T) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* ignore quota */
  }
}

let jobsCache: JobDescription[] | null = null;
let candidatesCache: Candidate[] | null = null;

function ensureSeed() {
  if (typeof window === "undefined") return;
  if (!window.localStorage.getItem(JOBS_KEY)) safeWrite(JOBS_KEY, MOCK_JOBS);
  if (!window.localStorage.getItem(CANDIDATES_KEY)) safeWrite(CANDIDATES_KEY, MOCK_CANDIDATES);
}

export function getJobs(): JobDescription[] {
  if (typeof window === "undefined") return MOCK_JOBS;
  ensureSeed();
  if (!jobsCache) jobsCache = safeRead<JobDescription[]>(JOBS_KEY, MOCK_JOBS);
  return jobsCache;
}
export function getCandidates(): Candidate[] {
  if (typeof window === "undefined") return MOCK_CANDIDATES;
  ensureSeed();
  if (!candidatesCache) candidatesCache = safeRead<Candidate[]>(CANDIDATES_KEY, MOCK_CANDIDATES);
  return candidatesCache;
}

export function saveJob(jd: JobDescription) {
  const jobs = [...getJobs()];
  const idx = jobs.findIndex((j) => j.id === jd.id);
  if (idx >= 0) jobs[idx] = jd;
  else jobs.unshift(jd);
  jobsCache = jobs;
  safeWrite(JOBS_KEY, jobs);
  emit();
}
export function saveCandidate(c: Candidate) {
  const list = [...getCandidates()];
  const idx = list.findIndex((x) => x.id === c.id);
  if (idx >= 0) list[idx] = c;
  else list.unshift(c);
  candidatesCache = list;
  safeWrite(CANDIDATES_KEY, list);
  emit();
}

export function useJobs(): JobDescription[] {
  return useSyncExternalStore(
    subscribe,
    () => getJobs(),
    () => MOCK_JOBS,
  );
}
export function useCandidates(): Candidate[] {
  return useSyncExternalStore(
    subscribe,
    () => getCandidates(),
    () => MOCK_CANDIDATES,
  );
}

export function useJob(id: string | undefined): JobDescription | undefined {
  const jobs = useJobs();
  return jobs.find((j) => j.id === id);
}
export function useCandidate(id: string | undefined): Candidate | undefined {
  const cs = useCandidates();
  return cs.find((c) => c.id === id);
}

// Hydration guard — render skeleton until localStorage has been touched
export function useHydrated() {
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);
  return hydrated;
}

export function resetSeed() {
  if (typeof window === "undefined") return;
  jobsCache = [...MOCK_JOBS];
  candidatesCache = [...MOCK_CANDIDATES];
  safeWrite(JOBS_KEY, MOCK_JOBS);
  safeWrite(CANDIDATES_KEY, MOCK_CANDIDATES);
  emit();
}

export const useStoreAction = () => useCallback(emit, []);
