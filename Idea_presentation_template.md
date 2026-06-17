# 🏆 INDIA.RUNS Hackathon Slide Presentation - TalentDNA AI

---

## Slide 1: Title & Cover

* **Event Branding:** redrob × H2S | INDIA.RUNS (Build what next India runs on)
* **Team Name:** TalentDNA AI (Team: Advait)
* **Team Leader Name:** Nelluri Dolendra Sai Teja
* **Contact:** dolendracse@gmail.com

### Problem Statement:
Traditional Applicant Tracking Systems (ATS) rely on rigid keyword density, matching static skill lists rather than a candidate's actual trajectory. This creates high false-positive rates for keyword-stuffed profiles and false-negatives for "Hidden Gems" who possess adjacent, transferable technical capabilities and high career velocity. Additionally, modern recruitment pipelines must scale to evaluate large pools (100,000+ candidates) within strict, air-gapped resource constraints (≤ 5 minutes, CPU-only, no active networks) without throwing out valid talent.

---

## Slide 2: Solution Overview

### What is your proposed solution?
* **TalentDNA AI** is a high-speed, memory-optimized ranking engine built specifically to process large-scale recruitment datasets locally and securely.
* It completely eliminates fragile, hardcoded regex text filters by implementing an offline **Local Quantized LLM Parsing Service** (`llama-cpp-python`) that understands deep resume context.
* Parsed profiles pass into a deterministic **Two-Pass Streaming Pipeline** combined with a bounded **Top-100 Minimum Heap** to extract the absolute highest-probability hires without exceeding memory limits.

### What differentiates your approach from traditional candidate matching systems?
* **Contextual Understanding Over Regex:** Our local LLM understands semantic structure, completely bypassing casing, punctuation, and typographical differences (e.g., accurately mapping 'Sentence Transformers' or 'sentence-transformers' to the same unified canonical schema item).
* **Trajectory-First Evaluation:** Instead of just counting keyword occurrences, our system evaluates candidate trajectory through three custom metrics: Skill Transferability ($ST$), Adaptability Score ($AS$), and Career Velocity ($CV$).
* **Anti-Pattern & Trap Filtering:** It actively detects and penalizes optimized "trap" profiles (such as keyword-stuffed resumes and duplicate/impossible career timelines) that standard keyword filters rank too high.
* **100% Offline Integrity:** Runs completely air-gapped on standard hardware, utilizing precompiled vector space lookups to achieve zero active API dependency during ranking execution.

---

## Slide 3: JD Understanding & Candidate Evaluation

### What are the key requirements extracted from the JD?
* **Core Required Tech Stack:** Dense/hybrid retrieval, vector infrastructures (FAISS, Milvus, Pinecone, Qdrant), sentence-transformers, BGE, E5, and ranking evaluation metrics (NDCG, MAP, MRR).
* **Preferred Additions:** Parameter-Efficient Fine-Tuning (PEFT, LoRA, QLoRA), learning-to-rank, and distributed system engineering.
* **Target Bounds:** 5 to 9 years of experience, localized across prime tech regions (Pune, Noida, Hyderabad, Mumbai, Delhi NCR).

### Which candidate signals are most important for determining relevance? / How does your solution evaluate candidate fit beyond keyword matching?
* **Skill Transferability ($ST$):** Computes semantic similarity over missing keywords using vector math to find highly valuable adjacent skills (e.g., matching a candidate with deep vector infrastructure knowledge like `pgvector` even if they omit a specific keyword like `Pinecone`).
* **Adaptability Score ($AS$):** Scans historical experience timelines to calculate how rapidly a candidate has picked up and shipped new technologies over the trailing 36 months.
* **Career Velocity ($CV$):** Evaluates how quickly a candidate climbs internal organizational tiers relative to their total years in the field.
* **Hiring Risk / Real-World Friction Index ($R$):** Dynamically tracks real-world onboarding blockers like long company notice periods (e.g., 90-to-120 days) and penalizes them to balance immediate business needs.

---

## Slide 4: Ranking Methodology

### How does your system retrieve, score, and rank candidates?
* The system uses a two-pass stream framework. **Pass 1** scans the full dataset to establish global min/max limits for mathematical normalization. **Pass 2** scores each candidate and pushes them through a size-constrained min-heap to extract the absolute Top 100 rows. Maintains an $O(N \log K)$ runtime compute complexity and a strict $O(K)$ space complexity where $N = 100,000$ pool records and $K = 100$ target recommendations, preventing RAM degradation.

### What models, algorithms, or heuristics are used?
* **Local Schema Processing:** Uses an offline, quantized `Llama-3-8B-Instruct GGUF` model run via single-threaded orchestration (`n_threads=1`) to parse unformatted resumes into structured schemas.
* **Vector Embeddings:** Pre-compiled skill text mappings generated via the `all-MiniLM-L6-v2` transformer model.
* **Fast Math Execution:** Cosine similarities are evaluated using high-speed, localized `NumPy` matrix lookups to protect the CPU time limit.

### How are multiple candidate signals combined into a final ranking?
* Signals are combined into a balanced optimization composite score:
  $$\text{Composite} = 0.15 \cdot S_{\text{current}} + 0.30 \cdot \text{FutureFit} + 0.20 \cdot \text{HiddenGem} + 0.10 \cdot \text{Opportunity} + 0.05 \cdot \text{Confidence} + 0.05 \cdot \text{LocationFit} + 0.05 \cdot \text{ExperienceBand} + 0.10 \cdot \text{CareerIRSignal} - 0.15 \cdot \text{Risk} - \text{Penalties}$$
* **Tie-Breaking Guard:** Sorted explicitly by `(-composite, candidate_id)`. If two candidates tie on score, the engine performs a strict lexicographical ID comparison to eliminate ranking collisions.

---

## Slide 5: Explainability & Data Validation

### How are ranking decisions explained?
* The system utilizes a **Fact-Slot Assembly Framework** inside `explainability.py`. It generates highly realistic, unique human-sounding justifications based directly on the candidate's real metrics (e.g., *"Traditional ATS Filter Score: 52% (Missing exact token: Pinecone). TalentDNA Score: 91% (Highly adjacent vector match: FAISS/Milvus)..."*).

### How do you prevent hallucinations or unsupported justifications?
* **Zero-LLM Pipeline Constraint during Ranking:** While a local LLM is used to safely convert plain text to JSON objects at ingestion, no generative AI models are called during the math-intensive ranking stage in `rank.py`. Every word in the reasoning string is built deterministically from verified profile tokens.

### How does your solution handle inconsistent, low-quality, or suspicious profiles?
* **Honeypot Extermination:** Profiles with impossible timeline structures or fake expert levels instantly trigger a maximum execution penalty (`honeypot_penalty = 0.35`), dropping them from the ranks.
* **Role-Skill Mismatch Detection:** Captures non-technical titles (like Marketing/HR Managers, e.g., `CAND_0008412`) that have been heavily padded with AI keywords, applying a severe composite score deduction (`role_skill_mismatch = 0.35` penalty, suppressing composite to 0.35×).
* **Consulting-Only Career:** All roles at TCS/Infosys/Wipro/Accenture/Cognizant/Capgemini trigger a `0.20` penalty without any product-company offset.

---

## Slide 6: End-to-End Workflow

```
[1. RESUME INGEST]   ───► Local Llama-3-8B GGUF Model parses plain text to structured JSONL
                                │
[2. STREAM PASS 1]   ───► Stream candidates.jsonl line-by-line (0MB Memory footprint)
                     ───► Calculate and store global pool metrics (Velocity min/max)
                                │
[3. STREAM PASS 2]   ───► Stream file again ──► Compute Current Fit + Future Fit vectors
                     ───► Apply Honeypot filters & Anti-Pattern Trap deductions
                                │
[4. MIN-HEAP BIND]   ───► Maintain strict size-100 Min-Heap tracking top candidates
                     ───► Execute Lexicographical Candidate ID Tie-Breakers
                                │
[5. EXPLAINABILITY]  ───► Map top 100 rows through Fact-Slot Context Builder
                                │
[6. FILE OUTPUTS]    ───► Export finalized, format-verified "Advait.csv" sheet
```

* **Constraints Met:** Bounded runtime of ≤ 5 minutes on CPU-only, keeping RAM limit under 16 GB for 100K streaming JSONL lines with zero active network calls during `rank.py`.

---

## Slide 7: System Architecture

```
 ┌─────────────────────────────────────────────────────────────────┐
 │                       INPUT DATA LAYER                          │
 │  • data/job_description.md     • data/candidates.jsonl          │
 │  • config/weights.json         • config/candidate_schema.json   │
 └────────────────────────────────┬────────────────────────────────┘
                                  │
                                  ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │               LOCAL OFFLINE LLM PARSING SERVICE                 │
 │  • llama-cpp-python Context Engine  • Llama-3-8B-Instruct GGUF  │
 │  • Zero-Regex Context Mapper        • Zero-Temperature Lock     │
 └────────────────────────────────┬────────────────────────────────┘
                                  │
                                  ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │                     TALENTDNA CORE ENGINE                       │
 │  • S_current Vector Lookup     • Skill Transferability (ST)     │
 │  • Adaptability Tracking (AS)  • Career Growth Velocity (CV)    │
 └────────────────────────────────┬────────────────────────────────┘
                                  │
                                  ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │                     OPTIMIZATION LAYER                          │
 │  • Trap/Honeypot Filter        • Hiring Risk (R) Penalty        │
 │  • Size-100 Min-Heap Track     • Lexicographical Tie-Breaker    │
 └────────────────────────────────┬────────────────────────────────┘
                                  │
                                  ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │                       OUTPUT DELIVERABLE                        │
 │  • Advait.csv (Top 100 Rows + Verified Human Reasoning Logs)     │
 └─────────────────────────────────────────────────────────────────┘
```

* **Orchestrator Flow:** `src/main.py` → `rank.py CLI` → `validate_submission.py` → `submission.csv` + `output/analytics.csv` + `output/results.json`.

---

## Slide 8: Results & Performance

### What results or insights demonstrate ranking quality?
* **ATS Rescue Demos:** High-potential candidates like **Saanvi Verma** (`CAND_0008392`)—who would be instantly rejected by standard ATS tools for missing exact text phrases—are successfully rescued and flagged as viable Hidden Gems due to semantic vector mapping (`pgvector` $\rightarrow$ search infrastructure).
* **Risk-Aware Trade-offs:** Candidates with great technical alignment but carrying extreme 90-to-120-day notice periods are penalized and shifted to Unaligned (e.g. **Ved Naidu** (`CAND_0008412`) or others with consulting-only career traps), allowing high-velocity engineers with immediate availability to bubble up.
* **Top 1 Candidate (Arjun Khanna - CAND_0081846):** Rebuilt matching pipelines (NDCG@10 0.72 $\rightarrow$ 0.91) serving 50M+ queries at Razorpay, expert in Elasticsearch/FAISS, high career velocity (6.7 years).

### How does your solution meet the challenge's runtime and compute constraints?
* **Time Performance:** Evaluates the entire 100,000 candidate dataset in under 3 minutes, easily beating the ≤ 5-minute hackathon threshold.
* **Hardware Efficiency:** CPU-only processing loop that keeps a near-zero memory footprint, running safely inside standard 16 GB RAM limitations without memory overhead.
* **Network Isolation:** Fully respects the offline constraint by handling embedding lookups via local `.npz` vector arrays.

---

## Slide 9: Technologies Used

* **Core Logic & Parsing:**
  * **Python:** Primary engine execution language.
  * **llama-cpp-python:** Drives the offline, GGUF local model execution layer.
  * **NumPy:** Powers lightning-fast vector dot-products and cosine operations locally.
  * **Sentence-Transformers:** `all-MiniLM-L6-v2` used offline for high-speed semantic skill mapping.
* **Data Validation & Ingestion:**
  * **Pydantic v2:** Maintains clean internal structures for candidate records.
  * **jsonschema:** Validates input file formatting line-by-line to handle irregular data safely.
  * **pypdf & docx2txt:** Handles structural plain-text extractions across varying file uploads.
* **Execution Infrastructure:**
  * **argparse & sys:** Drives the rigid, reproducible CLI interface inside `rank.py`.

---

## Slide 10: Submission Assets

* **GitHub Code Repository:** [https://github.com/Dolendra/Redrob-Talent-Hire](https://github.com/Dolendra/Redrob-Talent-Hire)
* **Interactive Hosted Demo Link:** [https://huggingface.co/spaces/Dolendra/Redrob-Talent-Hire](https://huggingface.co/spaces/Dolendra/Redrob-Talent-Hire) (Hosted live dashboard running on sandboxed data pools for visual verification)
* **Core Submission Output:** `Advait.csv` (Contains exactly 100 data rows, ordered monotonically, with strict tie-breaking applied)
* **Validation Verification Asset:** `validate_submission.py` run locally against the output file, verifying that it passes the official structural tests with 0 formatting errors.
