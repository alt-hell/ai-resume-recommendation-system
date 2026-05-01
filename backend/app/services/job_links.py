"""
job_links.py (Service)
----------------------
Generates real job application links using JSearch API (via RapidAPI).

JSearch aggregates job listings from Google for Jobs, which covers:
  LinkedIn, Indeed, Glassdoor, Naukri, ZipRecruiter, and 100+ other platforms.

Free tier: 200 requests/month, no credit card required.

Fallback: If API is unavailable or quota exceeded, generates smart
search URLs for major job platforms.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote_plus

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class JobLinkItem:
    """A single job listing with apply link."""
    job_title: str
    company: str
    location: str
    apply_url: str
    platform: str            # e.g. "LinkedIn", "Indeed", "Glassdoor"
    posted_date: str = ""    # e.g. "2 days ago"
    job_type: str = ""       # e.g. "Full-time", "Remote"
    description_snippet: str = ""  # Short preview of the job description

    def to_dict(self) -> dict:
        return {
            "job_title": self.job_title,
            "company": self.company,
            "location": self.location,
            "apply_url": self.apply_url,
            "platform": self.platform,
            "posted_date": self.posted_date,
            "job_type": self.job_type,
            "description_snippet": self.description_snippet,
        }


@dataclass
class JobLinksResult:
    """Complete job links result."""
    predicted_role: str
    jobs: list[JobLinkItem] = field(default_factory=list)
    source: str = "fallback"  # "jsearch" or "fallback"
    total_found: int = 0

    def to_dict(self) -> dict:
        return {
            "predicted_role": self.predicted_role,
            "jobs": [j.to_dict() for j in self.jobs],
            "source": self.source,
            "total_found": self.total_found,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_job_links(
    predicted_role: str,
    skills: list[str],
    location: str = "India",
    num_results: int = 5,
) -> JobLinksResult:
    """
    Generate job application links for the predicted role.

    Tries JSearch API first, falls back to static search URLs.

    Args:
        predicted_role: The predicted job role (e.g. "Backend Developer")
        skills: User's normalized skills for refining the search
        location: Preferred location for job search
        num_results: Number of job links to return (default 5)

    Returns:
        JobLinksResult with up to `num_results` job links.
    """
    # Try JSearch API if key is available
    if settings.RAPIDAPI_KEY:
        result = await _fetch_jsearch_jobs(predicted_role, skills, location, num_results)
        if result.jobs:
            return result
        logger.warning("JSearch returned no results — falling back to search URLs")

    # Fallback: Generate smart search URLs
    return _generate_fallback_links(predicted_role, skills, location)


# ---------------------------------------------------------------------------
# JSearch API Integration
# ---------------------------------------------------------------------------

async def _fetch_jsearch_jobs(
    role: str,
    skills: list[str],
    location: str,
    num_results: int,
) -> JobLinksResult:
    """
    Fetch real job listings from JSearch API (via RapidAPI).

    API docs: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
    """
    # Build search query: role + top 3 skills
    top_skills = skills[:3] if skills else []
    query_parts = [role] + top_skills
    query = " ".join(query_parts)

    params = {
        "query": f"{query} in {location}",
        "page": "1",
        "num_pages": "1",
    }

    headers = {
        "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://jsearch.p.rapidapi.com/search",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        raw_jobs = data.get("data", [])[:num_results]

        if not raw_jobs:
            logger.info("JSearch returned 0 jobs for query: '%s'", query)
            return JobLinksResult(predicted_role=role, source="jsearch")

        jobs: list[JobLinkItem] = []
        for job in raw_jobs:
            # Handle possible None values from API
            job_title = job.get("job_title") or role
            company = job.get("employer_name") or "Company"
            location_str = job.get("job_city") or job.get("job_country") or location
            
            apply_link = job.get("job_apply_link") or ""
            google_link = job.get("job_google_link") or ""
            apply_url = apply_link if apply_link else google_link
            
            publisher = job.get("job_publisher") or ""
            platform = _detect_platform(publisher, apply_url)

            # Build description snippet (first 150 chars)
            desc = job.get("job_description") or ""
            snippet = desc[:150].strip() + "..." if len(desc) > 150 else desc

            # Determine job type
            job_type_parts = []
            if job.get("job_is_remote"):
                job_type_parts.append("Remote")
            emp_type = job.get("job_employment_type") or ""
            if emp_type:
                job_type_parts.append(emp_type.replace("_", " ").title())

            posted_date = job.get("job_posted_at_datetime_utc") or ""

            jobs.append(JobLinkItem(
                job_title=job_title,
                company=company,
                location=location_str,
                apply_url=apply_url,
                platform=platform,
                posted_date=posted_date[:10] if posted_date else "",
                job_type=" · ".join(job_type_parts) if job_type_parts else "Full-time",
                description_snippet=snippet,
            ))

        logger.info("JSearch found %d jobs for '%s'", len(jobs), query)

        return JobLinksResult(
            predicted_role=role,
            jobs=jobs,
            source="jsearch",
            total_found=data.get("total", len(jobs)),
        )

    except httpx.HTTPStatusError as exc:
        logger.error("JSearch API HTTP error %d: %s", exc.response.status_code, exc.response.text[:200])
    except Exception as exc:
        logger.error("JSearch API failed: %s", exc)

    return JobLinksResult(predicted_role=role, source="jsearch")


def _detect_platform(publisher: str, url: str) -> str:
    """Detect which job platform a listing comes from."""
    publisher_lower = publisher.lower()
    url_lower = url.lower()

    platform_patterns = {
        "LinkedIn": ["linkedin"],
        "Indeed": ["indeed"],
        "Glassdoor": ["glassdoor"],
        "Naukri": ["naukri"],
        "ZipRecruiter": ["ziprecruiter"],
        "Monster": ["monster"],
        "Google": ["google", "careers.google"],
        "Dice": ["dice.com"],
        "Simply Hired": ["simplyhired"],
        "CareerBuilder": ["careerbuilder"],
    }

    for platform, patterns in platform_patterns.items():
        for pat in patterns:
            if pat in publisher_lower or pat in url_lower:
                return platform

    return publisher or "Job Board"


# ---------------------------------------------------------------------------
# Fallback: Static search URLs
# ---------------------------------------------------------------------------

def _generate_fallback_links(
    role: str,
    skills: list[str],
    location: str,
) -> JobLinksResult:
    """
    Generate pre-filled job search URLs for major platforms.
    Used when JSearch API is unavailable or quota exceeded.
    """
    encoded_role = quote_plus(role)
    encoded_location = quote_plus(location)
    skill_query = quote_plus(f"{role} {' '.join(skills[:2])}")

    platforms = [
        JobLinkItem(
            job_title=f"{role} Jobs",
            company="LinkedIn",
            location=location,
            apply_url=f"https://www.linkedin.com/jobs/search/?keywords={encoded_role}&location={encoded_location}",
            platform="LinkedIn",
            job_type="Multiple openings",
            description_snippet=f"Search {role} positions on LinkedIn — the world's largest professional network.",
        ),
        JobLinkItem(
            job_title=f"{role} Jobs",
            company="Indeed",
            location=location,
            apply_url=f"https://www.indeed.com/jobs?q={encoded_role}&l={encoded_location}",
            platform="Indeed",
            job_type="Multiple openings",
            description_snippet=f"Find {role} jobs on Indeed — search millions of jobs from thousands of companies.",
        ),
        JobLinkItem(
            job_title=f"{role} Jobs",
            company="Naukri",
            location=location,
            apply_url=f"https://www.naukri.com/{role.lower().replace(' ', '-')}-jobs?k={encoded_role}",
            platform="Naukri",
            job_type="Multiple openings",
            description_snippet=f"Browse {role} opportunities on Naukri — India's #1 job portal.",
        ),
        JobLinkItem(
            job_title=f"{role} Jobs",
            company="Glassdoor",
            location=location,
            apply_url=f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={encoded_role}&locT=C&locKeyword={encoded_location}",
            platform="Glassdoor",
            job_type="Multiple openings",
            description_snippet=f"Explore {role} listings on Glassdoor — see salaries, reviews, and job openings.",
        ),
        JobLinkItem(
            job_title=f"{role} Jobs",
            company="Google Jobs",
            location=location,
            apply_url=f"https://www.google.com/search?q={skill_query}+jobs+{encoded_location}&ibp=htl;jobs",
            platform="Google Jobs",
            job_type="Aggregated listings",
            description_snippet=f"Search {role} jobs across all platforms via Google's job aggregator.",
        ),
    ]

    return JobLinksResult(
        predicted_role=role,
        jobs=platforms,
        source="fallback",
        total_found=5,
    )
