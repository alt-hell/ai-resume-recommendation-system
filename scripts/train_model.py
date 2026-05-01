"""
train_model.py
--------------
ML Training Pipeline for the Resume Skill Analyzer.

Phases:
  1. Generate labeled training dataset (role → skill sets)
  2. Encode skills using MultiLabelBinarizer → feature vectors
  3. Train XGBoost multi-class classifier
  4. Evaluate model with cross-validation
  5. Save model.pkl and vectorizer.pkl to backend/app/models/

Run with:
  python scripts/train_model.py

Output:
  backend/app/models/model.pkl
  backend/app/models/vectorizer.pkl
  backend/app/models/label_encoder.pkl
  backend/app/models/training_report.json
"""

import json
import logging
import os
import random
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder, MultiLabelBinarizer
from xgboost import XGBClassifier

# Make backend app importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "backend" / "app"))

from services.normalization import SKILL_CATEGORIES, get_all_canonical_skills

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

MODELS_DIR = ROOT / "backend" / "app" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH       = MODELS_DIR / "model.pkl"
VECTORIZER_PATH  = MODELS_DIR / "vectorizer.pkl"
LABEL_ENC_PATH   = MODELS_DIR / "label_encoder.pkl"
REPORT_PATH      = MODELS_DIR / "training_report.json"

# ---------------------------------------------------------------------------
# Job Role Definitions
# Each role is defined by:
#   core    — skills almost always present (high probability)
#   common  — skills frequently present (medium probability)
#   bonus   — optional skills occasionally present (low probability)
# ---------------------------------------------------------------------------

JOB_ROLES: dict[str, dict[str, list[str]]] = {

    "Backend Developer": {
        "core":   ["Python", "REST APIs", "SQL", "Git", "PostgreSQL"],
        "common": ["Django", "FastAPI", "Flask", "Docker", "Redis",
                   "MongoDB", "Linux", "CI/CD", "Microservices"],
        "bonus":  ["Go", "Java", "Spring Boot", "Kubernetes",
                   "Apache Kafka", "gRPC", "Nginx"],
    },

    "Frontend Developer": {
        "core":   ["JavaScript", "React", "Git", "HTML/CSS"],
        "common": ["TypeScript", "Node.js", "REST APIs", "Vue.js",
                   "Next.js", "Jest", "GraphQL"],
        "bonus":  ["Angular", "Webpack", "Figma", "Selenium",
                   "WebSocket", "Agile"],
    },

    "Full Stack Developer": {
        "core":   ["JavaScript", "React", "Node.js", "SQL", "Git"],
        "common": ["TypeScript", "Python", "PostgreSQL", "MongoDB",
                   "REST APIs", "Docker", "Next.js"],
        "bonus":  ["GraphQL", "Redis", "AWS", "CI/CD", "Kubernetes",
                   "Agile", "Linux"],
    },

    "Data Scientist": {
        "core":   ["Python", "Machine Learning", "Pandas", "NumPy",
                   "Scikit-learn", "SQL"],
        "common": ["Deep Learning", "TensorFlow", "PyTorch", "Tableau",
                   "Statistics", "Jupyter", "Matplotlib"],
        "bonus":  ["NLP", "Computer Vision", "XGBoost", "Apache Spark",
                   "R", "Power BI", "Keras"],
    },

    "Machine Learning Engineer": {
        "core":   ["Python", "Machine Learning", "TensorFlow", "PyTorch",
                   "Scikit-learn", "Docker"],
        "common": ["Deep Learning", "MLflow", "Kubernetes", "REST APIs",
                   "NumPy", "Pandas", "AWS"],
        "bonus":  ["XGBoost", "Hugging Face", "NLP", "Computer Vision",
                   "Apache Kafka", "Airflow", "Keras", "LangChain"],
    },

    "Data Engineer": {
        "core":   ["Python", "SQL", "Apache Spark", "Apache Kafka",
                   "Airflow"],
        "common": ["Hadoop", "AWS", "Google Cloud", "dbt", "PostgreSQL",
                   "Docker", "Linux"],
        "bonus":  ["Scala", "Kubernetes", "MongoDB", "Elasticsearch",
                   "Terraform", "Microsoft Azure"],
    },

    "DevOps Engineer": {
        "core":   ["Docker", "Kubernetes", "Linux", "CI/CD", "Git",
                   "Terraform"],
        "common": ["AWS", "Ansible", "Jenkins", "GitHub Actions",
                   "Nginx", "Python", "Bash"],
        "bonus":  ["Google Cloud", "Microsoft Azure", "Prometheus",
                   "Grafana", "GitLab CI", "Helm", "Elasticsearch"],
    },

    "Cloud Engineer": {
        "core":   ["AWS", "Terraform", "Docker", "Linux", "CI/CD"],
        "common": ["Kubernetes", "Google Cloud", "Microsoft Azure",
                   "Python", "Ansible", "Nginx"],
        "bonus":  ["Jenkins", "GitLab CI", "GitHub Actions",
                   "Elasticsearch", "Redis", "Bash"],
    },

    "Mobile Developer": {
        "core":   ["Flutter", "Dart", "Git", "REST APIs"],
        "common": ["React Native", "JavaScript", "Android Development",
                   "iOS Development", "Firebase"],
        "bonus":  ["Kotlin", "Swift", "TypeScript", "PostgreSQL",
                   "GraphQL", "CI/CD"],
    },

    "Android Developer": {
        "core":   ["Android Development", "Java", "Kotlin", "Git"],
        "common": ["REST APIs", "Firebase", "SQLite", "CI/CD"],
        "bonus":  ["Python", "Docker", "PostgreSQL", "Unit Testing",
                   "React Native"],
    },

    "iOS Developer": {
        "core":   ["iOS Development", "Swift", "Xcode", "Git"],
        "common": ["REST APIs", "Firebase", "SQLite", "Objective-C"],
        "bonus":  ["React Native", "Flutter", "CI/CD", "Unit Testing"],
    },

    "Database Administrator": {
        "core":   ["SQL", "PostgreSQL", "MySQL", "Linux", "Git"],
        "common": ["Oracle Database", "Microsoft SQL Server", "MongoDB",
                   "Redis", "Elasticsearch", "Bash"],
        "bonus":  ["Python", "Docker", "AWS", "Cassandra", "InfluxDB"],
    },

    "Security Engineer": {
        "core":   ["Linux", "Python", "Bash", "Git", "CI/CD"],
        "common": ["AWS", "Docker", "Kubernetes", "Terraform", "Nginx"],
        "bonus":  ["Go", "Rust", "Elasticsearch", "Ansible"],
    },

    "QA Engineer": {
        "core":   ["Selenium", "Unit Testing", "Git", "Pytest", "Jest"],
        "common": ["Python", "JavaScript", "REST APIs", "CI/CD", "Agile"],
        "bonus":  ["Docker", "Postman", "SQL", "Java", "TypeScript"],
    },

    "Tech Lead": {
        "core":   ["Leadership", "Agile", "Git", "Problem Solving",
                   "Communication"],
        "common": ["Python", "Java", "REST APIs", "Docker",
                   "Microservices", "CI/CD", "SQL"],
        "bonus":  ["Kubernetes", "AWS", "React", "Node.js",
                   "PostgreSQL", "Terraform"],
    },
}

# ---------------------------------------------------------------------------
# Dataset Generation
# ---------------------------------------------------------------------------

SAMPLES_PER_ROLE  = 5000   # Big Data Simulator (75k total samples)
RANDOM_SEED       = 42

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


def generate_dataset() -> pd.DataFrame:
    """
    Synthetically generate a labeled dataset of (skill_set, job_role) pairs.

    For each role, generates SAMPLES_PER_ROLE samples by:
      - Always including all core skills
      - Randomly sampling 40-80% of common skills
      - Randomly sampling 0-30% of bonus skills
      - Adding 1-3 random skills from the full registry (noise)

    This creates realistic variation that prevents the model from
    memorizing exact skill sets.
    """
    all_canonical = get_all_canonical_skills()
    records: list[dict] = []

    logger.info("Generating training dataset (%d roles × %d samples)...",
                len(JOB_ROLES), SAMPLES_PER_ROLE)

    for role, skill_config in JOB_ROLES.items():
        core   = skill_config["core"]
        common = skill_config["common"]
        bonus  = skill_config.get("bonus", [])

        # Filter to only skills that exist in our canonical registry
        core   = [s for s in core   if s in all_canonical]
        common = [s for s in common if s in all_canonical]
        bonus  = [s for s in bonus  if s in all_canonical]

        for _ in range(SAMPLES_PER_ROLE):
            skills: list[str] = []

            # Core: always included (drop 1 randomly to add noise)
            drop_core = random.randint(0, 1)
            included_core = core if drop_core == 0 else random.sample(
                core, max(len(core) - 1, 1)
            )
            skills.extend(included_core)

            # Common: include 40-80% randomly
            if common:
                n_common = random.randint(
                    max(1, int(len(common) * 0.4)),
                    int(len(common) * 0.8),
                )
                skills.extend(random.sample(common, min(n_common, len(common))))

            # Bonus: include 0-30% randomly
            if bonus:
                n_bonus = random.randint(0, max(1, int(len(bonus) * 0.3)))
                if n_bonus:
                    skills.extend(random.sample(bonus, min(n_bonus, len(bonus))))

            # Random noise: 1-5 skills from outside role definition to simulate highly imperfect raw resumes
            noise_pool = [
                s for s in all_canonical
                if s not in core and s not in common and s not in bonus
            ]
            n_noise = random.randint(1, 5)
            skills.extend(random.sample(noise_pool, min(n_noise, len(noise_pool))))

            # Deduplicate while preserving list form
            skills = list(dict.fromkeys(skills))
            records.append({"skills": skills, "role": role})

    df = pd.DataFrame(records)
    logger.info("Dataset generated: %d samples, %d roles", len(df), df["role"].nunique())
    logger.info("Samples per role:\n%s", df["role"].value_counts().to_string())
    return df


# ---------------------------------------------------------------------------
# Feature Engineering
# ---------------------------------------------------------------------------

def build_feature_matrix(
    df: pd.DataFrame,
    vectorizer: MultiLabelBinarizer | None = None,
    fit: bool = True,
) -> tuple[np.ndarray, MultiLabelBinarizer]:
    """
    Convert list-of-skills column into a binary feature matrix.

    Uses MultiLabelBinarizer — each column is one canonical skill,
    each row is a binary vector (1 = skill present, 0 = absent).

    Args:
        df:         DataFrame with a 'skills' column (list of strings).
        vectorizer: Existing fitted vectorizer (for transform-only mode).
        fit:        If True, fit a new vectorizer. If False, use provided one.

    Returns:
        (X, vectorizer) — feature matrix and fitted vectorizer.
    """
    if fit or vectorizer is None:
        vectorizer = MultiLabelBinarizer()
        X = vectorizer.fit_transform(df["skills"])
        logger.info(
            "Vectorizer fitted: %d samples × %d features",
            X.shape[0], X.shape[1]
        )
    else:
        X = vectorizer.transform(df["skills"])

    return X.astype(np.float32), vectorizer


# ---------------------------------------------------------------------------
# Model Training
# ---------------------------------------------------------------------------

def train_model(
    X: np.ndarray,
    y_encoded: np.ndarray,
    label_encoder: LabelEncoder,
) -> XGBClassifier:
    """
    Train an XGBoost multi-class classifier.

    Hyperparameters are tuned for this dataset size and feature space.
    No LLM is used here — pure gradient boosting.

    Args:
        X:             Binary feature matrix (n_samples × n_skills).
        y_encoded:     Integer-encoded label array.
        label_encoder: Fitted LabelEncoder for logging class names.

    Returns:
        Fitted XGBClassifier.
    """
    n_classes = len(label_encoder.classes_)

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        reg_alpha=0.1,
        reg_lambda=1.0,
        objective="multi:softprob",
        num_class=n_classes,
        eval_metric="mlogloss",
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )

    logger.info("Training XGBoost (%d classes, %d features, %d samples)...",
                n_classes, X.shape[1], X.shape[0])
    model.fit(X, y_encoded)
    logger.info("Training complete.")
    return model


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_model(
    model: XGBClassifier,
    X: np.ndarray,
    y_encoded: np.ndarray,
    label_encoder: LabelEncoder,
) -> dict:
    """
    Evaluate model using 5-fold stratified cross-validation.

    Returns a dict with CV scores and per-class classification report.
    """
    logger.info("Running 5-fold stratified cross-validation...")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    cv_scores = cross_val_score(model, X, y_encoded, cv=cv, scoring="accuracy")

    logger.info(
        "CV Accuracy: %.4f ± %.4f  (min=%.4f, max=%.4f)",
        cv_scores.mean(), cv_scores.std(),
        cv_scores.min(), cv_scores.max()
    )

    # Full-data classification report
    y_pred = model.predict(X)
    report = classification_report(
        y_encoded, y_pred,
        target_names=label_encoder.classes_,
        output_dict=True,
    )

    logger.info("\nPer-class report (train set):\n%s",
                classification_report(y_encoded, y_pred,
                                      target_names=label_encoder.classes_))

    return {
        "cv_accuracy_mean": round(float(cv_scores.mean()), 4),
        "cv_accuracy_std":  round(float(cv_scores.std()), 4),
        "cv_scores":        [round(float(s), 4) for s in cv_scores],
        "classification_report": report,
        "n_samples":  int(X.shape[0]),
        "n_features": int(X.shape[1]),
        "n_classes":  int(len(label_encoder.classes_)),
        "roles":      list(label_encoder.classes_),
    }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_artifacts(
    model: XGBClassifier,
    vectorizer: MultiLabelBinarizer,
    label_encoder: LabelEncoder,
    report: dict,
) -> None:
    """Save all model artifacts to MODELS_DIR."""

    joblib.dump(model,         MODEL_PATH,      compress=3)
    joblib.dump(vectorizer,    VECTORIZER_PATH,  compress=3)
    joblib.dump(label_encoder, LABEL_ENC_PATH,  compress=3)

    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    logger.info("Artifacts saved:")
    logger.info("  Model       → %s (%.1f KB)", MODEL_PATH,
                MODEL_PATH.stat().st_size / 1024)
    logger.info("  Vectorizer  → %s (%.1f KB)", VECTORIZER_PATH,
                VECTORIZER_PATH.stat().st_size / 1024)
    logger.info("  LabelEncoder→ %s", LABEL_ENC_PATH)
    logger.info("  Report      → %s", REPORT_PATH)


def load_artifacts() -> tuple[XGBClassifier, MultiLabelBinarizer, LabelEncoder]:
    """
    Load saved model artifacts for inference.
    Called by recommendation_engine.py at startup.

    Returns:
        (model, vectorizer, label_encoder)

    Raises:
        FileNotFoundError if any artifact is missing (run train_model.py first).
    """
    for path in [MODEL_PATH, VECTORIZER_PATH, LABEL_ENC_PATH]:
        if not path.exists():
            raise FileNotFoundError(
                f"Model artifact not found: {path}\n"
                "Run: python scripts/train_model.py"
            )

    model         = joblib.load(MODEL_PATH)
    vectorizer    = joblib.load(VECTORIZER_PATH)
    label_encoder = joblib.load(LABEL_ENC_PATH)

    logger.info("Loaded model artifacts from %s", MODELS_DIR)
    return model, vectorizer, label_encoder


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=" * 60)
    logger.info("RESUME ANALYZER — ML TRAINING PIPELINE")
    logger.info("=" * 60)

    # Step 1: Generate dataset
    df = generate_dataset()

    # Step 2: Encode labels
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(df["role"])
    logger.info("Label encoder: %d classes → %s",
                len(label_encoder.classes_), list(label_encoder.classes_))

    # Step 3: Build feature matrix
    X, vectorizer = build_feature_matrix(df, fit=True)

    # Step 4: Train model
    model = train_model(X, y_encoded, label_encoder)

    # Step 5: Evaluate
    report = evaluate_model(model, X, y_encoded, label_encoder)

    # Step 6: Save
    save_artifacts(model, vectorizer, label_encoder, report)

    logger.info("=" * 60)
    logger.info("TRAINING COMPLETE")
    logger.info("  CV Accuracy : %.2f%% ± %.2f%%",
                report["cv_accuracy_mean"] * 100,
                report["cv_accuracy_std"] * 100)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()