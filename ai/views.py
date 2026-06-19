"""
AI views — AJAX endpoints consumed by the builder UI.

All endpoints return JSON so the frontend can inject results without a
full page reload. They require login and use POST + CSRF.

Feature flags:
  AI features are silently disabled (return a graceful error JSON) when
  OPENAI_API_KEY is not set, so the builder still works without a key.
"""
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from resumes.models import Resume

from .services import (
    AIServiceError,
    analyze_resume,
    career_suggestions,
    field_suggestions,
    improve_bullet,
    rewrite_summary,
)


def _resume_or_404(request, pk):
    return get_object_or_404(Resume, pk=pk, user=request.user)


def _json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "error": message}, status=status)


# ---------------------------------------------------------------------------
# Rewrite professional summary
# ---------------------------------------------------------------------------
@login_required
@require_POST
def ai_rewrite_summary(request, pk):
    resume = _resume_or_404(request, pk)
    skills = list(resume.skills.values_list("name", flat=True))
    job_title = getattr(resume.personal_info, "professional_title", "") if hasattr(resume, "personal_info") else ""
    try:
        text = rewrite_summary(resume.professional_summary, job_title, skills)
        return JsonResponse({"ok": True, "text": text})
    except AIServiceError as exc:
        return _json_error(str(exc))


# ---------------------------------------------------------------------------
# Full resume analysis
# ---------------------------------------------------------------------------
@login_required
@require_POST
def ai_analyze(request, pk):
    resume = _resume_or_404(request, pk)
    sections = []
    if hasattr(resume, "personal_info"):
        sections.append("personal_info")
    for rel in ["experiences", "educations", "skills", "certifications",
                "projects", "languages", "awards", "publications"]:
        if getattr(resume, rel).exists():
            sections.append(rel)

    data = {
        "title": resume.title,
        "summary": resume.professional_summary,
        "experience_count": resume.experiences.count(),
        "education_count": resume.educations.count(),
        "skill_count": resume.skills.count(),
        "sections_present": sections,
    }
    try:
        result = analyze_resume(data)
        return JsonResponse({"ok": True, **result})
    except AIServiceError as exc:
        return _json_error(str(exc))


# ---------------------------------------------------------------------------
# Career suggestions
# ---------------------------------------------------------------------------
@login_required
@require_POST
def ai_career_suggestions(request, pk):
    resume = _resume_or_404(request, pk)
    job_title = (
        getattr(resume.personal_info, "professional_title", "")
        if hasattr(resume, "personal_info") else ""
    ) or resume.title
    skills = list(resume.skills.values_list("name", flat=True))
    experience_years = resume.experiences.count() * 2  # rough proxy

    try:
        suggestions = career_suggestions(job_title, skills, experience_years)
        return JsonResponse({"ok": True, "suggestions": suggestions})
    except AIServiceError as exc:
        return _json_error(str(exc))


# ---------------------------------------------------------------------------
# Improve a single bullet point
# ---------------------------------------------------------------------------
@login_required
@require_POST
def ai_improve_bullet(request, pk):
    resume = _resume_or_404(request, pk)
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return _json_error("Invalid JSON body.")

    bullet = (body.get("bullet") or "").strip()
    job_title = (body.get("job_title") or "").strip()
    if not bullet:
        return _json_error("bullet is required.")

    try:
        improved = improve_bullet(bullet, job_title)
        return JsonResponse({"ok": True, "improved": improved})
    except AIServiceError as exc:
        return _json_error(str(exc))


# ---------------------------------------------------------------------------
# Contextual field suggestions
# ---------------------------------------------------------------------------
@login_required
@require_POST
def ai_field_suggestions(request, pk):
    resume = _resume_or_404(request, pk)
    try:
        body = json.loads(request.body or "{}")
    except (json.JSONDecodeError, ValueError):
        return _json_error("Invalid JSON body.")

    field_type = (body.get("field_type") or "").strip()
    current_value = (body.get("current_value") or "").strip()
    job_title = (body.get("job_title") or "").strip()
    company = (body.get("company") or "").strip()
    professional_title = (
        getattr(resume.personal_info, "professional_title", "")
        if hasattr(resume, "personal_info") else ""
    ) or resume.title
    existing_skills = list(resume.skills.values_list("name", flat=True))

    try:
        suggestions = field_suggestions(
            field_type=field_type,
            professional_title=professional_title,
            current_value=current_value,
            existing_skills=existing_skills,
            job_title=job_title,
            company=company,
        )
        return JsonResponse({"ok": True, "suggestions": suggestions})
    except AIServiceError as exc:
        return _json_error(str(exc))
