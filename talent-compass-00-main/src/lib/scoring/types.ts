export type Recommendation = "strong_hire" | "consider" | "pass";

export interface Skill {
  name: string;
  proficiency: "beginner" | "intermediate" | "advanced" | "expert";
  yearsOfUse?: number;
}

export interface CareerEntry {
  company: string;
  title: string;
  level: "Junior" | "Mid" | "Senior" | "Lead" | "Principal";
  startDate: string; // YYYY-MM
  endDate: string;   // YYYY-MM or "present"
  durationMonths: number;
  description?: string;
}

export interface RedrobSignals {
  profileCompleteness: number;        // 0..100
  recruiterResponseRate: number;      // 0..1
  interviewCompletionRate: number;    // 0..1
  githubActivityScore: number;        // 0..100
  assessmentScores: {
    codingProficiency?: number;
    systemDesign?: number;
  };
}

export interface Candidate {
  id: string;
  name: string;
  headline: string;
  location: string;
  yearsOfExperience: number;
  skills: Skill[];
  career: CareerEntry[];
  education: { degree: string; field: string; institution: string; year: number }[];
  signals: RedrobSignals;
  /** Original ATS keyword score the system would have given them — used for the "Why ATS missed" comparison. */
  atsScore: number;
}

export interface JobDescription {
  id: string;
  title: string;
  company: string;
  description: string;
  requiredSkills: string[];
  preferredSkills: string[];
  minExperienceYears: number;
  maxExperienceYears?: number;
  location: string;
  createdAt: string;
}

export interface ScoreBreakdown {
  currentFit: number;     // 0..100
  futureFit: number;      // 0..100
  hiddenGem: number;      // 0..100
  riskScore: number;      // 0..100 (higher = riskier)
  onboardingWeeks: number;
  growthVelocity: number; // 0..1
  confidence: number;     // 0..1
  recommendation: Recommendation;
  matchedRequired: string[];
  missingRequired: string[];
  matchedPreferred: string[];
  adjacentBridges: { missing: string; bridges: string[] }[];
  whyAtsMissed: string[];
}
