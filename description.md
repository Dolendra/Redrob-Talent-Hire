# 🏆 TalentDNA AI — Hackathon Submission Details

---

## 👥 Team Name & Leader Information
* **Team Name:** TalentDNA AI (Team: Advait)
* **Team Leader Name:** Nelluri Dolendra Sai Teja
* **Contact Email:** dolendracse@gmail.com

---

## ❓ Problem Statement
Traditional Applicant Tracking Systems (ATS) rely on rigid keyword density, matching static skill lists rather than a candidate's actual trajectory. This creates:
1. **False Positives (The "Keyword Stuffer" Trap):** Non-technical candidates who pad their profiles with AI buzzwords are ranked too high.
2. **False Negatives (The "Hidden Gem" Miss):** High-velocity engineers with deep adjacent skills (e.g., matching a candidate who knows `pgvector` for a `Pinecone` database requirement) are instantly filtered out by exact-match rules.
3. **Compute and Resource Scale Constraints:** Systems must evaluate massive candidate pools (100,000+ deep JSON profiles) within strict sandboxed limits (≤ 5 minutes execution time, CPU-only, no active networks, and ≤ 16 GB RAM) without leaking resources or failing.

---

## 💡 Solution Overview

### What is your proposed solution?
TalentDNA AI is a high-speed, memory-optimized offline ranking engine designed specifically to process large-scale candidate datasets securely and locally.
* **Offline LLM Parser:** Replaces fragile regex parsing with a local, quantized `Llama-3-8B-Instruct GGUF` model running via `llama-cpp-python` (`n_threads=1`, `temperature=0.0`) to convert unformatted plain-text or PDF resumes into structured JSON schemas.
* **Two-Pass Streaming Ranker:** Reads the 465MB `candidates.jsonl` database line-by-line with $O(1)$ memory consumption, dynamically normalizing global pool metrics and sorting candidates using a bounded top-100 min-heap.

### What differentiates your approach from traditional candidate matching systems?
* **Contextual Parsing vs. Token Regex:** Our local LLM understands semantic structure, completely bypassing casing, punctuation, and typographical differences (e.g., accurately mapping 'Sentence Transformers' or 'sentence-transformers' to the same unified canonical schema item).
* **Trajectory-First Evaluation:** Instead of static counts, we compute three dynamic progression metrics: Skill Transferability ($ST$), Adaptability Score ($AS$), and Career Velocity ($CV$).
* **Anti-Pattern Extermination:** The system programmatically checks and penalizes duplicate timelines, impossible chronological dates, non-technical title padding, and consulting-firm-only careers.
* **100% Offline Integrity:** The engine does not make active API or network calls, utilizing precompiled vector spaces for skill mapping.

---

## 🎯 JD Understanding & Candidate Evaluation

### What are the key requirements extracted from the JD?
* **Required Technical Stack:** Dense/hybrid retrieval, vector infrastructures (FAISS, Milvus, Pinecone, Qdrant, Weaviate, Elasticsearch), sentence-transformers, BGE, E5, and evaluation metrics (NDCG, MAP, MRR).
* **Preferred Experience:** Parameter-Efficient Fine-Tuning (PEFT, LoRA, QLoRA), learning-to-rank, distributed engineering, and open-source contributions.
* **Demographic Boundaries:** 5 to 9 years of experience, localized across prime Indian tech regions (Pune, Noida, Hyderabad, Mumbai, Delhi NCR).

### Which candidate signals are most important for determining relevance? / How does your solution evaluate candidate fit beyond keyword matching?
* **Skill Transferability ($ST$):** We compute the cosine similarity between the candidate's existing skills and missing required skills using local `all-MiniLM-L6-v2` embeddings to identify high-affinity adjacent capabilities (e.g. pgvector $\rightarrow$ Pinecone).
* **Adaptability Score ($AS$):** Scans the candidate’s career history to count distinct technology transitions shipped over the trailing 36 months.
* **Career Velocity ($CV$):** Calculates the delta between seniority levels relative to years of experience, highlighting high-velocity career growth.
* **Hiring Risk / Friction ($R$):** Dynamically scales candidate utility using availability signals, recruiter response rates, and notice periods (applying deductions for 90-to-120-day notice periods).

---

## 📐 Ranking Methodology

### How does your system retrieve, score, and rank candidates?
* **Pass 1 (Global Stat Scan):** Streams the JSONL file to establish global min/max limits for Career Velocity and Adaptability.
* **Pass 2 (Composite Scoring & Top-K Heap):** Streams the JSONL again, scores each profile, and feeds them into a bounded min-heap (`heapq.nlargest(100)`). Maintains an $O(N \log K)$ runtime compute complexity and a strict $O(K)$ space complexity where $N = 100,000$ pool records and $K = 100$ target recommendations, preventing RAM degradation. The top 100 results are exported to `Advait.csv`.

### What models, algorithms, or heuristics are used?
* **Llama-3-8B-Instruct GGUF:** Quantized offline model used to parse plaintext inputs into target JSON format.
* **all-MiniLM-L6-v2:** Encodes unique skill keywords into a precompiled `skill_vectors.npz` dictionary.
* **Cosine Similarity:** Uses localized `NumPy` dot-product matrices to evaluate maximum cosine match scores.
* **Lexicographical Tie-Breaker:** Resolves matching scores ties by sorting alphabetically on `candidate_id` to enforce deterministic outputs.

### How are multiple candidate signals combined into a final ranking?
* Weighted composite optimization formula:
  $$\text{Composite} = 0.15 \cdot S_{\text{current}} + 0.30 \cdot \text{FutureFit} + 0.20 \cdot \text{HiddenGem} + 0.10 \cdot \text{Opportunity} + 0.05 \cdot \text{Confidence} + 0.05 \cdot \text{LocationFit} + 0.05 \cdot \text{ExperienceBand} + 0.10 \cdot \text{CareerIRSignal} - 0.15 \cdot \text{Risk} - \text{Penalties}$$
  * *Note: Final composite is scaled by `(0.35 + 0.65 * title_relevance)` to suppress non-technical keyword stuffers.*

---

## 🛡️ Explainability & Data Validation

### How are ranking decisions explained?
* **Fact-Slot Assembly Framework (`src/explainability.py`):** Generates deterministic, natural-language contrastive reasoning. E.g., *"Traditional ATS Filter Score: 52% (Missing exact token: Pinecone). TalentDNA Score: 91% (Highly adjacent vector match: FAISS/Milvus). Notice period: 30 days."*

### How do you prevent hallucinations or unsupported justifications?
* **Zero-LLM Pipeline Constraint at Rank Time:** To ensure deterministic execution and block hallucinations, no generative AI models are called during `rank.py`. Every word in the reasoning string is built from verified data tokens.

### How does your solution handle inconsistent, low-quality, or suspicious profiles?
* **Honeypot Extermination:** Impossible timelines or expert skills with 0 months duration trigger an immediate `-0.35` absolute composite deduction.
* **Role-Skill Mismatch:** Non-technical headlines (e.g. *Marketing Manager* with AI skills) are penalized and multiplier-suppressed.
* **Consulting-Only Career:** Consulting backgrounds without product offsets receive a `-0.20` penalty.

---

## 🔄 End-to-End Workflow

### What is the complete workflow from JD input to ranked candidate output?
```
[1. JD INPUT]       ───► Raw text or file parsed into structured targets via Llama-3-8B GGUF
                                │
[2. EMBEDDINGS]     ───► Compile unique skills into local skill_vectors.npz
                                │
[3. STREAM PASS 1]  ───► Collect global metrics (Velocity & Adaptability bounds)
                                │
[4. STREAM PASS 2]  ───► Compute composite scores & apply Trap/Honeypot penalties
                                │
[5. HEAP SELECTION] ───► Bounded Top-100 heap tracking + Lexicographical ID Tie-Breakers
                                │
[6. EXPLAINABILITY] ───► Fact-slot contrast cards generated for Top 100
                                │
[7. DELIVERABLE]    ───► Export finalized, validated "Advait.csv"
```

---

## 🏛️ System Architecture
The application consists of a four-layer modular architecture:
1. **Parser Layer (`src/parser.py`):** Handles gzip candidate parsing, schema conformance, and document ingestion.
2. **Feature Layer (`src/features.py`):** Computes time-series adaptability, seniority velocity, notice period risk, and anti-pattern triggers.
3. **Scoring Layer (`src/scoring.py`):** Runs precompiled vector similarities, normalizations, and weights composite.
4. **Explainability Layer (`src/explainability.py`):** Drives natural-language slot generation.
5. **Dashboard Layer (`dashboard/app.py`):** rec_command_center screen, talent map visualizations, and candidate pipeline selectors.

---

## 📊 Results & Performance

### What results or insights demonstrate ranking quality?
* **ATS Rescue (Saanvi Verma - `CAND_0008392`):** Rescued as a **Hidden Gem** (Future Fit 68%) due to her deep vector infrastructure work (`pgvector` at PolicyBazaar), despite missing the specific keyword `Pinecone`.
* **Notice Period / Availability (Ved Naidu - `CAND_0008412`):** Penalized and pushed down due to an extreme 90-day notice period and consulting-only background.
* **Top Rank Arjun Khanna (`CAND_0081846`):** Lead AI Engineer, ex-Razorpay, ex-Paytm. High Career Velocity, expert Elasticsearch/FAISS profile, and a sub-60-day notice.

### How does your solution meet the challenge’s runtime and compute constraints?
* **Time Performance:** Evaluates the entire 100,000 candidate pool in **under 3 minutes** (threshold: ≤ 5 minutes).
* **RAM & CPU Efficiency:** Streaming keeps RAM footprint minimal (< 200MB execution peaks), running purely on standard multi-core CPU threads.
* **Offline Security:** All vector similarities lookups are resolved offline using local `.npz` files (no active HTTP requests).

---

## 💻 Technologies Used

### What technologies, frameworks, and tools were used and why were they selected for this solution?
* **Python:** Standard language for rapid data manipulation and machine learning.
* **llama-cpp-python:** Selected for high-speed, local quantized GGUF Llama model execution without external API dependencies.
* **NumPy:** Leveraged for precompiled embedding representations and fast matrix-based cosine lookups on CPU.
* **Sentence-Transformers (all-MiniLM-L6-v2):** Selected for high-fidelity, CPU-efficient sentence embeddings.
* **Pydantic v2 & jsonschema:** Selected to enforce strict candidate schema validation and data integrity.
* **Streamlit & Plotly:** Used to build the recruiter dashboard and interactive quadrant charts locally.

---

## 📂 Submission Assets
* **Core Ranking Output:** `Advait.csv` (Top 100 candidate table conforming to schema limits and sort rules).
* **Format Validator:** `validate_submission.py` to test and ensure formatting compliance.
* **Interactive Dashboard:** `app.py` (Local Streamlit recruitment visual suite).
* **GitHub Code Repository:** [https://github.com/Dolendra/Redrob-Talent-Hire](https://github.com/Dolendra/Redrob-Talent-Hire)
* **Live Sandbox Link:** [https://huggingface.co/spaces/Dolendra/Redrob-Talent-Hire](https://huggingface.co/spaces/Dolendra/Redrob-Talent-Hire)
* **GitHub Video Demo:** *(Optional - To be recorded and linked by the participant)*
