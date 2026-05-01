"""
normalization.py
----------------
Maps raw extracted skill strings to their canonical forms.

Problem this solves:
  The skill extractor returns whatever text appears in the resume.
  The same skill appears in dozens of forms across resumes:
    "js" / "javascript" / "Java Script" / "ES6" → "JavaScript"
    "node" / "nodejs" / "node.js" / "Node JS"  → "Node.js"
    "ml" / "machine learning" / "Machine-Learning" → "Machine Learning"

  Without normalization, the ML model sees hundreds of "unique" skills
  that are actually the same thing — ruining vectorization.

Responsibilities:
  - Map every alias to a single canonical skill name
  - Preserve casing of the canonical form (e.g. "PostgreSQL" not "postgresql")
  - Group canonical skills into categories for the recommendation engine
  - Detect and flag unknown skills (not in the dictionary)

Pipeline position:
  skill_extractor → [THIS FILE] → recommendation_engine
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Canonical skill registry
# ---------------------------------------------------------------------------
# Structure: "canonical name" → [list of known aliases]
# Aliases are matched case-insensitively after light normalization.
# The canonical name is the "source of truth" used in vectors and output.

SKILL_REGISTRY: dict[str, list[str]] = {

    # ── Programming Languages ───────────────────────────────────────────────
    "Python": [
        "python", "python3", "python 3", "python2", "python3.x",
        "py", "cpython", "python programming",
    ],
    "JavaScript": [
        "javascript", "java script", "js", "es6", "es2015", "es2016",
        "es2017", "es2018", "es2019", "es2020", "es2021", "es2022",
        "ecmascript", "vanilla js", "vanilla javascript",
    ],
    "TypeScript": [
        "typescript", "type script", "ts",
    ],
    "Java": [
        "java", "java8", "java 8", "java11", "java 11",
        "java17", "java 17", "core java", "advanced java",
    ],
    "C": [
        "c language", "c programming", "ansi c",
    ],
    "C++": [
        "c++", "cpp", "c plus plus", "cplusplus",
    ],
    "C#": [
        "c#", "csharp", "c sharp", "dotnet c#",
    ],
    "Go": [
        "go", "golang", "go lang", "go language",
    ],
    "Rust": [
        "rust", "rust lang", "rust language",
    ],
    "Ruby": [
        "ruby", "ruby language",
    ],
    "PHP": [
        "php", "php7", "php8", "php programming",
    ],
    "Swift": [
        "swift", "swift language", "swift programming",
    ],
    "Kotlin": [
        "kotlin", "kotlin language",
    ],
    "Scala": [
        "scala", "scala language",
    ],
    "R": [
        "r", "r language", "r programming", "r studio", "rstudio",
    ],
    "MATLAB": [
        "matlab", "mat lab",
    ],
    "Bash": [
        "bash", "bash scripting", "shell", "shell scripting",
        "shell script", "bash script", "unix shell",
    ],
    "PowerShell": [
        "powershell", "power shell", "ps1",
    ],
    "Perl": [
        "perl", "perl scripting",
    ],
    "Dart": [
        "dart", "dart language",
    ],

    # ── Web Frameworks ──────────────────────────────────────────────────────
    "Django": [
        "django", "django rest", "django rest framework", "drf",
        "django framework",
    ],
    "Flask": [
        "flask", "flask framework", "flask api",
    ],
    "FastAPI": [
        "fastapi", "fast api",
    ],
    "React": [
        "react", "reactjs", "react.js", "react js",
        "react native", "react hooks",
    ],
    "Angular": [
        "angular", "angularjs", "angular.js", "angular js",
        "angular 2", "angular2+",
    ],
    "Vue.js": [
        "vue", "vuejs", "vue.js", "vue js", "vue 3",
    ],
    "Node.js": [
        "node", "nodejs", "node.js", "node js",
        "express", "expressjs", "express.js",
    ],
    "Next.js": [
        "next", "nextjs", "next.js", "next js",
    ],
    "Nuxt.js": [
        "nuxt", "nuxtjs", "nuxt.js",
    ],
    "Spring Boot": [
        "spring boot", "spring", "spring framework",
        "spring mvc", "spring data", "spring security",
    ],
    "Laravel": [
        "laravel", "laravel framework",
    ],
    "Ruby on Rails": [
        "rails", "ruby on rails", "ror",
    ],
    "ASP.NET": [
        "asp.net", "aspnet", "asp net", ".net core", "dotnet core",
        "asp.net core", "asp.net mvc",
    ],
    "FastAPI": [
        "fastapi", "fast api",
    ],
    "HTML": [
        "html", "html5",
    ],
    "CSS": [
        "css", "css3", "tailwind", "tailwind css", "bootstrap",
    ],
    "Express.js": [
        "express", "expressjs", "express.js", "express framework",
    ],
    "Redux": [
        "redux", "redux toolkit", "rtk",
    ],
    "Webpack": [
        "webpack", "webpack module bundler",
    ],
    "Vite": [
        "vite", "vitejs",
    ],
    "MERN Stack": [
        "mern", "mern stack",
    ],
    "MEAN Stack": [
        "mean", "mean stack",
    ],

    # ── Databases ───────────────────────────────────────────────────────────
    "PostgreSQL": [
        "postgresql", "postgres", "postgre sql", "pg",
        "psql", "postgres sql",
    ],
    "MySQL": [
        "mysql", "my sql", "mysql database",
    ],
    "MongoDB": [
        "mongodb", "mongo", "mongo db",
    ],
    "Redis": [
        "redis", "redis cache", "redis db",
    ],
    "SQLite": [
        "sqlite", "sqlite3", "sql lite",
    ],
    "Microsoft SQL Server": [
        "sql server", "mssql", "ms sql", "microsoft sql server",
        "t-sql", "tsql",
    ],
    "Oracle Database": [
        "oracle", "oracle db", "oracle database", "oracle sql", "pl/sql", "plsql",
    ],
    "Cassandra": [
        "cassandra", "apache cassandra",
    ],
    "Elasticsearch": [
        "elasticsearch", "elastic search", "es", "elastic",
    ],
    "DynamoDB": [
        "dynamodb", "dynamo db", "aws dynamodb",
    ],
    "Firebase": [
        "firebase", "google firebase", "firestore",
    ],
    "Neo4j": [
        "neo4j", "neo4 j", "graph database",
    ],
    "InfluxDB": [
        "influxdb", "influx db",
    ],

    # ── Cloud Platforms ─────────────────────────────────────────────────────
    "AWS": [
        "aws", "amazon web services", "amazon aws",
        "aws cloud", "amazon cloud",
    ],
    "Google Cloud": [
        "gcp", "google cloud", "google cloud platform",
        "google cloud services",
    ],
    "Microsoft Azure": [
        "azure", "microsoft azure", "ms azure", "azure cloud",
    ],
    "Heroku": [
        "heroku", "heroku platform",
    ],
    "DigitalOcean": [
        "digitalocean", "digital ocean",
    ],

    # ── DevOps & Infrastructure ─────────────────────────────────────────────
    "Docker": [
        "docker", "docker container", "containerization",
        "docker compose", "docker-compose", "dockerfile",
    ],
    "Kubernetes": [
        "kubernetes", "k8s", "k 8s", "kube",
        "kubernetes cluster", "kubectl",
    ],
    "Terraform": [
        "terraform", "tf", "terraform iac",
    ],
    "Ansible": [
        "ansible", "ansible playbook",
    ],
    "Jenkins": [
        "jenkins", "jenkins ci", "jenkins pipeline",
    ],
    "GitHub Actions": [
        "github actions", "gh actions", "github ci",
    ],
    "GitLab CI": [
        "gitlab ci", "gitlab ci/cd", "gitlab pipelines",
    ],
    "CI/CD": [
        "ci/cd", "cicd", "ci cd", "continuous integration",
        "continuous deployment", "continuous delivery",
    ],
    "Nginx": [
        "nginx", "nginx server", "nginx proxy",
    ],
    "Apache": [
        "apache", "apache http", "apache server", "apache httpd",
    ],
    "Linux": [
        "linux", "ubuntu", "debian", "centos", "rhel",
        "red hat", "fedora", "unix", "linux administration",
    ],

    # ── Machine Learning & AI ───────────────────────────────────────────────
    "Machine Learning": [
        "machine learning", "ml", "supervised learning",
        "unsupervised learning", "ml algorithms",
    ],
    "Deep Learning": [
        "deep learning", "dl", "neural networks", "neural network",
        "ann", "dnn",
    ],
    "TensorFlow": [
        "tensorflow", "tensor flow", "tf",
    ],
    "PyTorch": [
        "pytorch", "py torch", "torch",
    ],
    "Scikit-learn": [
        "scikit-learn", "sklearn", "scikit learn",
        "scikitlearn", "scikit",
    ],
    "Keras": [
        "keras", "keras api",
    ],
    "NLP": [
        "nlp", "natural language processing",
        "text processing", "text mining",
    ],
    "Computer Vision": [
        "computer vision", "cv", "image processing",
        "object detection", "image recognition",
    ],
    "XGBoost": [
        "xgboost", "xgb", "extreme gradient boosting",
    ],
    "LangChain": [
        "langchain", "lang chain",
    ],
    "Hugging Face": [
        "hugging face", "huggingface", "transformers",
        "huggingface transformers",
    ],
    "LLMs": [
        "llm", "llms", "large language models",
    ],
    "Generative AI": [
        "generative ai", "gen ai", "genai",
    ],
    "RAG": [
        "rag", "retrieval augmented generation",
    ],
    "LlamaIndex": [
        "llamaindex", "llama index",
    ],
    "OpenAI API": [
        "openai api", "openai", "gpt-4", "chatgpt api", "chatgpt",
    ],
    "Vector Databases": [
        "vector database", "vector databases", "chromadb", "pinecone", "milvus", "qdrant",
    ],
    "Prompt Engineering": [
        "prompt engineering",
    ],
    "Fine-Tuning": [
        "fine-tuning", "fine tuning", "peft", "lora", "qlora",
    ],
    "Stable Diffusion": [
        "stable diffusion",
    ],
    "AWS Bedrock": [
        "aws bedrock", "amazon bedrock", "amazon titan",
    ],
    "MLOps": [
        "mlops", "machine learning operations", "ml ops",
    ],
    "MLflow": [
        "mlflow",
    ],
    "Weights & Biases": [
        "weights & biases", "wandb", "weights and biases",
    ],
    "Model Deployment": [
        "model deployment", "model serving", "triton", "tensorflow serving",
    ],
    "SpaCy": [
        "spacy",
    ],
    "NLTK": [
        "nltk", "natural language toolkit",
    ],
    "Time Series Analysis": [
        "time series", "time series analysis", "arima",
    ],
    "Predictive Modeling": [
        "predictive modeling", "predictive analytics",
    ],

    # ── ML Algorithms & Techniques ─────────────────────────────────────────
    "Logistic Regression": [
        "logistic regression", "logit",
    ],
    "Linear Regression": [
        "linear regression",
    ],
    "Random Forest": [
        "random forest", "random forests",
    ],
    "Decision Trees": [
        "decision tree", "decision trees",
    ],
    "KNN": [
        "knn", "k-nearest neighbors", "k nearest neighbors",
        "k-nn", "k nearest neighbour",
    ],
    "SVM": [
        "svm", "support vector machine", "support vector machines",
    ],
    "Naive Bayes": [
        "naive bayes", "naivebayes",
    ],
    "Gradient Boosting": [
        "gradient boosting", "gbm", "gradient boosted tree",
    ],
    "CatBoost": [
        "catboost",
    ],
    "LightGBM": [
        "lightgbm", "light gbm",
    ],
    "SVD": [
        "svd", "singular value decomposition",
    ],
    "Recommendation Systems": [
        "recommendation system", "recommendation systems",
        "recommender system", "recommender systems",
        "recommendation engine", "collaborative filtering",
        "content based filtering",
    ],
    "Ensemble Methods": [
        "ensemble methods", "ensemble learning", "bagging", "boosting", "stacking",
    ],
    "Feature Engineering": [
        "feature engineering", "feature selection", "feature extraction",
    ],
    "Hyperparameter Tuning": [
        "hyperparameter tuning", "hyperparameter optimization",
        "grid search", "random search", "bayesian optimization",
    ],
    "Model Evaluation": [
        "model evaluation", "cross validation", "cross-validation",
        "confusion matrix", "roc curve", "precision recall",
    ],
    "Dimensionality Reduction": [
        "dimensionality reduction", "pca", "principal component analysis",
        "t-sne", "tsne", "umap",
    ],
    "Clustering": [
        "clustering", "k-means", "kmeans", "dbscan",
        "hierarchical clustering",
    ],
    "Anomaly Detection": [
        "anomaly detection", "outlier detection", "fraud detection",
    ],

    # ── Deep Learning Architectures ────────────────────────────────────────
    "RNN": [
        "rnn", "recurrent neural network", "recurrent neural networks",
    ],
    "LSTM": [
        "lstm", "long short-term memory", "long short term memory",
    ],
    "GRU": [
        "gru", "gated recurrent unit", "gated recurrent units",
    ],
    "CNN": [
        "cnn", "convolutional neural network", "convolutional neural networks",
        "convnet",
    ],
    "Transformers": [
        "transformer", "transformers", "attention mechanism",
        "self-attention", "multi-head attention",
    ],
    "BERT": [
        "bert", "bidirectional encoder representations",
    ],
    "GPT": [
        "gpt", "gpt-3", "gpt-4", "gpt3", "gpt4",
    ],
    "GANs": [
        "gan", "gans", "generative adversarial network",
        "generative adversarial networks",
    ],
    "Autoencoders": [
        "autoencoder", "autoencoders", "variational autoencoder", "vae",
    ],

    # ── Data Analysis & Statistics ─────────────────────────────────────────
    "Data Analysis": [
        "data analysis", "data analytics", "data handling",
        "data interpretation",
    ],
    "Data Visualization": [
        "data visualization", "data visualisation",
    ],
    "Data Wrangling": [
        "data wrangling", "data cleaning", "data preprocessing",
        "data munging",
    ],
    "EDA": [
        "eda", "exploratory data analysis",
    ],
    "Statistical Analysis": [
        "statistical analysis", "correlation analysis",
        "trend analysis", "regression analysis",
    ],
    "Advanced Excel": [
        "advanced excel", "advance excel", "adavance excel",
        "excel formulas", "pivot tables", "vlookup",
    ],
    "Web Scraping": [
        "web scraping", "beautiful soup", "beautifulsoup",
        "scrapy", "web crawling",
    ],
    "Streamlit": [
        "streamlit",
    ],
    "Jupyter": [
        "jupyter", "jupyter notebook", "jupyter lab",
        "google colab",
    ],

    # ── Data Engineering & Analytics ────────────────────────────────────────
    "Pandas": [
        "pandas", "pandas library", "pd",
    ],
    "NumPy": [
        "numpy", "num py", "np",
    ],
    "Apache Spark": [
        "spark", "apache spark", "pyspark", "py spark", "spark sql",
    ],
    "Hadoop": [
        "hadoop", "apache hadoop", "hdfs", "mapreduce", "map reduce",
    ],
    "Apache Kafka": [
        "kafka", "apache kafka",
    ],
    "Airflow": [
        "airflow", "apache airflow",
    ],
    "dbt": [
        "dbt", "data build tool",
    ],
    "Fivetran": [
        "fivetran",
    ],
    "Snowflake": [
        "snowflake",
    ],
    "BigQuery": [
        "bigquery", "google bigquery",
    ],
    "Tableau": [
        "tableau", "tableau desktop", "tableau server",
    ],
    "Power BI": [
        "power bi", "powerbi", "microsoft power bi",
    ],
    "Excel": [
        "excel", "ms excel", "microsoft excel",
    ],
    "VBA": [
        "vba", "excel vba", "macro", "macros",
    ],
    "SQL": [
        "sql", "structured query language", "ansi sql",
        "advanced sql", "complex sql", "sql queries",
    ],
    "Looker": [
        "looker",
    ],
    "Qlik": [
        "qlik", "qlikview", "qliksense",
    ],
    "Google Analytics": [
        "google analytics", "ga4",
    ],
    "A/B Testing": [
        "a/b testing", "ab testing", "split testing",
    ],
    "Statistics": [
        "statistics", "statistical analysis", "hypothesis testing",
    ],
    "Optimization": [
        "optimization", "optimisation", "mathematical optimization", "operations research",
    ],
    "SciPy": [
        "scipy",
    ],
    "Business Intelligence": [
        "business intelligence", "bi",
    ],
    "Business Analysis": [
        "business analysis", "business decision analysis", "decision analysis",
    ],
    "Financial Risk Management": [
        "financial risk management", "risk management", "frm",
    ],
    "Hive": [
        "hive", "apache hive",
    ],
    "Presto": [
        "presto", "prestodb", "trino",
    ],
    "Databricks": [
        "databricks",
    ],
    "ETL": [
        "etl", "extract transform load",
    ],
    "Data Warehousing": [
        "data warehousing", "data warehouse", "dwh",
    ],
    "Data Modeling": [
        "data modeling", "data architecture",
    ],
    "Flink": [
        "flink", "apache flink",
    ],
    "Matplotlib": [
        "matplotlib",
    ],
    "Seaborn": [
        "seaborn",
    ],
    "Plotly": [
        "plotly",
    ],

    # ── Version Control ─────────────────────────────────────────────────────
    "Git": [
        "git", "git version control", "git scm",
    ],
    "GitHub": [
        "github", "git hub",
    ],
    "GitLab": [
        "gitlab", "git lab",
    ],
    "Bitbucket": [
        "bitbucket", "bit bucket",
    ],

    # ── Mobile Development ──────────────────────────────────────────────────
    "Flutter": [
        "flutter", "flutter framework", "flutter sdk",
    ],
    "React Native": [
        "react native", "rn", "reactnative",
    ],
    "Android Development": [
        "android", "android development", "android sdk",
        "android studio",
    ],
    "iOS Development": [
        "ios", "ios development", "xcode",
    ],

    # ── APIs & Protocols ────────────────────────────────────────────────────
    "REST APIs": [
        "rest", "rest api", "restful", "restful api",
        "rest apis", "rest web services", "http api",
    ],
    "GraphQL": [
        "graphql", "graph ql",
    ],
    "gRPC": [
        "grpc", "g rpc", "grpc api",
    ],
    "WebSocket": [
        "websocket", "web socket", "websockets",
    ],
    "Microservices": [
        "microservices", "micro services", "microservice architecture",
        "microservice", "service-oriented architecture", "soa",
    ],
    "JWT": [
        "jwt", "json web token", "json web tokens",
    ],
    "API Integration": [
        "api integration", "api integration & development", "api development", "api implementation",
    ],

    # ── Testing ─────────────────────────────────────────────────────────────
    "Pytest": [
        "pytest", "py test",
    ],
    "Jest": [
        "jest", "jest testing",
    ],
    "Selenium": [
        "selenium", "selenium webdriver", "selenium testing",
    ],
    "Unit Testing": [
        "unit testing", "unit tests", "unit test",
        "tdd", "test driven development",
    ],

    # ── Soft Skills ─────────────────────────────────────────────────────────
    "Agile": [
        "agile", "agile methodology", "agile development",
        "scrum", "kanban", "sprint planning",
    ],
    "Communication": [
        "communication", "verbal communication", "written communication",
        "presentation skills",
    ],
    "Leadership": [
        "leadership", "team leadership", "people management",
        "team management",
    ],
    "Problem Solving": [
        "problem solving", "problem-solving", "analytical thinking",
        "analytical skills", "critical thinking",
    ],
    "Responsive Design": [
        "responsive design", "responsive web design", "rwd",
    ],
    "Postman": [
        "postman",
    ],
    "Vercel": [
        "vercel", "vercel deployment",
    ],
    
    # ── Design & UI/UX ──────────────────────────────────────────────────────
    "Figma": ["figma", "figma design"],
    "Sketch": ["sketch", "sketch app"],
    "Adobe XD": ["adobe xd", "xd"],
    "Adobe Photoshop": ["photoshop", "adobe photoshop", "ps"],
    "Adobe Illustrator": ["illustrator", "adobe illustrator", "ai"],
    "UI/UX Design": ["ui/ux", "user interface", "user experience", "ui design", "ux design"],
    "Wireframing": ["wireframes", "wireframing", "prototyping"],

    # ── Marketing & SEO ─────────────────────────────────────────────────────
    "SEO": ["seo", "search engine optimization", "search engine optimisation"],
    "SEM": ["sem", "search engine marketing"],
    "Content Marketing": ["content marketing", "content creation", "copywriting"],
    "Email Marketing": ["email marketing", "mailchimp", "sendgrid"],
    "Google Ads": ["google ads", "adwords"],
    "HubSpot": ["hubspot", "hub spot"],

    # ── Sales & CRM ─────────────────────────────────────────────────────────
    "Salesforce": ["salesforce", "sales force", "sfdc"],
    "B2B Sales": ["b2b", "b2b sales", "business to business"],
    "CRM": ["crm", "customer relationship management"],
    "Account Management": ["account management", "key account management"],

    # ── Cybersecurity ───────────────────────────────────────────────────────
    "Penetration Testing": ["penetration testing", "pen testing", "ethical hacking"],
    "Network Security": ["network security", "firewalls", "vpn"],
    "Cryptography": ["cryptography", "encryption", "pki"],
    "IAM": ["iam", "identity and access management", "active directory", "okta"],
    "Vulnerability Assessment": ["vulnerability assessment", "vulnerability scanning"],

    # ── Finance & Accounting ────────────────────────────────────────────────
    "Financial Modeling": ["financial modeling", "financial modelling"],
    "Accounting": ["accounting", "bookkeeping", "general ledger"],
    "QuickBooks": ["quickbooks", "quick books"],
    "SAP": ["sap", "sap erp", "sap hana"],
    "Financial Analysis": ["financial analysis", "corporate finance"],

    # ── Game Development ────────────────────────────────────────────────────
    "Unity": ["unity", "unity 3d", "unity3d"],
    "Unreal Engine": ["unreal", "unreal engine", "ue4", "ue5"],
    "Godot": ["godot", "godot engine"],

    # ── Extended Data / DevOps ──────────────────────────────────────────────
    "Alteryx": ["alteryx"],
    "Talend": ["talend"],
    "Looker Studio": ["looker studio", "google data studio", "data studio"],
}


# ---------------------------------------------------------------------------
# Category mapping
# Maps each canonical skill to a high-level category.
# Used by the recommendation engine for skill gap analysis.
# ---------------------------------------------------------------------------

SKILL_CATEGORIES: dict[str, str] = {
    # Languages
    "Python": "Programming Languages",
    "JavaScript": "Programming Languages",
    "TypeScript": "Programming Languages",
    "Java": "Programming Languages",
    "C": "Programming Languages",
    "C++": "Programming Languages",
    "C#": "Programming Languages",
    "Go": "Programming Languages",
    "Rust": "Programming Languages",
    "Ruby": "Programming Languages",
    "PHP": "Programming Languages",
    "Swift": "Programming Languages",
    "Kotlin": "Programming Languages",
    "Scala": "Programming Languages",
    "R": "Programming Languages",
    "MATLAB": "Programming Languages",
    "Bash": "Programming Languages",
    "PowerShell": "Programming Languages",
    "Perl": "Programming Languages",
    "Dart": "Programming Languages",
    # Web Frameworks
    "Django": "Web Frameworks",
    "Flask": "Web Frameworks",
    "FastAPI": "Web Frameworks",
    "React": "Web Frameworks",
    "Angular": "Web Frameworks",
    "Vue.js": "Web Frameworks",
    "Node.js": "Web Frameworks",
    "Next.js": "Web Frameworks",
    "Nuxt.js": "Web Frameworks",
    "Spring Boot": "Web Frameworks",
    "Laravel": "Web Frameworks",
    "Ruby on Rails": "Web Frameworks",
    "ASP.NET": "Web Frameworks",
    "HTML": "Web Frameworks",
    "CSS": "Web Frameworks",
    "Express.js": "Web Frameworks",
    "Redux": "Web Frameworks",
    "Webpack": "Web Frameworks",
    "Vite": "Web Frameworks",
    "MERN Stack": "Web Frameworks",
    "MEAN Stack": "Web Frameworks",
    # Databases
    "PostgreSQL": "Databases",
    "MySQL": "Databases",
    "MongoDB": "Databases",
    "Redis": "Databases",
    "SQLite": "Databases",
    "Microsoft SQL Server": "Databases",
    "Oracle Database": "Databases",
    "Cassandra": "Databases",
    "Elasticsearch": "Databases",
    "DynamoDB": "Databases",
    "Firebase": "Databases",
    "Neo4j": "Databases",
    "InfluxDB": "Databases",
    "SQL": "Databases",
    # Cloud
    "AWS": "Cloud Platforms",
    "Google Cloud": "Cloud Platforms",
    "Microsoft Azure": "Cloud Platforms",
    "Heroku": "Cloud Platforms",
    "DigitalOcean": "Cloud Platforms",
    # DevOps
    "Docker": "DevOps",
    "Kubernetes": "DevOps",
    "Terraform": "DevOps",
    "Ansible": "DevOps",
    "Jenkins": "DevOps",
    "GitHub Actions": "DevOps",
    "GitLab CI": "DevOps",
    "CI/CD": "DevOps",
    "Nginx": "DevOps",
    "Apache": "DevOps",
    "Linux": "DevOps",
    # ML / AI
    "Machine Learning": "Machine Learning & AI",
    "Deep Learning": "Machine Learning & AI",
    "TensorFlow": "Machine Learning & AI",
    "PyTorch": "Machine Learning & AI",
    "Scikit-learn": "Machine Learning & AI",
    "Keras": "Machine Learning & AI",
    "NLP": "Machine Learning & AI",
    "Computer Vision": "Machine Learning & AI",
    "XGBoost": "Machine Learning & AI",
    "LangChain": "Machine Learning & AI",
    "Hugging Face": "Machine Learning & AI",
    "LLMs": "Machine Learning & AI",
    "Generative AI": "Machine Learning & AI",
    "RAG": "Machine Learning & AI",
    "LlamaIndex": "Machine Learning & AI",
    "OpenAI API": "Machine Learning & AI",
    "Vector Databases": "Machine Learning & AI",
    "Prompt Engineering": "Machine Learning & AI",
    "Fine-Tuning": "Machine Learning & AI",
    "Stable Diffusion": "Machine Learning & AI",
    "AWS Bedrock": "Machine Learning & AI",
    "MLOps": "Machine Learning & AI",
    "MLflow": "Machine Learning & AI",
    "Weights & Biases": "Machine Learning & AI",
    "Model Deployment": "Machine Learning & AI",
    "SpaCy": "Machine Learning & AI",
    "NLTK": "Machine Learning & AI",
    "Time Series Analysis": "Machine Learning & AI",
    "Predictive Modeling": "Machine Learning & AI",
    # ML Algorithms
    "Logistic Regression": "Machine Learning & AI",
    "Linear Regression": "Machine Learning & AI",
    "Random Forest": "Machine Learning & AI",
    "Decision Trees": "Machine Learning & AI",
    "KNN": "Machine Learning & AI",
    "SVM": "Machine Learning & AI",
    "Naive Bayes": "Machine Learning & AI",
    "Gradient Boosting": "Machine Learning & AI",
    "CatBoost": "Machine Learning & AI",
    "LightGBM": "Machine Learning & AI",
    "SVD": "Machine Learning & AI",
    "Recommendation Systems": "Machine Learning & AI",
    "Ensemble Methods": "Machine Learning & AI",
    "Feature Engineering": "Machine Learning & AI",
    "Hyperparameter Tuning": "Machine Learning & AI",
    "Model Evaluation": "Machine Learning & AI",
    "Dimensionality Reduction": "Machine Learning & AI",
    "Clustering": "Machine Learning & AI",
    "Anomaly Detection": "Machine Learning & AI",
    # DL Architectures
    "RNN": "Machine Learning & AI",
    "LSTM": "Machine Learning & AI",
    "GRU": "Machine Learning & AI",
    "CNN": "Machine Learning & AI",
    "Transformers": "Machine Learning & AI",
    "BERT": "Machine Learning & AI",
    "GPT": "Machine Learning & AI",
    "GANs": "Machine Learning & AI",
    "Autoencoders": "Machine Learning & AI",
    # Data Analysis
    "Data Analysis": "Data Engineering & Analytics",
    "Data Visualization": "Data Engineering & Analytics",
    "Data Wrangling": "Data Engineering & Analytics",
    "EDA": "Data Engineering & Analytics",
    "Statistical Analysis": "Data Engineering & Analytics",
    "Advanced Excel": "Data Engineering & Analytics",
    "Web Scraping": "Data Engineering & Analytics",
    "Streamlit": "Data Engineering & Analytics",
    "Jupyter": "Data Engineering & Analytics",
    # Data
    "Pandas": "Data Engineering & Analytics",
    "NumPy": "Data Engineering & Analytics",
    "Apache Spark": "Data Engineering & Analytics",
    "Hadoop": "Data Engineering & Analytics",
    "Apache Kafka": "Data Engineering & Analytics",
    "Airflow": "Data Engineering & Analytics",
    "dbt": "Data Engineering & Analytics",
    "Fivetran": "Data Engineering & Analytics",
    "Snowflake": "Data Engineering & Analytics",
    "BigQuery": "Data Engineering & Analytics",
    "Tableau": "Data Engineering & Analytics",
    "Power BI": "Data Engineering & Analytics",
    "Excel": "Data Engineering & Analytics",
    "VBA": "Data Engineering & Analytics",
    "Looker": "Data Engineering & Analytics",
    "Qlik": "Data Engineering & Analytics",
    "Google Analytics": "Data Engineering & Analytics",
    "A/B Testing": "Data Engineering & Analytics",
    "Statistics": "Data Engineering & Analytics",
    "Optimization": "Data Engineering & Analytics",
    "SciPy": "Data Engineering & Analytics",
    "Business Intelligence": "Data Engineering & Analytics",
    "Business Analysis": "Data Engineering & Analytics",
    "Financial Risk Management": "Data Engineering & Analytics",
    "Hive": "Data Engineering & Analytics",
    "Presto": "Data Engineering & Analytics",
    "Databricks": "Data Engineering & Analytics",
    "ETL": "Data Engineering & Analytics",
    "Data Warehousing": "Data Engineering & Analytics",
    "Data Modeling": "Data Engineering & Analytics",
    "Flink": "Data Engineering & Analytics",
    "Matplotlib": "Data Engineering & Analytics",
    "Seaborn": "Data Engineering & Analytics",
    "Plotly": "Data Engineering & Analytics",
    # Version Control
    "Git": "Version Control",
    "GitHub": "Version Control",
    "GitLab": "Version Control",
    "Bitbucket": "Version Control",
    # Mobile
    "Flutter": "Mobile Development",
    "React Native": "Mobile Development",
    "Android Development": "Mobile Development",
    "iOS Development": "Mobile Development",
    # APIs
    "REST APIs": "APIs & Architecture",
    "GraphQL": "APIs & Architecture",
    "gRPC": "APIs & Architecture",
    "WebSocket": "APIs & Architecture",
    "Microservices": "APIs & Architecture",
    # Testing
    "Pytest": "Testing",
    "Jest": "Testing",
    "Selenium": "Testing",
    "Unit Testing": "Testing",
    # Soft Skills
    "Agile": "Soft Skills",
    "Communication": "Soft Skills",
    "Leadership": "Soft Skills",
    "Problem Solving": "Soft Skills",
    "Responsive Design": "Web Frameworks",
    "Postman": "Testing",
    "Vercel": "Cloud Platforms",
    "JWT": "APIs & Architecture",
    "API Integration": "APIs & Architecture",
    
    # Design & UI/UX
    "Figma": "Design & UI/UX",
    "Sketch": "Design & UI/UX",
    "Adobe XD": "Design & UI/UX",
    "Adobe Photoshop": "Design & UI/UX",
    "Adobe Illustrator": "Design & UI/UX",
    "UI/UX Design": "Design & UI/UX",
    "Wireframing": "Design & UI/UX",

    # Marketing & SEO
    "SEO": "Marketing & SEO",
    "SEM": "Marketing & SEO",
    "Content Marketing": "Marketing & SEO",
    "Email Marketing": "Marketing & SEO",
    "Google Ads": "Marketing & SEO",
    "HubSpot": "Marketing & SEO",

    # Sales & CRM
    "Salesforce": "Sales & CRM",
    "B2B Sales": "Sales & CRM",
    "CRM": "Sales & CRM",
    "Account Management": "Sales & CRM",

    # Cybersecurity
    "Penetration Testing": "Cybersecurity",
    "Network Security": "Cybersecurity",
    "Cryptography": "Cybersecurity",
    "IAM": "Cybersecurity",
    "Vulnerability Assessment": "Cybersecurity",

    # Finance & Accounting
    "Financial Modeling": "Finance & Accounting",
    "Accounting": "Finance & Accounting",
    "QuickBooks": "Finance & Accounting",
    "SAP": "Finance & Accounting",
    "Financial Analysis": "Finance & Accounting",

    # Game Development
    "Unity": "Game Development",
    "Unreal Engine": "Game Development",
    "Godot": "Game Development",

    # Extended Data
    "Alteryx": "Data Engineering & Analytics",
    "Talend": "Data Engineering & Analytics",
    "Looker Studio": "Data Engineering & Analytics",
}


# ---------------------------------------------------------------------------
# Internal helpers  (must be defined before _build_alias_map uses them)
# ---------------------------------------------------------------------------

def _normalize_for_lookup(text: str) -> str:
    """
    Normalize a skill string for alias dictionary lookup.

    Steps:
      1. Lowercase
      2. Strip surrounding whitespace and punctuation
      3. Collapse internal whitespace
      4. Collapse hyphen/dot between words so "node.js" → "node js"
         which then matches the alias "node js" in the registry.
    """
    text = text.lower().strip()
    text = text.strip(".,;:•●()[]{}\"'")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[-.]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# Build reverse lookup: alias → canonical  (computed once at import time)
# ---------------------------------------------------------------------------

def _build_alias_map(registry: dict[str, list[str]]) -> dict[str, str]:
    """
    Build a flat alias → canonical lookup from the registry.

    Keys are normalized aliases (lowercase, stripped, punctuation-reduced).
    Values are the canonical skill names (original casing preserved).
    """
    alias_map: dict[str, str] = {}
    for canonical, aliases in registry.items():
        # The canonical name maps to itself
        alias_map[_normalize_for_lookup(canonical)] = canonical
        for alias in aliases:
            key = _normalize_for_lookup(alias)
            if key in alias_map and alias_map[key] != canonical:
                logger.debug(
                    "Alias conflict: '%s' → '%s' (already mapped to '%s')",
                    alias, canonical, alias_map[key]
                )
            alias_map[key] = canonical
    return alias_map


# Module-level reverse lookup (built once, reused on every call)
_ALIAS_MAP: dict[str, str] = _build_alias_map(SKILL_REGISTRY)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class NormalizationResult:
    """
    Result of normalizing a list of raw skills.

    Attributes:
        normalized:   List of canonical skill names (known skills only).
        unknown:      Raw skill strings that had no match in the registry.
        mapping:      Dict mapping each input raw skill → canonical form or None.
        categories:   Dict mapping each canonical skill → its category.
    """
    normalized: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    mapping: dict[str, Optional[str]] = field(default_factory=dict)
    categories: dict[str, str] = field(default_factory=dict)

    @property
    def known_count(self) -> int:
        return len(self.normalized)

    @property
    def unknown_count(self) -> int:
        return len(self.unknown)

    @property
    def match_rate(self) -> float:
        total = self.known_count + self.unknown_count
        return self.known_count / total if total > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "normalized": self.normalized,
            "unknown": self.unknown,
            "mapping": self.mapping,
            "categories": self.categories,
            "known_count": self.known_count,
            "unknown_count": self.unknown_count,
            "match_rate": round(self.match_rate, 3),
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_skills(raw_skills: list[str]) -> NormalizationResult:
    """
    Normalize a list of raw extracted skill strings to canonical forms.

    Args:
        raw_skills: Output of skill_extractor.extract_skills().skills

    Returns:
        NormalizationResult with canonical skills and metadata.

    Example:
        >>> normalize_skills(["js", "nodejs", "mongo", "REST"])
        normalized = ["JavaScript", "Node.js", "MongoDB", "REST APIs"]
    """
    normalized: list[str] = []
    unknown: list[str] = []
    mapping: dict[str, Optional[str]] = {}
    categories: dict[str, str] = {}
    seen_canonical: set[str] = set()
    seen_unknown: set[str] = set()

    for raw in raw_skills:
        if not raw or not raw.strip():
            continue

        canonical = lookup_canonical(raw)

        if canonical is not None:
            mapping[raw] = canonical
            if canonical not in seen_canonical:
                seen_canonical.add(canonical)
                normalized.append(canonical)
                category = SKILL_CATEGORIES.get(canonical, "Other")
                categories[canonical] = category
        else:
            mapping[raw] = None
            # Only add to unknown if it looks like a real skill (not garbage)
            if _is_valid_unknown_skill(raw) and raw.lower() not in seen_unknown:
                seen_unknown.add(raw.lower())
                unknown.append(raw)
                logger.debug("Unknown skill (not in registry): '%s'", raw)

    logger.info(
        "Normalized %d/%d skills (%.0f%% match rate)",
        len(normalized),
        max(len(raw_skills), 1),
        (len(normalized) / max(len(raw_skills), 1)) * 100,
    )

    return NormalizationResult(
        normalized=normalized,
        unknown=unknown,
        mapping=mapping,
        categories=categories,
    )


def _is_valid_unknown_skill(raw: str) -> bool:
    """
    Filter garbage from the unknown skills list.
    Returns True only if the raw string looks like a plausible skill.
    """
    text = raw.strip()
    lower = text.lower()

    # Too short or too long
    if len(text) < 2 or len(text) > 40:
        return False

    # Pure numbers
    if text.replace(".", "").replace(",", "").isdigit():
        return False

    # Email
    if re.match(r'^[\w.+-]+@[\w-]+\.\w+$', lower):
        return False

    # URL
    if re.match(r'^(https?://|www\.)', lower):
        return False

    # Phone number
    if re.match(r'^[\d\s\-+().]{7,}$', lower):
        return False

    # Date patterns
    if re.match(r'^\d{4}([-–]\d{4})?$', lower):
        return False
    if re.match(r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', lower):
        return False

    # Contains @
    if "@" in text:
        return False

    # Starts with digit and has spaces (likely date/ID)
    if text[0].isdigit() and " " in text:
        return False

    # Location pattern "City, Country"
    if re.match(r'^[A-Z][a-z]+,\s*[A-Z]', text):
        return False

    # Too many words — sentence fragment
    if len(text.split()) > 4:
        return False

    # Common resume garbage words
    garbage_words = {
        "name", "email", "phone", "address", "linkedin", "github",
        "india", "usa", "uk", "remote", "onsite", "hybrid",
        "bachelor", "master", "degree", "cgpa", "gpa", "percentage",
        "mr", "mrs", "ms", "dr", "university", "college", "school",
        "intern", "internship", "full time", "part time", "contract",
        "present", "current", "result", "grade", "score",
    }
    if lower in garbage_words:
        return False

    # Single character
    if len(text) == 1:
        return False

    return True


def lookup_canonical(raw_skill: str) -> Optional[str]:
    """
    Look up the canonical form for a single raw skill string.

    Returns the canonical name if found, None if unknown.

    Matching strategies (in order):
      1. Exact match after normalization
      2. Strip all non-alpha characters and retry
      3. Extract parenthetical abbreviation (e.g. "NLP" from "Natural Language Processing (NLP)")
      4. Try the text before parentheses
      5. Remove trailing version numbers (e.g. "React 18" → "React")
      6. Substring matching: check if any known alias is contained in the skill

    Args:
        raw_skill: A raw skill string, e.g. "js", "nodejs", "python3"

    Returns:
        Canonical name e.g. "JavaScript", "Node.js", "Python", or None.
    """
    key = _normalize_for_lookup(raw_skill)

    # Strategy 1: Exact match
    if key in _ALIAS_MAP:
        return _ALIAS_MAP[key]

    # Strategy 2: Strip all non-alpha characters and retry
    stripped = re.sub(r"[^a-z\s]", "", key).strip()
    if stripped and stripped in _ALIAS_MAP:
        return _ALIAS_MAP[stripped]

    # Strategy 3: Extract parenthetical abbreviation
    # "Natural Language Processing (NLP)" → try "nlp"
    paren_match = re.match(r"^(.+?)\s*\(([^)]+)\)\s*$", raw_skill)
    if paren_match:
        abbrev = _normalize_for_lookup(paren_match.group(2))
        if abbrev in _ALIAS_MAP:
            return _ALIAS_MAP[abbrev]
        # Also try the main text before parentheses
        main_text = _normalize_for_lookup(paren_match.group(1))
        if main_text in _ALIAS_MAP:
            return _ALIAS_MAP[main_text]
        # Try the full string with parentheses included
        full_with_paren = _normalize_for_lookup(raw_skill)
        if full_with_paren in _ALIAS_MAP:
            return _ALIAS_MAP[full_with_paren]

    # Strategy 4: Remove trailing version numbers
    # "React 18" → "react", "Python3.11" → "python"
    no_version = re.sub(r"\s*\d+(\.\d+)*\s*$", "", key).strip()
    if no_version and no_version != key and no_version in _ALIAS_MAP:
        return _ALIAS_MAP[no_version]

    return None


def get_skill_category(canonical_skill: str) -> str:
    """
    Return the category for a canonical skill name.

    Args:
        canonical_skill: A canonical skill name from the registry.

    Returns:
        Category string, e.g. "Programming Languages", or "Other".
    """
    return SKILL_CATEGORIES.get(canonical_skill, "Other")


def get_all_canonical_skills() -> list[str]:
    """Return all canonical skill names from the registry."""
    return list(SKILL_REGISTRY.keys())


def get_skills_by_category(category: str) -> list[str]:
    """
    Return all canonical skills belonging to a given category.

    Args:
        category: e.g. "Programming Languages", "Machine Learning & AI"

    Returns:
        List of canonical skill names in that category.
    """
    return [
        skill for skill, cat in SKILL_CATEGORIES.items()
        if cat.lower() == category.lower()
    ]


def get_all_categories() -> list[str]:
    """Return all unique skill categories."""
    return sorted(set(SKILL_CATEGORIES.values()))


def add_custom_skill(canonical: str, aliases: list[str], category: str = "Other") -> None:
    """
    Register a new skill at runtime (e.g. from admin configuration).

    Useful for adding niche or domain-specific skills without editing
    the source file.

    Args:
        canonical: The canonical name to register, e.g. "LangGraph"
        aliases:   List of alias strings for this skill.
        category:  Category to assign. Defaults to "Other".
    """
    SKILL_REGISTRY[canonical] = aliases
    SKILL_CATEGORIES[canonical] = category

    # Update the alias map with new entries
    _ALIAS_MAP[_normalize_for_lookup(canonical)] = canonical
    for alias in aliases:
        _ALIAS_MAP[_normalize_for_lookup(alias)] = canonical

    logger.info("Registered custom skill: '%s' (%s)", canonical, category)