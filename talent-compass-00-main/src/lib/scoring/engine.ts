import type {
  Candidate,
  JobDescription,
  Recommendation,
  ScoreBreakdown,
} from "./types";
import { adjacencyCoverage, getAdjacentSkills } from "./skillAdjacency";

const LEVEL_WEIGHT: Record<string, number> = {
  Junior: 1,
  Mid: 2,
  Senior: 3,
  Lead: 4,
  Principal: 5,
};

const PROFICIENCY_BOOST: Record<string, number> = {
  beginner: 0.6,
  intermediate: 0.85,
  advanced: 1.0,
  expert: 1.1,
};

function lower(arr: string[]) {
  return arr.map((s) => s.toLowerCase());
}

/** Current Fit (35% weight in composite). Direct skill match weighted by proficiency. */
export function computeCurrentFit(c: Candidate, jd: JobDescription) {
  const required = lower(jd.requiredSkills);
  const preferred = lower(jd.preferredSkills);
  const candSkillMap = new Map(c.skills.map((s) => [s.name.toLowerCase(), s]));

  let reqHit = 0;
  const matchedRequired: string[] = [];
  const missingRequired: string[] = [];
  for (const r of required) {
    const skill = candSkillMap.get(r);
    if (skill) {
      reqHit += PROFICIENCY_BOOST[skill.proficiency] ?? 1;
      matchedRequired.push(r);
    } else {
      missingRequired.push(r);
    }
  }
  const reqScore = required.length === 0 ? 1 : reqHit / required.length;

  let prefHit = 0;
  const matchedPreferred: string[] = [];
  for (const p of preferred) {
    const skill = candSkillMap.get(p);
    if (skill) {
      prefHit += PROFICIENCY_BOOST[skill.proficiency] ?? 1;
      matchedPreferred.push(p);
    }
  }
  const prefScore = preferred.length === 0 ? 0 : prefHit / preferred.length;

  // Experience component
  const expFit =
    c.yearsOfExperience >= jd.minExperienceYears
      ? 1
      : Math.max(0, c.yearsOfExperience / Math.max(jd.minExperienceYears, 0.1));

  const raw = reqScore * 0.7 + prefScore * 0.2 + expFit * 0.1;
  return {
    score: Math.min(100, raw * 100),
    matchedRequired,
    missingRequired,
    matchedPreferred,
  };
}

/** Growth velocity: rate of seniority gain per year, normalized 0..1 */
export function computeGrowthVelocity(c: Candidate) {
  if (c.career.length < 2 || c.yearsOfExperience < 0.5) return 0.35;
  const sorted = [...c.career].sort((a, b) => a.startDate.localeCompare(b.startDate));
  const first = LEVEL_WEIGHT[sorted[0].level] ?? 2;
  const last = LEVEL_WEIGHT[sorted[sorted.length - 1].level] ?? 2;
  const delta = Math.max(0, last - first);
  // 1 level / 2 years = baseline 1.0
  const raw = delta / Math.max(c.yearsOfExperience, 1) / 0.5;
  return Math.max(0.2, Math.min(1, raw));
}

/** Future Fit = currentFit + (100 - currentFit) × adjacency% × velocity */
export function computeFutureFit(args: {
  currentFit: number;
  missingRequired: string[];
  candidateSkills: string[];
  velocity: number;
}) {
  const adj = adjacencyCoverage(args.missingRequired, args.candidateSkills);
  const headroom = 100 - args.currentFit;
  const future = args.currentFit + headroom * adj * args.velocity;
  return { score: Math.min(100, future), adjacency: adj };
}

/** Hidden Gem = futureFit × confidence × (1 - currentFit). Peaks when currentFit low + futureFit high. */
export function computeHiddenGem(future: number, current: number, confidence: number) {
  const norm = (future / 100) * confidence * (1 - current / 100);
  return Math.min(100, norm * 180); // scale for readability
}

/** Risk score 0..100, higher = riskier. */
export function computeRiskScore(c: Candidate) {
  // Job hopping: any tenure < 12 months adds 20 (cap at 60)
  const hopping = c.career.filter((e) => e.durationMonths < 12).length * 20;
  const ghosting = (1 - c.signals.recruiterResponseRate) * 40;
  const dropoff = (1 - c.signals.interviewCompletionRate) * 40;
  return Math.min(100, Math.min(60, hopping) + ghosting + dropoff);
}

/** Confidence in the score, derived from data completeness + signals. */
export function computeConfidence(c: Candidate) {
  const completeness = c.signals.profileCompleteness / 100;
  const signalsAvg =
    (c.signals.recruiterResponseRate +
      c.signals.interviewCompletionRate +
      c.signals.githubActivityScore / 100) /
    3;
  return Math.max(0.3, Math.min(1, completeness * 0.6 + signalsAvg * 0.4));
}

/** Onboarding cost in weeks. Baseline 2 weeks + penalties for missing skills. */
export function computeOnboardingWeeks(args: {
  missingRequired: string[];
  candidateSkills: string[];
  velocity: number;
}) {
  const lowerCand = new Set(args.candidateSkills.map((s) => s.toLowerCase()));
  let penalty = 0;
  for (const m of args.missingRequired) {
    const neighbors = getAdjacentSkills(m);
    const bridgeCount = neighbors.filter((n) => lowerCand.has(n)).length;
    if (bridgeCount >= 2) penalty += 1;
    else if (bridgeCount === 1) penalty += 2;
    else penalty += 4;
  }
  const learning = Math.max(0.6, args.velocity);
  return Math.round((2 + penalty / learning) * 10) / 10;
}

function classify(currentFit: number, futureFit: number, risk: number): Recommendation {
  if (risk > 60) return "pass";
  if (futureFit >= 80 && currentFit >= 60) return "strong_hire";
  if (futureFit >= 75) return "strong_hire";
  if (futureFit >= 60) return "consider";
  return "pass";
}

function reasonsAtsMissed(args: {
  matchedRequired: string[];
  missingRequired: string[];
  adjacentBridges: { missing: string; bridges: string[] }[];
  velocity: number;
  currentFit: number;
  futureFit: number;
}): string[] {
  const out: string[] = [];
  if (args.missingRequired.length > 0 && args.adjacentBridges.length > 0) {
    const top = args.adjacentBridges.slice(0, 2);
    out.push(
      `ATS rejected for missing ${args.missingRequired.join(", ")} — but candidate has structural neighbours: ${top
        .map((b) => `${b.missing} ≈ ${b.bridges.slice(0, 2).join(" + ")}`)
        .join("; ")}.`,
    );
  }
  if (args.velocity >= 0.75) {
    out.push(
      `Career velocity in the top quartile (${Math.round(args.velocity * 100)} percentile) — closes the gap fast.`,
    );
  }
  if (args.futureFit - args.currentFit > 18) {
    out.push(
      `Future Fit is ${Math.round(args.futureFit - args.currentFit)} pts above Current Fit — keyword matchers can't see this trajectory.`,
    );
  }
  if (out.length === 0) {
    out.push("Direct keyword match was strong enough; no hidden-gem premium applies.");
  }
  return out;
}

export function scoreCandidate(c: Candidate, jd: JobDescription): ScoreBreakdown {
  const cur = computeCurrentFit(c, jd);
  const velocity = computeGrowthVelocity(c);
  const fut = computeFutureFit({
    currentFit: cur.score,
    missingRequired: cur.missingRequired,
    candidateSkills: c.skills.map((s) => s.name),
    velocity,
  });
  const confidence = computeConfidence(c);
  const hidden = computeHiddenGem(fut.score, cur.score, confidence);
  const risk = computeRiskScore(c);
  const onboardingWeeks = computeOnboardingWeeks({
    missingRequired: cur.missingRequired,
    candidateSkills: c.skills.map((s) => s.name),
    velocity,
  });
  const recommendation = classify(cur.score, fut.score, risk);

  const lowerCand = new Set(c.skills.map((s) => s.name.toLowerCase()));
  const adjacentBridges = cur.missingRequired
    .map((m) => ({
      missing: m,
      bridges: getAdjacentSkills(m).filter((n) => lowerCand.has(n)),
    }))
    .filter((b) => b.bridges.length > 0);

  const whyAtsMissed = reasonsAtsMissed({
    matchedRequired: cur.matchedRequired,
    missingRequired: cur.missingRequired,
    adjacentBridges,
    velocity,
    currentFit: cur.score,
    futureFit: fut.score,
  });

  return {
    currentFit: Math.round(cur.score),
    futureFit: Math.round(fut.score),
    hiddenGem: Math.round(hidden),
    riskScore: Math.round(risk),
    onboardingWeeks,
    growthVelocity: Math.round(velocity * 100) / 100,
    confidence: Math.round(confidence * 100) / 100,
    recommendation,
    matchedRequired: cur.matchedRequired,
    missingRequired: cur.missingRequired,
    matchedPreferred: cur.matchedPreferred,
    adjacentBridges,
    whyAtsMissed,
  };
}

export function recommendationLabel(r: Recommendation) {
  return r === "strong_hire" ? "Strong Hire" : r === "consider" ? "Consider" : "Pass";
}

export function quadrantOf(s: ScoreBreakdown): "safe" | "gem" | "stretch" | "pass" {
  if (s.currentFit >= 60 && s.futureFit >= 70) return "safe";
  if (s.currentFit < 60 && s.futureFit >= 70) return "gem";
  if (s.currentFit >= 60 && s.futureFit < 70) return "stretch";
  return "pass";
}
