"""
AI service layer for SmartCV Builder.

All functions are synchronous and make one chat completion call.
They raise AIServiceError on API failure so callers can handle gracefully
(show a user-facing message rather than a 500 error).

Configure AI_PROVIDER in settings to choose 'openai' or 'github'.
Set the corresponding API key and model in environment variables.
"""
from __future__ import annotations

import json

from django.conf import settings


class AIServiceError(Exception):
    """Raised when the AI call fails or returns unusable content."""


def _client():
    """Lazily build an AI client (OpenAI or GitHub) based on AI_PROVIDER setting.
    Import is only required when AI features are actually used.
    """
    import openai
    
    provider = getattr(settings, "AI_PROVIDER", "openai").lower()
    
    if provider == "github":
        # GitHub Models API (OpenAI-compatible, uses Azure endpoint)
        key = getattr(settings, "GITHUB_API_KEY", "")
        endpoint = getattr(settings, "GITHUB_AI_ENDPOINT", "https://models.inference.ai.azure.com")
        if not key:
            raise AIServiceError(
                "GitHub API key is not configured. Set GITHUB_API_KEY in your environment."
            )
        return openai.OpenAI(api_key=key, base_url=endpoint)
    
    elif provider == "openai":
        # Standard OpenAI API
        key = getattr(settings, "OPENAI_API_KEY", "")
        if not key:
            raise AIServiceError(
                "OpenAI API key is not configured. Set OPENAI_API_KEY in your environment."
            )
        return openai.OpenAI(api_key=key)
    
    else:
        raise AIServiceError(f"Unknown AI_PROVIDER: {provider}. Use 'openai' or 'github'.")


def _get_model() -> str:
    """Get the model name based on AI_PROVIDER."""
    provider = getattr(settings, "AI_PROVIDER", "openai").lower()
    if provider == "github":
        return getattr(settings, "GITHUB_AI_MODEL", "gpt-4o")
    elif provider == "zai":
        return getattr(settings, "ZAI_AI_MODEL", "glm-5.2")
    else:
        return getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")


def _chat(system: str, user: str, max_tokens: int = 600) -> str:
    """Single-turn chat completion, returns the text content."""
    provider = getattr(settings, "AI_PROVIDER", "openai").lower()
    # ZAI provider: use simple HTTP POST to the configured endpoint
    if provider == "zai":
        try:
            import requests

            key = getattr(settings, "ZAI_API_KEY", "")
            endpoint = getattr(settings, "ZAI_AI_ENDPOINT", "https://api.z.ai/api/paas/v4/chat/completions")
            model = getattr(settings, "ZAI_AI_MODEL", "glm-5.2")
            if not key:
                raise AIServiceError(
                    "ZAI API key is not configured. Set ZAI_API_KEY in your environment."
                )

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            }
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Accept-Language": "en-US,en",
            }
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=20)
            if resp.status_code != 200:
                raise AIServiceError(f"ZAI request failed: {resp.status_code} {resp.text[:200]}")
            data = resp.json()
            # Support common response shapes: choices[].message.content or choices[].text
            try:
                return data["choices"][0]["message"]["content"].strip()
            except Exception:
                try:
                    return data["choices"][0]["text"].strip()
                except Exception:
                    raise AIServiceError(f"Unexpected ZAI response shape: {str(data)[:200]}")
        except AIServiceError:
            raise
        except Exception as exc:
            raise AIServiceError(f"ZAI request failed: {exc}") from exc

    # Fallback to OpenAI / OpenAI-compatible client (OpenAI or GitHub)
    try:
        resp = _client().chat.completions.create(
            model=_get_model(),
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        raise AIServiceError(f"AI request failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Public feature functions
# ---------------------------------------------------------------------------

def rewrite_summary(current_summary: str, job_title: str, skills: list[str]) -> str:
    """Return a rewritten professional summary (2-4 sentences).

    Args:
        current_summary: The user's existing summary text (may be empty).
        job_title: E.g. "Senior Backend Engineer".
        skills: List of skill names for the CV.
    """
    skills_str = ", ".join(skills[:12]) if skills else "not specified"
    system = (
        "You are a professional CV writer. Write concise, impactful professional "
        "summaries (2-4 sentences). Use active voice, avoid clichés, and tailor "
        "the tone to the role. Return only the summary text, no labels or preamble."
    )
    user = (
        f"Role: {job_title}\n"
        f"Key skills: {skills_str}\n"
        f"Existing summary (may be blank): {current_summary or '(empty)'}\n\n"
        "Rewrite or create a strong professional summary for this candidate."
    )
    return _chat(system, user, max_tokens=200)


def analyze_resume(resume_data: dict) -> dict:
    """Return a structured analysis of the CV.

    Args:
        resume_data: A dict with keys: title, summary, experience_count,
                     education_count, skill_count, sections_present (list).

    Returns:
        Dict with keys: score (int 0-100), strengths (list[str]),
        improvements (list[str]), ats_tips (list[str]).
    """
    import json

    system = (
        "You are an expert CV reviewer. Analyze the CV data provided and return "
        "ONLY a JSON object with this exact schema:\n"
        '{"score": <int 0-100>, "strengths": [<str>, ...], '
        '"improvements": [<str>, ...], "ats_tips": [<str>, ...]}\n'
        "score = overall quality. strengths = 2-3 things done well. "
        "improvements = 2-3 concrete suggestions. ats_tips = 1-2 ATS-specific tips. "
        "Return valid JSON only, no markdown fences."
    )
    user = json.dumps(resume_data, indent=2)
    raw = _chat(system, user, max_tokens=500)
    try:
        # Strip any accidental markdown fences
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        raise AIServiceError(f"AI returned non-JSON response: {raw[:200]}") from exc


def career_suggestions(job_title: str, skills: list[str], experience_years: int) -> list[str]:
    """Return 4-6 career development suggestions as a list of strings.

    Args:
        job_title: Current or target job title.
        skills: List of skill names.
        experience_years: Rough years of professional experience.
    """
    import json

    skills_str = ", ".join(skills[:15]) if skills else "not specified"
    system = (
        "You are a career coach. Give specific, actionable career development "
        "suggestions. Return ONLY a JSON array of 4-6 suggestion strings, no preamble."
    )
    user = (
        f"Role: {job_title}\n"
        f"Skills: {skills_str}\n"
        f"Years of experience: {experience_years}\n"
        "Provide career development suggestions."
    )
    raw = _chat(system, user, max_tokens=400)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        result = json.loads(clean)
        if isinstance(result, list):
            return result
        raise AIServiceError("Expected a JSON array from career suggestions.")
    except json.JSONDecodeError as exc:
        raise AIServiceError(f"AI returned non-JSON: {raw[:200]}") from exc


def improve_bullet(bullet_text: str, job_title: str) -> str:
    """Rewrite a single job description bullet to be more impactful.

    Args:
        bullet_text: The existing bullet/description text.
        job_title: The role this bullet belongs to.

    Returns:
        Improved version of the bullet (plain text, no leading dash).
    """
    system = (
        "You are a professional CV writer. Improve job description bullets to be "
        "concise, impact-focused, and quantified where possible. Use strong action "
        "verbs. Return only the improved text, no bullet symbol, no explanation."
    )
    user = f"Role: {job_title}\nOriginal bullet: {bullet_text}\nImproved version:"
    return _chat(system, user, max_tokens=150)


def field_suggestions(
    field_type: str,
    professional_title: str,
    current_value: str = "",
    existing_skills: list[str] | None = None,
    job_title: str = "",
    company: str = "",
) -> list[dict[str, str]]:
    """Return insertable suggestions for a CV field.

    Each suggestion is a dict with a short label and a value suitable for
    inserting into a form field.
    """
    allowed_types = {"summary", "skills", "job_description", "professional_title"}
    if field_type not in allowed_types:
        raise AIServiceError("Unknown suggestion field type.")

    existing_skills = existing_skills or []
    target_title = professional_title or job_title or "the target role"
    system = (
        "You are a practical CV writing assistant. Generate concise, realistic "
        "content a job seeker can paste into a CV form. Return ONLY valid JSON "
        "with this schema: [{\"label\": <short label>, \"value\": <pasteable text>}]. "
        "Do not use markdown fences."
    )

    if field_type == "summary":
        instruction = (
            "Create 3 alternative professional summaries. Each value should be "
            "2-4 sentences, tailored to the professional title."
        )
    elif field_type == "skills":
        instruction = (
            "Suggest 12 relevant CV skills. Each value should be one skill name only. "
            "Prefer a mix of technical and transferable skills. Avoid duplicates."
        )
    elif field_type == "job_description":
        instruction = (
            "Create 4 alternative job description entries. Each value should contain "
            "2-3 strong CV bullet lines separated by newlines. Use action verbs and "
            "include measurable impact placeholders only where the user can edit them."
        )
    else:
        instruction = (
            "Suggest 5 polished professional title options. Each value should be one "
            "short title suitable for a CV header."
        )

    user = (
        f"Field type: {field_type}\n"
        f"Professional title: {target_title}\n"
        f"Current field value: {current_value or '(empty)'}\n"
        f"Existing skills: {', '.join(existing_skills[:20]) or '(none)'}\n"
        f"Experience job title: {job_title or '(not specified)'}\n"
        f"Company: {company or '(not specified)'}\n\n"
        f"{instruction}"
    )

    raw = _chat(system, user, max_tokens=700)
    try:
        parsed = json.loads(raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip())
    except json.JSONDecodeError as exc:
        raise AIServiceError(f"AI returned non-JSON suggestions: {raw[:200]}") from exc

    if not isinstance(parsed, list):
        raise AIServiceError("AI suggestions were not returned as a list.")

    suggestions: list[dict[str, str]] = []
    for item in parsed[:12]:
        if isinstance(item, str):
            label = item[:48]
            value = item
        elif isinstance(item, dict):
            label = str(item.get("label") or item.get("value") or "Suggestion")[:48]
            value = str(item.get("value") or "").strip()
        else:
            continue
        if value:
            suggestions.append({"label": label, "value": value})

    if not suggestions:
        raise AIServiceError("AI returned empty suggestions.")
    return suggestions
