# src/ingestion.py
import json
import re
from pathlib import Path
from typing import Dict, Any, List
from src.resume_parser import ResumeParser, LocalModelParserService

def find_local_gguf_model() -> Path:
    # 1. Search in models/ subdirectory (recursively)
    models_dir = Path("models")
    if models_dir.exists() and models_dir.is_dir():
        for p in models_dir.rglob("*.gguf"):
            return p
    # 2. Search in data/ subdirectory
    data_dir = Path("data")
    if data_dir.exists() and data_dir.is_dir():
        for p in data_dir.rglob("*.gguf"):
            return p
    # 3. Search in current working directory
    for p in Path(".").glob("*.gguf"):
        return p
    # 4. Fallback default
    return Path("models/Llama-3-8B-Instruct.Q4_K_M.gguf")

class ProductionIngestionService:
    def __init__(self, schema_path: Path):
        self.schema_path = schema_path
        self.parser = ResumeParser(schema_path=schema_path)
        self.active_filename = "resume.pdf"
        
        # Auto-detect local GGUF model and initialize the LocalModelParserService
        model_path = find_local_gguf_model()
        self.local_parser = LocalModelParserService(model_path=model_path, schema_path=schema_path)


    def extract_document_text(self, file_path: Path) -> str:
        """High-speed text extraction from common resume payloads."""
        self.active_filename = file_path.name
        suffix = file_path.suffix.lower()
        if suffix in [".txt", ".md"]:
            try:
                import chardet
                raw_bytes = file_path.read_bytes()
                detected = chardet.detect(raw_bytes)
                encoding = detected.get("encoding") or "utf-8"
                return raw_bytes.decode(encoding, errors="ignore")
            except Exception:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
        elif suffix == ".docx":
            try:
                import docx
            except ImportError as e:
                raise ImportError("python-docx is required to parse .docx resumes.") from e
            doc = docx.Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        elif suffix == ".pdf":
            try:
                import pypdf
            except ImportError as e:
                raise ImportError("pypdf is required to parse .pdf resumes.") from e
            reader = pypdf.PdfReader(file_path)
            pages_text = []
            for page in reader.pages:
                try:
                    # layout mode preserves columns and reads top-to-bottom
                    text = page.extract_text(extraction_mode="layout")
                except Exception:
                    text = page.extract_text()
                if text:
                    pages_text.append(text)
            return "\n".join(pages_text)
        return ""

    def rule_based_ner_normalizer(self, raw_text: str, skill_vocabulary: List[str]) -> Dict[str, Any]:
        """
        Production-grade token extractor. Extracts and structures profile fields.
        """
        # Load master vocabulary from config/weights.json
        master_vocab = set()
        try:
            weights_path = Path("config/weights.json")
            if weights_path.exists():
                with open(weights_path, "r", encoding="utf-8") as f:
                    weights = json.load(f)
                    
                # 1. jd_skill_seeds
                seeds = weights.get("jd_skill_seeds", {})
                for s in seeds.get("required", []) + seeds.get("preferred", []):
                    master_vocab.add(s)
                    
                # 2. skill_clusters
                clusters = weights.get("skill_clusters", {})
                for k, v in clusters.items():
                    master_vocab.add(k)
                    for s in v:
                        master_vocab.add(s)
                        
                # 3. skill_adjacency
                adjacency = weights.get("skill_adjacency", {})
                for k, v in adjacency.items():
                    master_vocab.add(k)
                    for s in v:
                        master_vocab.add(s)
        except Exception:
            pass
            
        # Add popular baseline technologies that candidates commonly list
        popular_techs = [
            "Java", "JavaScript", "React.js", "React", "Node.js", "Node", "Express.js", "Express", 
            "Docker", "Jenkins", "FAISS", "Terraform", "AWS", "GCP", "Azure", "Kubernetes", "K8s",
            "Git", "GitHub", "HTML", "CSS", "C++", "Go", "Rust", "FastAPI", "Flask", "Django", 
            "SQL", "PostgreSQL", "MySQL", "MongoDB", "Python", "Pinecone", "Weaviate", "Qdrant",
            "Milvus", "OpenSearch", "Elasticsearch", "RAG", "LLM", "embeddings", "retrieval", "NDCG"
        ]
        for tech in popular_techs:
            master_vocab.add(tech)
            
        # Merge the active skill_vocabulary passed from the workspace context
        if skill_vocabulary:
            for s in skill_vocabulary:
                master_vocab.add(s)
                
        # Try local LLM parsing first if engine is active
        if self.local_parser.llm is not None:
            try:
                print(f"Parsing resume using local LLM model from: {self.local_parser.llm.model_path}")
                parsed_data = self.local_parser.parse_resume_to_schema(raw_text)
                if parsed_data and "error" not in parsed_data:
                    # Map the parsed JSON fields back to the normalizer dictionary layout
                    profile = parsed_data.get("profile", {})
                    name = profile.get("anonymized_name", "") or profile.get("name", "")
                    if not name:
                        name = self.parser.extract_name(raw_text)
                        
                    current_title = profile.get("current_title", "")
                    current_company = profile.get("current_company", "")
                    
                    location = profile.get("location", "Bangalore")
                    country = profile.get("country", "India")
                    
                    try:
                        years_of_experience = float(profile.get("years_of_experience", 3.0))
                    except Exception:
                        years_of_experience = 3.0
                        
                    skills = parsed_data.get("skills", [])
                    # Ensure skills has the correct schema (name, proficiency, endorsements)
                    normalized_skills = []
                    for s in skills:
                        if isinstance(s, dict) and "name" in s:
                            duration = s.get("duration_months")
                            if duration is None:
                                duration = int(years_of_experience * 12)
                            normalized_skills.append({
                                "name": s.get("name"),
                                "proficiency": s.get("proficiency", "intermediate"),
                                "endorsements": int(s.get("endorsements", 1)),
                                "duration_months": int(duration)
                            })
                        elif isinstance(s, str):
                            normalized_skills.append({
                                "name": s,
                                "proficiency": "intermediate",
                                "endorsements": 1,
                                "duration_months": int(years_of_experience * 12)
                            })
                            
                    career_history = parsed_data.get("career_history", [])
                    for role in career_history:
                        if "company" not in role:
                            role["company"] = "Enterprise Corporation"
                        if "title" not in role:
                            role["title"] = "Software Engineer"
                        if "start_date" not in role:
                            role["start_date"] = "2022-01-01"
                        if "end_date" not in role:
                            role["end_date"] = None
                        if "duration_months" not in role:
                            role["duration_months"] = 12
                        if "is_current" not in role:
                            role["is_current"] = role.get("end_date") is None
                        if "industry" not in role:
                            role["industry"] = "Information Technology"
                        if "company_size" not in role:
                            role["company_size"] = "51-200"
                        if "description" not in role:
                            role["description"] = "Role description"
                            
                    education = parsed_data.get("education", [])
                    for edu in education:
                        if "institution" not in edu:
                            edu["institution"] = "Tier 3 University"
                        if "degree" not in edu:
                            edu["degree"] = "Bachelor of Science"
                        if "field_of_study" not in edu:
                            edu["field_of_study"] = "Computer Science"
                        if "start_year" not in edu:
                            edu["start_year"] = 2018
                        if "end_year" not in edu:
                            edu["end_year"] = 2022
                        if "tier" not in edu:
                            edu["tier"] = "unknown"
                            
                    certifications = parsed_data.get("certifications", [])
                    languages = parsed_data.get("languages", [])
                    
                    if career_history and not current_title:
                        current_title = career_history[0].get("title", "Software Engineer")
                    if career_history and not current_company:
                        current_company = career_history[0].get("company", "Enterprise Corporation")
                        
                    industry = profile.get("current_industry", "")
                    if not industry:
                        industry = self.parser.classify_industry(current_title or "Software Engineer", normalized_skills)
                        
                    return {
                        "name": name,
                        "current_title": current_title or "Software Engineer",
                        "current_company": current_company or "Enterprise Corporation",
                        "location": location,
                        "country": country,
                        "years_of_experience": years_of_experience,
                        "skills": normalized_skills,
                        "career_history": career_history,
                        "education": education,
                        "certifications": certifications,
                        "languages": languages,
                        "industry": industry,
                        "raw_text_snapshot": raw_text[:2000]
                    }
                else:
                    print(f"Warning: Local LLM returned parsing error: {parsed_data.get('error') if parsed_data else 'None'}. Falling back to default regex parser.")
            except Exception as e:
                print(f"Warning: Failed parsing using local LLM engine: {e}. Falling back to default regex parser.")

        merged_vocabulary = list(master_vocab)

        name = self.parser.extract_name(raw_text)
        city, country = self.parser.extract_location(raw_text)
        career_history = self.parser.extract_career_history(raw_text)
        
        # Estimate experience
        total_months = sum(r["duration_months"] for r in career_history)
        years_of_experience = min(30.0, round(total_months / 12.0, 1))
        if years_of_experience <= 0:
            years_of_experience = 3.0
            
        skills = self.parser.extract_skills(raw_text, merged_vocabulary, career_history, years_of_experience)
        education = self.parser.extract_education(raw_text)
        certifications = self.parser.extract_certifications(raw_text)
        languages = self.parser.extract_languages(raw_text)
        
        current_title = "Software Engineer"
        current_company = "Enterprise Corporation"
        if career_history:
            current_title = career_history[0]["title"]
            current_company = career_history[0]["company"]
            
        industry = self.parser.classify_industry(current_title, skills)
        
        return {
            "name": name,
            "current_title": current_title,
            "current_company": current_company,
            "location": city,
            "country": country,
            "years_of_experience": years_of_experience,
            "skills": skills,
            "career_history": career_history,
            "education": education,
            "certifications": certifications,
            "languages": languages,
            "industry": industry,
            "raw_text_snapshot": raw_text[:2000]
        }


    def compile_to_schema_row(self, normalized_features: Dict[str, Any]) -> Dict[str, Any]:
        """Converts extracted text metrics into a valid, schema-compliant dictionary."""
        candidate_id = self.parser.extract_candidate_id(self.active_filename, normalized_features["raw_text_snapshot"])
        
        profile = {
            "anonymized_name": normalized_features["name"],
            "headline": f"{normalized_features['current_title']} with {normalized_features['years_of_experience']:.1f} years of experience",
            "summary": normalized_features["raw_text_snapshot"][:500],
            "location": normalized_features["location"],
            "country": normalized_features["country"],
            "years_of_experience": float(normalized_features["years_of_experience"]),
            "current_title": normalized_features["current_title"],
            "current_company": normalized_features["current_company"],
            "current_company_size": "51-200",
            "current_industry": normalized_features["industry"]
        }
        
        signals = self.parser.build_redrob_signals()
        
        raw_dict = {
            "candidate_id": candidate_id,
            "profile": profile,
            "skills": normalized_features["skills"],
            "career_history": normalized_features["career_history"],
            "education": normalized_features["education"],
            "certifications": normalized_features["certifications"],
            "languages": normalized_features["languages"],
            "redrob_signals": signals
        }
        
        # Repair schema mismatch in-place if needed
        if self.parser.schema:
            fixed_dict, errors = self.parser.validate_and_fix(raw_dict, self.parser.schema)
            return fixed_dict
            
        return raw_dict
