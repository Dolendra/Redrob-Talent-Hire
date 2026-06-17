#!/usr/bin/env python3
"""Generate synthetic, schema-compliant candidates for validation and test runs."""

import argparse
import sys
import json
import random
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.resume_parser import ResumeParser

FIRST_NAMES = ["Advait", "Rohan", "Priya", "Amit", "Nisha", "Suresh", "Vikram", "Sneha", "Karan", "Anjali", "David", "Emma", "Alex", "Sophia", "Ryan"]
LAST_NAMES = ["Sharma", "Patel", "Kumar", "Singh", "Joshi", "Das", "Mehta", "Iyer", "Nair", "Reddy", "Smith", "Jones", "Miller", "Davis", "Wilson"]
CITIES = [("Pune", "India"), ("Bangalore", "India"), ("Noida", "India"), ("Hyderabad", "India"), ("Mumbai", "India"), ("Delhi", "India"), ("Gurgaon", "India")]
COMPANIES = ["Enterprise Corporation", "Cognitive Systems", "InnovaTech Solutions", "Apex Global", "Synergy Labs", "Pixel Craft", "Blue Sky Ventures"]
TITLES = ["Machine Learning Engineer", "Software Engineer", "Backend Engineer", "Data Scientist", "Lead AI Engineer", "AI Architect"]
SKILLS_LIST = [
    "embeddings", "sentence-transformers", "BGE", "E5", "retrieval", "vector database", "Pinecone",
    "Weaviate", "Qdrant", "Milvus", "OpenSearch", "Elasticsearch", "FAISS", "hybrid search", "Python",
    "NDCG", "MRR", "MAP", "ranking evaluation", "A/B testing", "LoRA", "QLoRA", "PEFT", "fine-tuning",
    "learning to rank", "XGBoost", "Spark", "SQL", "Docker", "Kubernetes", "Git", "PyTorch", "TensorFlow"
]

def generate_candidate(cid_num: int) -> dict:
    fname = random.choice(FIRST_NAMES)
    lname = random.choice(LAST_NAMES)
    name = f"{fname} {lname}"
    title = random.choice(TITLES)
    city, country = random.choice(CITIES)
    yexp = round(random.uniform(3.0, 12.0), 1)
    
    # Career history
    history = []
    comp_size = "51-200"
    industry = "Information Technology"
    
    start_year = 2026 - int(yexp)
    start_date = f"{start_year}-06-16"
    end_date = None
    
    history.append({
        "company": random.choice(COMPANIES),
        "title": title,
        "start_date": f"{2024}-01-01",
        "end_date": end_date,
        "duration_months": int((2026 - 2024) * 12 + 5),
        "is_current": True,
        "industry": industry,
        "company_size": comp_size,
        "description": f"Worked as {title} developing deep learning and search capabilities."
    })
    
    if yexp > 5.0:
        history.append({
            "company": random.choice(COMPANIES),
            "title": "Junior Engineer",
            "start_date": f"{start_year}-06-16",
            "end_date": f"2023-12-31",
            "duration_months": int((2023 - start_year) * 12 + 6),
            "is_current": False,
            "industry": industry,
            "company_size": comp_size,
            "description": "Implemented microservices, worked on bugs, and learned backend development."
        })
        
    # Skills
    skills = []
    selected_skills = random.sample(SKILLS_LIST, random.randint(5, 10))
    for s in selected_skills:
        freq = random.randint(1, 6)
        prof = "expert" if freq >= 5 else "advanced" if freq >= 3 else "intermediate" if freq >= 2 else "beginner"
        skills.append({
            "name": s,
            "proficiency": prof,
            "endorsements": random.randint(0, 15),
            "duration_months": random.randint(6, 48)
        })
        
    # Education
    education = [{
        "institution": "Pune University",
        "degree": "Bachelor of Technology",
        "field_of_study": "Computer Science",
        "start_year": start_year - 4,
        "end_year": start_year,
        "grade": "First Class",
        "tier": "tier_3"
    }]
    
    # Certifications
    certs = []
    if random.random() > 0.5:
        certs.append({
            "name": "AWS Certified Cloud Practitioner",
            "issuer": "Amazon Web Services",
            "year": 2023
        })
        
    # Languages
    langs = [{"language": "English", "proficiency": "professional"}]
    if country == "India":
        langs.append({"language": "Hindi", "proficiency": "native"})
        
    # Redrob signals
    parser = ResumeParser()
    signals = parser.build_redrob_signals()
    
    # Customize signals slightly to make them look real
    signals["profile_completeness_score"] = float(random.randint(65, 95))
    signals["recruiter_response_rate"] = round(random.uniform(0.3, 0.9), 2)
    signals["interview_completion_rate"] = round(random.uniform(0.6, 1.0), 2)
    signals["github_activity_score"] = float(random.randint(-1, 95))
    
    profile = {
        "anonymized_name": name,
        "headline": f"{title} with {yexp:.1f} years of experience",
        "summary": "AI enthusiast and software engineer specializing in scalable applications.",
        "location": city,
        "country": country,
        "years_of_experience": yexp,
        "current_title": title,
        "current_company": history[0]["company"],
        "current_company_size": comp_size,
        "current_industry": industry
    }
    
    return {
        "candidate_id": f"CAND_{cid_num:07d}",
        "profile": profile,
        "career_history": history,
        "education": education,
        "skills": skills,
        "certifications": certs,
        "languages": langs,
        "redrob_signals": signals
    }

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic candidates pool")
    parser.add_argument("--count", type=int, default=100, help="Number of profiles to generate")
    parser.add_argument("--out", type=Path, default=Path("test_candidates.jsonl"), help="Output JSONL path")
    args = parser.parse_args()
    
    print(f"Generating {args.count} candidates in {args.out}...")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    
    with open(args.out, "w", encoding="utf-8") as f:
        for i in range(1, args.count + 1):
            cand = generate_candidate(i)
            f.write(json.dumps(cand) + "\n")
            
    print("Generation complete!")

if __name__ == "__main__":
    main()
