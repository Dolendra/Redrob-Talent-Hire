import type { Candidate, JobDescription } from "@/lib/scoring/types";

export const MOCK_JOBS: JobDescription[] = [
  {
    id: "JOB_001",
    title: "Senior Machine Learning Engineer",
    company: "Redrob AI",
    description:
      "Build and scale ML systems powering recommendations and ranking. Own end-to-end model lifecycle from data pipeline to production deployment.",
    requiredSkills: ["python", "pytorch", "kubernetes", "rag", "vector db"],
    preferredSkills: ["langchain", "spark", "aws", "airflow"],
    minExperienceYears: 5,
    maxExperienceYears: 10,
    location: "Remote · India / SF",
    createdAt: "2026-06-10",
  },
  {
    id: "JOB_002",
    title: "Full-Stack TypeScript Engineer",
    company: "Redrob AI",
    description:
      "Ship product surfaces across the recruiter command-center. React + Node, fast iteration, beautiful UI.",
    requiredSkills: ["typescript", "react", "node.js", "postgres"],
    preferredSkills: ["next.js", "graphql", "tailwindcss"],
    minExperienceYears: 3,
    maxExperienceYears: 8,
    location: "Bengaluru · Hybrid",
    createdAt: "2026-06-12",
  },
  {
    id: "JOB_003",
    title: "DevOps / Platform Lead",
    company: "Redrob AI",
    description:
      "Lead our cloud-native platform. Multi-region Kubernetes, IaC, observability, and developer productivity.",
    requiredSkills: ["kubernetes", "terraform", "aws", "ci/cd"],
    preferredSkills: ["docker", "helm", "go", "rust"],
    minExperienceYears: 6,
    location: "Remote",
    createdAt: "2026-06-08",
  },
];

// --- Candidate factory helpers ---
type C = Candidate;
function mk(
  id: string,
  name: string,
  headline: string,
  yoe: number,
  skills: { name: string; p: C["skills"][number]["proficiency"] }[],
  career: Omit<C["career"][number], "description">[],
  signals: Partial<C["signals"]> = {},
  atsScore = 50,
  location = "Bengaluru, IN",
): C {
  return {
    id,
    name,
    headline,
    location,
    yearsOfExperience: yoe,
    skills: skills.map((s) => ({ name: s.name, proficiency: s.p })),
    career: career.map((e) => ({ ...e })),
    education: [
      { degree: "B.Tech", field: "Computer Science", institution: "IIT", year: 2014 },
    ],
    signals: {
      profileCompleteness: 85,
      recruiterResponseRate: 0.9,
      interviewCompletionRate: 0.95,
      githubActivityScore: 60,
      assessmentScores: { codingProficiency: 75, systemDesign: 70 },
      ...signals,
    },
    atsScore,
  };
}

const NOW = "2026-06";

export const MOCK_CANDIDATES: Candidate[] = [
  // ===== Strong direct matches (Safe Hires) =====
  mk(
    "CAND_001",
    "Aarav Mehta",
    "Senior ML Engineer @ Flipkart",
    6,
    [
      { name: "Python", p: "expert" },
      { name: "PyTorch", p: "advanced" },
      { name: "Kubernetes", p: "advanced" },
      { name: "RAG", p: "intermediate" },
      { name: "Vector DB", p: "intermediate" },
      { name: "Spark", p: "advanced" },
      { name: "AWS", p: "advanced" },
    ],
    [
      { company: "Flipkart", title: "Sr ML Engineer", level: "Senior", startDate: "2023-01", endDate: "present", durationMonths: 41 },
      { company: "Swiggy", title: "ML Engineer", level: "Mid", startDate: "2020-06", endDate: "2022-12", durationMonths: 30 },
      { company: "Hike", title: "Data Scientist", level: "Junior", startDate: "2019-07", endDate: "2020-05", durationMonths: 10 },
    ],
    { profileCompleteness: 95, recruiterResponseRate: 0.95, githubActivityScore: 88 },
    82,
  ),
  mk(
    "CAND_002",
    "Priya Sharma",
    "Staff Engineer @ Razorpay",
    8,
    [
      { name: "Python", p: "expert" },
      { name: "PyTorch", p: "expert" },
      { name: "Kubernetes", p: "expert" },
      { name: "RAG", p: "advanced" },
      { name: "Vector DB", p: "advanced" },
      { name: "LangChain", p: "advanced" },
      { name: "Airflow", p: "intermediate" },
    ],
    [
      { company: "Razorpay", title: "Staff Engineer", level: "Lead", startDate: "2022-04", endDate: "present", durationMonths: 50 },
      { company: "Microsoft", title: "Sr SDE", level: "Senior", startDate: "2018-06", endDate: "2022-03", durationMonths: 45 },
    ],
    { profileCompleteness: 98, recruiterResponseRate: 1, githubActivityScore: 92 },
    91,
  ),

  // ===== HIDDEN GEMS — low ATS, high TalentDNA =====
  mk(
    "CAND_003",
    "Ritika Joshi",
    "ML Engineer @ early-stage startup",
    4,
    [
      // Missing: kubernetes, rag, vector db — but adjacent skills present
      { name: "Python", p: "expert" },
      { name: "PyTorch", p: "advanced" },
      { name: "Docker", p: "advanced" },
      { name: "Helm", p: "intermediate" },
      { name: "Terraform", p: "intermediate" },
      { name: "LangChain", p: "advanced" },
      { name: "Pinecone", p: "intermediate" },
      { name: "FastAPI", p: "advanced" },
    ],
    [
      { company: "Lumio.ai", title: "ML Engineer", level: "Mid", startDate: "2024-01", endDate: "present", durationMonths: 29 },
      { company: "Zomato", title: "Jr ML Engineer", level: "Junior", startDate: "2022-06", endDate: "2023-12", durationMonths: 18 },
    ],
    { profileCompleteness: 90, recruiterResponseRate: 0.92, githubActivityScore: 95 },
    42, // ATS heavily penalised her
  ),
  mk(
    "CAND_004",
    "Karthik Iyer",
    "Backend Engineer transitioning to ML",
    5,
    [
      { name: "Python", p: "expert" },
      { name: "TensorFlow", p: "advanced" }, // adjacent to PyTorch
      { name: "Docker", p: "advanced" },
      { name: "Containerd", p: "advanced" },
      { name: "Weaviate", p: "intermediate" },
      { name: "OpenAI API", p: "advanced" },
      { name: "FastAPI", p: "expert" },
      { name: "AWS", p: "advanced" },
    ],
    [
      { company: "Twilio", title: "Sr Backend Engineer", level: "Senior", startDate: "2022-08", endDate: "present", durationMonths: 45 },
      { company: "Postman", title: "Backend Engineer", level: "Mid", startDate: "2020-05", endDate: "2022-07", durationMonths: 26 },
    ],
    { profileCompleteness: 88, recruiterResponseRate: 0.85, githubActivityScore: 81 },
    38,
  ),

  // ===== Stretch hires (good now, lower trajectory) =====
  mk(
    "CAND_005",
    "Neha Reddy",
    "Senior Data Scientist @ HDFC",
    7,
    [
      { name: "Python", p: "expert" },
      { name: "PyTorch", p: "intermediate" },
      { name: "Kubernetes", p: "beginner" },
      { name: "Vector DB", p: "beginner" },
      { name: "Spark", p: "advanced" },
    ],
    [
      { company: "HDFC", title: "Sr Data Scientist", level: "Senior", startDate: "2019-01", endDate: "present", durationMonths: 89 },
    ],
    { profileCompleteness: 75, recruiterResponseRate: 0.7, githubActivityScore: 40 },
    71,
  ),

  // ===== Risky candidates =====
  mk(
    "CAND_006",
    "Rohan Kapoor",
    "ML Engineer (frequent moves)",
    4,
    [
      { name: "Python", p: "advanced" },
      { name: "PyTorch", p: "intermediate" },
      { name: "Kubernetes", p: "intermediate" },
      { name: "RAG", p: "beginner" },
    ],
    [
      { company: "StartupA", title: "ML Engineer", level: "Mid", startDate: "2025-09", endDate: "present", durationMonths: 9 },
      { company: "StartupB", title: "ML Engineer", level: "Mid", startDate: "2024-10", endDate: "2025-08", durationMonths: 10 },
      { company: "StartupC", title: "ML Engineer", level: "Junior", startDate: "2023-12", endDate: "2024-09", durationMonths: 9 },
      { company: "StartupD", title: "Jr Engineer", level: "Junior", startDate: "2022-05", endDate: "2023-11", durationMonths: 18 },
    ],
    { profileCompleteness: 60, recruiterResponseRate: 0.4, interviewCompletionRate: 0.55, githubActivityScore: 35 },
    55,
  ),

  // ===== Full-Stack pool (JOB_002) =====
  mk(
    "CAND_010",
    "Diya Krishnan",
    "Sr Full-Stack @ Atlassian",
    6,
    [
      { name: "TypeScript", p: "expert" },
      { name: "React", p: "expert" },
      { name: "Node.js", p: "expert" },
      { name: "Postgres", p: "advanced" },
      { name: "Next.js", p: "advanced" },
      { name: "GraphQL", p: "advanced" },
    ],
    [
      { company: "Atlassian", title: "Sr Engineer", level: "Senior", startDate: "2022-01", endDate: "present", durationMonths: 53 },
      { company: "Razorpay", title: "Engineer", level: "Mid", startDate: "2019-06", endDate: "2021-12", durationMonths: 31 },
    ],
    { profileCompleteness: 96, recruiterResponseRate: 0.98, githubActivityScore: 90 },
    88,
  ),
  mk(
    "CAND_011",
    "Faisal Ahmed",
    "Vue dev pivoting to React",
    4,
    [
      // Missing react — has Vue, Svelte, Next.js, TS, Node
      { name: "TypeScript", p: "advanced" },
      { name: "Vue", p: "expert" },
      { name: "Svelte", p: "intermediate" },
      { name: "Next.js", p: "advanced" },
      { name: "Node.js", p: "advanced" },
      { name: "Postgres", p: "intermediate" },
    ],
    [
      { company: "GoJek", title: "Sr Frontend", level: "Senior", startDate: "2023-03", endDate: "present", durationMonths: 39 },
      { company: "Tokopedia", title: "Frontend", level: "Mid", startDate: "2021-08", endDate: "2023-02", durationMonths: 18 },
    ],
    { profileCompleteness: 90, recruiterResponseRate: 0.9, githubActivityScore: 78 },
    44,
    "Jakarta, ID",
  ),
  mk(
    "CAND_012",
    "Sneha Gupta",
    "Full-Stack Engineer @ Freshworks",
    3,
    [
      { name: "TypeScript", p: "advanced" },
      { name: "React", p: "advanced" },
      { name: "Node.js", p: "intermediate" },
      { name: "Postgres", p: "intermediate" },
      { name: "Tailwindcss", p: "advanced" },
    ],
    [
      { company: "Freshworks", title: "Engineer", level: "Mid", startDate: "2023-07", endDate: "present", durationMonths: 35 },
      { company: "Zoho", title: "Jr Engineer", level: "Junior", startDate: "2022-05", endDate: "2023-06", durationMonths: 13 },
    ],
    { profileCompleteness: 87, recruiterResponseRate: 0.93, githubActivityScore: 70 },
    72,
    "Chennai, IN",
  ),
  mk(
    "CAND_013",
    "Marco Rossi",
    "React Native lead, web background",
    5,
    [
      { name: "TypeScript", p: "expert" },
      { name: "React", p: "expert" },
      { name: "Node.js", p: "advanced" },
      { name: "GraphQL", p: "advanced" },
      // Missing postgres — has mysql + supabase
      { name: "MySQL", p: "advanced" },
      { name: "Supabase", p: "intermediate" },
    ],
    [
      { company: "Satispay", title: "Lead Engineer", level: "Lead", startDate: "2022-09", endDate: "present", durationMonths: 45 },
      { company: "Bending Spoons", title: "Sr Engineer", level: "Senior", startDate: "2020-03", endDate: "2022-08", durationMonths: 29 },
    ],
    { profileCompleteness: 92, recruiterResponseRate: 0.88, githubActivityScore: 84 },
    48,
    "Milan, IT",
  ),

  // ===== DevOps pool (JOB_003) =====
  mk(
    "CAND_020",
    "Vikram Singh",
    "Platform Lead @ Ola",
    9,
    [
      { name: "Kubernetes", p: "expert" },
      { name: "Terraform", p: "expert" },
      { name: "AWS", p: "expert" },
      { name: "CI/CD", p: "expert" },
      { name: "Docker", p: "expert" },
      { name: "Helm", p: "advanced" },
      { name: "Go", p: "advanced" },
    ],
    [
      { company: "Ola", title: "Platform Lead", level: "Lead", startDate: "2021-06", endDate: "present", durationMonths: 60 },
      { company: "InMobi", title: "Sr SRE", level: "Senior", startDate: "2017-04", endDate: "2021-05", durationMonths: 49 },
    ],
    { profileCompleteness: 97, recruiterResponseRate: 0.97, githubActivityScore: 88 },
    93,
  ),
  mk(
    "CAND_021",
    "Ananya Pillai",
    "SRE with strong adjacency",
    5,
    [
      // Missing kubernetes + terraform but adjacent: docker, helm, ansible, pulumi, aws
      { name: "Docker", p: "expert" },
      { name: "Helm", p: "advanced" },
      { name: "Pulumi", p: "advanced" },
      { name: "Ansible", p: "advanced" },
      { name: "AWS", p: "advanced" },
      { name: "CI/CD", p: "expert" },
      { name: "Rust", p: "intermediate" },
    ],
    [
      { company: "Cloudflare", title: "SRE II", level: "Senior", startDate: "2022-11", endDate: "present", durationMonths: 43 },
      { company: "Atlassian", title: "SRE", level: "Mid", startDate: "2020-08", endDate: "2022-10", durationMonths: 26 },
    ],
    { profileCompleteness: 91, recruiterResponseRate: 0.94, githubActivityScore: 86 },
    41,
  ),
];

// Helper: filter candidates that are reasonable for a JD pool
export function poolForJob(jdId: string, all: Candidate[] = MOCK_CANDIDATES): Candidate[] {
  // For demo, every job gets the full pool — let the scoring engine decide.
  return all;
}
void NOW;
