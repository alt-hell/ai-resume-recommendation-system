import pytest
from fastapi.testclient import TestClient

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.main import app

@pytest.fixture
def client():
    # Provide a reusable test client for API endpoint integration tests
    return TestClient(app)

@pytest.fixture
def sample_pdf_bytes():
    """Minimal valid-looking PDF bytes for testing upload validation."""
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

@pytest.fixture
def sample_docx_bytes():
    """Minimal DOCX-like bytes (PK zip header) for upload validation tests."""
    return b"PK\x03\x04\x14\x00\x08\x00\x08\x00\x00\x00\x00\x00"

@pytest.fixture
def sample_resume_text():
    """Cleaned resume text fixture reused across extraction tests."""
    return (
        "John Doe\njohn@example.com\n\n"
        "SKILLS\nPython, FastAPI, MongoDB, Docker, Machine Learning\n\n"
        "EXPERIENCE\nSoftware Engineer at Acme Corp (2021-2024)\n"
        "Built REST APIs using FastAPI\n"
        "Deployed ML models to production\n\n"
        "EDUCATION\nB.Tech Computer Science, 2021"
    )
