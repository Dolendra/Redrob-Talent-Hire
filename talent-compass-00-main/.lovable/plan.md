# TalentDNA AI — Hackathon Demo Dashboard

A polished React dashboard that replaces the proposed Streamlit UI. Built entirely on the frontend so it boots instantly for judges, with mock candidate/JD data wired into a real scoring engine that mirrors your Python formulas exactly. No backend, no auth, no upload-to-cloud — everything runs in-browser so the demo is bulletproof on stage.

## Scope

In scope (the 4 screens you confirmed):
1. Recruiter Dashboard + Talent Opportunity Map (quadrant chart)
2. Create New Job (JD authoring form)
3. Upload Candidate Resume (PDF/DOCX ingestion preview)
4. Per-candidate TalentDNA report (Current vs Future Fit, Risk, Onboarding, "Why ATS missed")

Out of scope (intentionally):
- The Python `rank.py` Stage-3 submission engine — keep that air-gapped in your separate repo
- Auth, multi-user, persistence to a real DB (uses localStorage so refresh keeps state)
- Live LLM calls / paid APIs

## Information architecture

```
/                          → Recruiter Dashboard (jobs list + KPIs + opportunity map for selected JD)
/jobs/new                  → Create New Job form
/jobs/$jobId               → Job detail: ranked candidates table + filters + quadrant
/jobs/$jobId/candidates/$candidateId → TalentDNA report (the 30-second recruiter card)
/upload                    → Upload Candidate Resume (drag-drop, schema preview, assign to JD)
```

Sidebar navigation (shadcn `Sidebar`, collapsible to icons) with: Dashboard, Jobs, Upload Candidate, Settings (stub).

## Screen-by-screen

**1. Recruiter Dashboard (`/`)**
- Top KPI row: Active JDs, Tracked Candidates, Hidden Gems Found, Avg Time-to-Shortlist
- JD selector (segmented control or dropdown)
- Hero panel: **Talent Opportunity Map** — scatter plot, X = Current Fit, Y = Future Fit, bubble size = Confidence, color = Risk bucket. Quadrant labels: *Safe Hires* (top-right), *Hidden Gems* (top-left), *Stretch* (bottom-right), *Pass* (bottom-left).
- Side panel: Top 5 Hidden Gems list with "Why ATS missed this" one-liner

**2. Create New Job (`/jobs/new`)**
- Form: title, description (textarea), required skills (tag input), preferred skills (tag input), min/max experience, location, weights override (collapsible advanced section)
- Live preview card on the right showing the parsed "Job DNA matrix"
- Submit → persists to localStorage, navigates to `/jobs/$jobId`

**3. Upload Candidate Resume (`/upload`)**
- Drag-drop zone (accept .pdf, .docx, .txt) — uses `pdfjs-dist` + `mammoth` in-browser for actual text extraction (no server)
- Target JD selector
- After parse: shows extracted text + normalized JSON schema (rule-based skill matching against the JD's vocabulary)
- "Add to candidate pool" button → runs scoring, navigates to candidate report

**4. TalentDNA Report (`/jobs/$jobId/candidates/$candidateId`)**
- Header: name, current title, recommendation badge (Strong Hire / Consider / Pass)
- Two big radial gauges: Current Fit, Future Fit
- Comparison strip: **ATS Score: 62 vs TalentDNA: 91** with "Why ATS Missed This Candidate" reasoning bullets
- Cards: Growth Velocity, Risk Score breakdown (job-hopping, ghosting, drop-off), Onboarding Cost Index (weeks)
- Skill adjacency graph: required skills vs candidate skills vs adjacent skills they have
- Career timeline (horizontal)

## Scoring engine (TypeScript, in `/src/lib/scoring/`)

Mirrors your Python formulas exactly so you can defend numbers in Q&A:
- `currentFit.ts` — cosine-similarity-style match using a hand-built embedding of the canonical skill vocabulary (small lookup, no model needed for demo)
- `futureFit.ts` — `currentFit + (100 - currentFit) × adjacency% × velocity`
- `hiddenGem.ts` — `futureFit × confidence × (1 - currentFit)`
- `onboardingCost.ts` — weeks penalty per missing skill, adjusted by learning velocity
- `riskScore.ts` — job-hopping + ghosting + drop-off penalties
- `skillAdjacency.ts` — pre-mapped neighbor graph (Kubernetes → Docker/Helm/Terraform/ECS, etc.)

## Mock data

`/src/data/mockCandidates.ts` (~50 candidates) and `/src/data/mockJobs.ts` (3 JDs: Senior ML Engineer, Full-Stack Engineer, DevOps Lead). Engineered to include obvious hidden gems so the quadrant chart tells a story.

## Design direction

Dark, dense, data-forward — recruiter command-center feel (think Linear × Pitchbook × Bloomberg Terminal, not generic SaaS pastel). Mono accent font for numbers, sans for body. Single signature accent color (electric green or amber) used only for "Hidden Gem" highlights so they pop on the map. Custom design tokens in `src/styles.css`, no purple-gradient-on-white.

## Tech stack

- TanStack Start (already set up) + TanStack Router for the 5 routes
- shadcn components: Sidebar, Card, Table, Tabs, Form, Dialog, Badge
- Recharts for the quadrant scatter, radial gauges, timeline
- `pdfjs-dist` + `mammoth` for in-browser PDF/DOCX parsing
- `framer-motion` for the one hero animation (quadrant points settling in)
- localStorage for state persistence — no Lovable Cloud needed

## Build order

1. Design tokens + sidebar shell + routes scaffolding
2. Mock data + scoring engine (pure TS, unit-testable)
3. Recruiter Dashboard + Talent Opportunity Map
4. Job detail + ranked candidates table
5. TalentDNA report (the money screen)
6. Create New Job form
7. Upload Candidate Resume + in-browser parsing
8. Polish: animations, empty states, loading shimmer

## New ideas worth adding (optional, ask before I build)

- **"Explain this score" tooltip** on every metric — clicking shows the literal formula with the candidate's numbers plugged in. Judges love seeing the math.
- **Side-by-side compare** (2-3 candidates) — column view of TalentDNA reports for shortlist decisions.
- **"Bias check" panel** on the dashboard — shows demographic-blind stats of your top 10 vs the full pool to demonstrate fairness.
- **Shareable read-only report link** (just a URL with state encoded) — judges can open the candidate report on their phone during pitch.

Reply with which (if any) of those optional ideas to include, and I'll start building. If you want to explore visual directions first (dark terminal vs editorial vs neo-brutalist), say the word and I'll generate 3 prototypes to pick from.
