# 🚀 AI-Powered Resume Skill Analyzer & Career Recommendation System

## 🧠 Overview

An end-to-end intelligent system that transforms unstructured resume data into actionable career insights using a hybrid NLP + Machine Learning architecture.

This project analyzes resumes, extracts skills, predicts optimal job roles, identifies skill gaps, and generates personalized learning paths — all without relying on LLMs during inference, ensuring scalability, consistency, and performance.

---

## 🎯 Key Features

* 📄 Resume Parsing (PDF/DOCX)
* 🧠 Intelligent Skill Extraction

  * Section-based parsing (primary)
  * spaCy NER (fallback)
* 🔄 Skill Normalization Engine
* 🤖 Role Prediction (XGBoost-based ML model)
* 📊 Skill Gap Analysis
* 🎯 Personalized Career Recommendations
* 📈 Skill Trend Analysis (from real job data)
* 🧭 Career Path Visualization
* 🔐 API-based architecture with FastAPI
* 🗄 MongoDB integration for persistent storage

---

## 🏗 System Architecture

```text
                🔶 TRAINING PIPELINE
Google Form (Job Data)
        ↓
LLM Skill Extraction (offline)
        ↓
Skill Cleaning & Normalization
        ↓
Role-Skill Dataset
        ↓
ML Model Training (XGBoost)
        ↓
Saved Model

================================================

                🔶 INFERENCE PIPELINE
User Resume
        ↓
Text Extraction (PDF/DOCX)
        ↓
Skill Section Detection
        ↓
Skill Extraction (Section + spaCy)
        ↓
Skill Normalization
        ↓
Feature Vectorization
        ↓
ML Model Prediction
        ↓
Skill Gap Analysis
        ↓
Recommendation Engine
        ↓
MongoDB Storage
        ↓
FastAPI Response → React Frontend
```

---

## 🧩 Tech Stack

### Backend

* Python
* FastAPI
* spaCy (NLP)
* Scikit-learn / XGBoost
* MongoDB

### Frontend

* React.js (API consumer)

### Data

* Google Forms (job dataset collection)
* Pandas / NumPy

---

## 📂 Project Structure

```
ai-resume-recommendation-system/

backend/app/
  api/                # FastAPI routes
  services/           # Core business logic
  models/             # Trained ML models
  database/           # MongoDB integration
  utils/              # Helpers
  core/               # Constants & security

data/
notebooks/
scripts/
docs/
tests/
```

---

## ⚙️ Core Modules

### 🔹 Resume Parser

Extracts structured text from PDF/DOCX resumes.

### 🔹 Skill Extractor

* Detects skill section using flexible headers
* Extracts structured skills
* Uses spaCy as fallback

### 🔹 Normalization Engine

Standardizes skills using a mapping dictionary:

```
"ml" → "machine learning"
"nlp" → "natural language processing"
```

### 🔹 ML Model

* Multi-class classification (XGBoost)
* Input: Skill vector
* Output: Job role + confidence

### 🔹 Recommendation Engine

* Role prediction
* Skill gap detection
* Learning path generation

### 🔹 Trend Analysis

* Extracts skill demand from job dataset

### 🔹 Career Path Engine

* Suggests role progression roadmap

---

## 🔌 API Endpoints

| Endpoint          | Method | Description         |
| ----------------- | ------ | ------------------- |
| `/upload`         | POST   | Upload resume       |
| `/extract-skills` | POST   | Extract skills      |
| `/recommend`      | GET    | Get recommendations |
| `/trends`         | GET    | Skill trends        |
| `/career-path`    | GET    | Career progression  |

---

## 🗄 Database Schema (MongoDB)

### Users

* name, email, phone, location

### Resumes

* extracted_skills, normalized_skills

### Recommendations

* role, confidence, skill_gap, learning_path

---

## 🧠 Machine Learning Pipeline

1. Collect job data via Google Forms
2. Extract skills (LLM-assisted offline)
3. Clean and normalize dataset
4. Convert skills → vectors
5. Train classification model
6. Save model for inference

---

## 📊 Example Output

```json
{
  "role": "Data Scientist",
  "confidence": 82,
  "skills": ["python", "sql"],
  "skill_gap": ["machine learning", "statistics"],
  "learning_path": ["statistics", "machine learning", "projects"]
}
```

---

## 🔥 Unique Selling Points

* ❌ No LLM dependency in production
* ✅ Hybrid NLP (rule-based + NER)
* ✅ Explainable recommendations
* ✅ Real-world dataset (LinkedIn job data)
* ✅ Scalable API architecture
* ✅ Modular and production-ready design

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/alt-hell/ai-resume-recommendation-system.git
cd ai-resume-recommendation-system
```

### 2. Setup backend

```bash
cd backend
pip install -r requirements.txt
```

### 3. Run FastAPI server

```bash
uvicorn app.main:app --reload
```

### 4. Open API Docs

```
http://localhost:8000/docs
```

---

## 📌 Future Improvements

* Resume scoring system
* Multi-role recommendation
* Real-time job market integration
* User progress tracking
* AI-powered resume feedback

---

## 👨‍💻 Author

**Sohail Ansari**
Data Scientist | AI/ML Engineer

---

## ⭐ Final Note

This project demonstrates the design of a scalable AI system that bridges unstructured resume data with structured career intelligence — combining NLP, ML, and system design principles into a production-ready solution.
