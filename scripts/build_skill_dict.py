import csv
import json
import sys
from pathlib import Path

# Add backend to sys.path so we can import constants
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.constants import JOB_ROLES

RAW_CSV = REPO_ROOT / "data" / "raw" / "job_postings_dataset.csv"
PROCESSED_DATA_DIR = REPO_ROOT / "data" / "processed"
OUTPUT_JSON = PROCESSED_DATA_DIR / "job_skills.json"

def map_title_to_role(title: str) -> str:
    title_lower = title.lower()
    
    # Direct mappings or strong inclusions
    if "data scientist" in title_lower or "science internship" in title_lower or "data science" in title_lower:
        return "Data Scientist"
    if "data analyst" in title_lower or "analyst" in title_lower:
        return "Data Analyst"
    if "machine learning" in title_lower or "ml" in title_lower or "nlp" in title_lower or "deep learning" in title_lower or "computer vision" in title_lower or "ai" in title_lower or "generative ai" in title_lower or "robotics" in title_lower or "reinforcement learning" in title_lower:
        return "Machine Learning Engineer"
    if "data engineer" in title_lower or "data platform" in title_lower:
        return "Data Engineer"
    if "full stack" in title_lower:
        return "Full Stack Developer"
    if "backend" in title_lower or "back end" in title_lower:
        return "Backend Developer"
    if "frontend" in title_lower or "front end" in title_lower:
        return "Frontend Developer"
    if "devops" in title_lower or "site reliability" in title_lower or "mlops" in title_lower:
        return "DevOps Engineer"
    if "cloud" in title_lower:
        return "Cloud Engineer"
    if "security" in title_lower or "cybersecurity" in title_lower:
        return "Cybersecurity Analyst"
    if "database" in title_lower or "dba" in title_lower:
        return "Database Administrator"
    if "qa" in title_lower or "test" in title_lower or "quality" in title_lower:
        return "QA Engineer"
    if "android" in title_lower:
        return "Android Developer"
    if "ios" in title_lower:
        return "iOS Developer"
        
    return "Machine Learning Engineer"  # fallback

def main():
    if not RAW_CSV.exists():
        print(f"Error: {RAW_CSV} not found.")
        sys.exit(1)

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    processed_samples = []
    
    with open(RAW_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("title", "")
            if not title:
                continue
                
            mapped_role = map_title_to_role(title)
            
            # Combine required and preferred skills
            required = row.get("skills_required", "")
            preferred = row.get("skills_preferred", "")
            
            skills_str = f"{required},{preferred}"
            skills = [s.strip() for s in skills_str.split(",") if s.strip()]
            
            if skills:
                processed_samples.append({
                    "role": mapped_role,
                    "title_raw": title,
                    "skills": list(set(skills))
                })

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(processed_samples, f, indent=2)
        
    print(f"Successfully processed {len(processed_samples)} job postings.")
    print(f"Saved to {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
