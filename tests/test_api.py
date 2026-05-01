"""
test_api.py
-----------
Integration tests for FastAPI endpoints (Phase 7).
Run with: pytest tests/test_api.py -v
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


# ---------------------------------------------------------------------------
# /upload endpoint tests
# ---------------------------------------------------------------------------

class TestUploadEndpoint:
    def test_upload_unsupported_type_returns_400(self, client):
        """Uploading a .txt file should return HTTP 400."""
        response = client.post("/upload", files={"file": ("resume.txt", b"hello txt", "text/plain")})
        assert response.status_code == 400
        assert "not supported" in response.json()["detail"].lower()

    def test_upload_empty_file_returns_400(self, client):
        """Empty file bytes should return HTTP 400."""
        response = client.post("/upload", files={"file": ("resume.pdf", b"", "application/pdf")})
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# /extract-skills endpoint tests
# ---------------------------------------------------------------------------

class TestExtractSkillsEndpoint:
    def test_extract_returns_skill_list(self, client, sample_resume_text):
        """Extracting from generic text using ad-hoc POST."""
        response = client.post("/extract-skills", json={"text": sample_resume_text})
        assert response.status_code == 200
        data = response.json()
        assert "raw_skills" in data
        assert len(data["raw_skills"]) > 0

    def test_extract_finds_python(self, client, sample_resume_text):
        """Python should be detected from the sample resume text."""
        response = client.post("/extract-skills", json={"text": sample_resume_text})
        assert "Python" in response.json()["raw_skills"]

    def test_extract_invalid_document_id_returns_400(self, client):
        """Unknown or invalid document ID should return HTTP 400 or 404."""
        response = client.post("/extract-skills/abc_123_invalid")
        assert response.status_code in (400, 404)


# ---------------------------------------------------------------------------
# /recommend endpoint tests
# ---------------------------------------------------------------------------

class TestRecommendEndpoint:
    def test_recommend_invalid_document_returns_400(self, client):
        """Should fail elegantly on missing documents."""
        response = client.get("/recommend/invalid_id")
        assert response.status_code in (400, 404)


# ---------------------------------------------------------------------------
# /trends endpoint tests
# ---------------------------------------------------------------------------

class TestTrendsEndpoint:
    def test_trends_returns_list(self, client):
        """Should return a list of trending skills with demand scores."""
        response = client.get("/trends")
        assert response.status_code == 200
        assert "top_skills" in response.json()
        
    def test_trends_role_route(self, client):
        """Should return trending skills for a specific role."""
        response = client.get("/trends/role/Data%20Scientist")
        assert response.status_code == 200
        assert "role_name" in response.json()


# ---------------------------------------------------------------------------
# /career-path endpoint tests
# ---------------------------------------------------------------------------

class TestCareerPathEndpoint:
    def test_career_path_invalid_id_returns_eror(self, client):
        """Unknown role ID should return HTTP 400/404."""
        response = client.get("/career-path/invalid-id")
        assert response.status_code in (400, 404)
        
    def test_career_path_roles(self, client):
        """Should return available path roles."""
        response = client.get("/career-path/roles")
        assert response.status_code == 200
        assert "roles" in response.json()