from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from .forms import (
    EducationFormSet,
    ExperienceFormSet,
    PersonalInfoForm,
    ResumeCustomizeForm,
    ResumeForm,
    SIMPLE_SECTION_REGISTRY,
)
from .models import DownloadHistory, PersonalInfo, Resume, Template

PDF_ENGINE_AVAILABLE = True
try:
    from weasyprint import HTML
except Exception:  # pragma: no cover - system libs (pango/cairo) missing
    PDF_ENGINE_AVAILABLE = False


def _owned_resume_or_404(request, pk):
    return get_object_or_404(Resume, pk=pk, user=request.user)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@login_required
def dashboard(request):
    profile = request.user.profile
    resumes = Resume.objects.filter(user=request.user)
    recent_resumes = resumes[:5]
    download_count = DownloadHistory.objects.filter(user=request.user).count()
    recent_downloads = DownloadHistory.objects.filter(user=request.user)[:5]

    avg_completion = 0
    if resumes:
        avg_completion = int(
            sum(r.completion_percentage() for r in resumes) / resumes.count()
        )

    context = {
        "total_cvs": resumes.count(),
        "recent_resumes": recent_resumes,
        "download_count": download_count,
        "recent_downloads": recent_downloads,
        "profile_completion": avg_completion,
        "profile": profile,
        "templates": Template.objects.all(),
        "resume_limit": None if profile.is_premium else profile.FREE_PLAN_RESUME_LIMIT,
    }
    return render(request, "resumes/dashboard.html", context)


# ---------------------------------------------------------------------------
# Resume list / create / delete
# ---------------------------------------------------------------------------
@login_required
def resume_list(request):
    resumes = Resume.objects.filter(user=request.user)
    return render(request, "resumes/resume_list.html", {"resumes": resumes})


@login_required
def resume_create(request):
    profile = request.user.profile
    current_count = Resume.objects.filter(user=request.user).count()
    if profile.resume_limit_reached(current_count):
        messages.warning(
            request,
            f"Free plan is limited to {profile.FREE_PLAN_RESUME_LIMIT} CVs. "
            "Upgrade to Premium for unlimited CVs.",
        )
        return redirect("resumes:dashboard")

    default_template = Template.objects.filter(is_premium=False).first() or Template.objects.first()
    if default_template is None:
        messages.error(request, "No templates are configured yet. Run migrations/seed data first.")
        return redirect("resumes:dashboard")

    resume = Resume.objects.create(
        user=request.user, title="Untitled CV", template=default_template
    )
    PersonalInfo.objects.create(
        resume=resume, full_name=request.user.get_full_name() or request.user.username
    )
    messages.success(request, "New CV created. Let's fill it in.")
    return redirect("resumes:builder", pk=resume.pk)


@login_required
@require_POST
def resume_delete(request, pk):
    resume = _owned_resume_or_404(request, pk)
    resume.delete()
    messages.info(request, "CV deleted.")
    return redirect("resumes:list")


@login_required
def resume_duplicate(request, pk):
    """Simple duplication: copies top-level resume + personal info only.
    (Deep-copying every child section is a fast follow, not core scope.)"""
    original = _owned_resume_or_404(request, pk)
    profile = request.user.profile
    current_count = Resume.objects.filter(user=request.user).count()
    if profile.resume_limit_reached(current_count):
        messages.warning(request, "Free plan CV limit reached. Upgrade to duplicate more CVs.")
        return redirect("resumes:dashboard")

    copy = Resume.objects.create(
        user=request.user,
        title=f"{original.title} (copy)",
        template=original.template,
        professional_summary=original.professional_summary,
        theme_color=original.theme_color,
        font_family=original.font_family,
        sidebar_position=original.sidebar_position,
    )
    if hasattr(original, "personal_info"):
        pi = original.personal_info
        PersonalInfo.objects.create(
            resume=copy,
            full_name=pi.full_name,
            professional_title=pi.professional_title,
            nationality=pi.nationality,
            address=pi.address,
            phone=pi.phone,
            email=pi.email,
            linkedin=pi.linkedin,
            github=pi.github,
            portfolio_website=pi.portfolio_website,
        )
    messages.success(request, "CV duplicated.")
    return redirect("resumes:builder", pk=copy.pk)


# ---------------------------------------------------------------------------
# Builder hub
# ---------------------------------------------------------------------------
@login_required
def builder(request, pk):
    resume = _owned_resume_or_404(request, pk)
    sections = []
    for key, cfg in SIMPLE_SECTION_REGISTRY.items():
        related_manager = getattr(resume, cfg["related_name"])
        sections.append(
            {
                "key": key,
                "label": cfg["label"],
                "icon": cfg["icon"],
                "count": related_manager.count(),
            }
        )
    context = {
        "resume": resume,
        "sections": sections,
        "experience_count": resume.experiences.count(),
        "education_count": resume.educations.count(),
        "has_personal_info": hasattr(resume, "personal_info"),
        "completion": resume.completion_percentage(),
    }
    return render(request, "resumes/builder.html", context)


@login_required
def resume_meta_edit(request, pk):
    resume = _owned_resume_or_404(request, pk)
    if request.method == "POST":
        form = ResumeForm(request.POST, instance=resume)
        if form.is_valid():
            form.save()
            messages.success(request, "CV details saved.")
            return redirect("resumes:builder", pk=resume.pk)
    else:
        form = ResumeForm(instance=resume)
    return render(request, "resumes/section_form.html", {
        "resume": resume, "form": form, "title": "CV Title & Summary",
        "ai_suggestion_url": "ai:field_suggestions",
        "ai_suggestions": [
            {
                "label": "Suggest summaries",
                "icon": "bi-stars",
                "field_type": "summary",
                "target": "professional_summary",
            },
        ],
    })


@login_required
def personal_info_edit(request, pk):
    resume = _owned_resume_or_404(request, pk)
    instance = getattr(resume, "personal_info", None)
    if request.method == "POST":
        form = PersonalInfoForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            personal_info = form.save(commit=False)
            personal_info.resume = resume
            personal_info.save()
            messages.success(request, "Personal information saved.")
            return redirect("resumes:builder", pk=resume.pk)
    else:
        form = PersonalInfoForm(instance=instance)
    return render(request, "resumes/section_form.html", {
        "resume": resume, "form": form, "title": "Personal Information", "is_multipart": True,
        "ai_suggestion_url": "ai:field_suggestions",
        "ai_suggestions": [
            {
                "label": "Suggest titles",
                "icon": "bi-person-workspace",
                "field_type": "professional_title",
                "target": "professional_title",
            },
        ],
    })


@login_required
def customize(request, pk):
    resume = _owned_resume_or_404(request, pk)
    if request.method == "POST":
        form = ResumeCustomizeForm(request.POST, instance=resume)
        if form.is_valid():
            form.save()
            messages.success(request, "Design updated.")
            return redirect("resumes:builder", pk=resume.pk)
    else:
        form = ResumeCustomizeForm(instance=resume)
    return render(request, "resumes/customize.html", {
        "resume": resume, "form": form, "templates": Template.objects.all(),
    })


# ---------------------------------------------------------------------------
# Experience / Education - inline formsets (dynamic add/remove via JS)
# ---------------------------------------------------------------------------
@login_required
def experience_edit(request, pk):
    resume = _owned_resume_or_404(request, pk)
    if request.method == "POST":
        formset = ExperienceFormSet(request.POST, instance=resume, prefix="experience")
        if formset.is_valid():
            formset.save()
            messages.success(request, "Work experience saved.")
            return redirect("resumes:builder", pk=resume.pk)
    else:
        formset = ExperienceFormSet(instance=resume, prefix="experience")
    return render(request, "resumes/formset_section.html", {
        "resume": resume, "formset": formset, "title": "Work Experience",
        "empty_message": "Add roles starting with your most recent.",
        "ai_suggestion_url": "ai:field_suggestions",
        "ai_formset_suggestions": True,
    })


@login_required
def education_edit(request, pk):
    resume = _owned_resume_or_404(request, pk)
    if request.method == "POST":
        formset = EducationFormSet(request.POST, instance=resume, prefix="education")
        if formset.is_valid():
            formset.save()
            messages.success(request, "Education saved.")
            return redirect("resumes:builder", pk=resume.pk)
    else:
        formset = EducationFormSet(instance=resume, prefix="education")
    return render(request, "resumes/formset_section.html", {
        "resume": resume, "formset": formset, "title": "Education",
        "empty_message": "Add your degrees, most recent first.",
    })


# ---------------------------------------------------------------------------
# Generic simple-section CRUD (skills, certifications, projects, etc.)
# ---------------------------------------------------------------------------
def _section_or_404(key):
    cfg = SIMPLE_SECTION_REGISTRY.get(key)
    if cfg is None:
        raise Http404("Unknown section")
    return cfg


@login_required
def section_list(request, pk, key):
    resume = _owned_resume_or_404(request, pk)
    cfg = _section_or_404(key)
    items = getattr(resume, cfg["related_name"]).all()
    return render(request, "resumes/section_list.html", {
        "resume": resume, "items": items, "key": key, "label": cfg["label"],
    })


@login_required
def section_item_form(request, pk, key, item_pk=None):
    resume = _owned_resume_or_404(request, pk)
    cfg = _section_or_404(key)
    Model, FormClass = cfg["model"], cfg["form"]

    instance = None
    if item_pk:
        instance = get_object_or_404(Model, pk=item_pk, resume=resume)

    if request.method == "POST":
        form = FormClass(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.resume = resume
            obj.save()
            messages.success(request, f"{cfg['label']} item saved.")
            return redirect("resumes:section_list", pk=resume.pk, key=key)
    else:
        form = FormClass(instance=instance)

    return render(request, "resumes/section_item_form.html", {
        "resume": resume, "form": form, "label": cfg["label"], "key": key, "editing": instance is not None,
        "ai_suggestion_url": "ai:field_suggestions" if key == "skills" else "",
        "ai_suggestions": [
            {
                "label": "Suggest skills",
                "icon": "bi-lightning-charge",
                "field_type": "skills",
                "target": "name",
            },
        ] if key == "skills" else [],
    })


@login_required
@require_POST
def section_item_delete(request, pk, key, item_pk):
    resume = _owned_resume_or_404(request, pk)
    cfg = _section_or_404(key)
    instance = get_object_or_404(cfg["model"], pk=item_pk, resume=resume)
    instance.delete()
    messages.info(request, "Item removed.")
    return redirect("resumes:section_list", pk=resume.pk, key=key)


# ---------------------------------------------------------------------------
# Preview / PDF export
# ---------------------------------------------------------------------------
def _template_html_name(resume):
    """Map a Template slug to its rendering template file."""
    known = {
        "modern-corporate":    "resumes/templates_layouts/modern_corporate.html",
        "minimalist":          "resumes/templates_layouts/minimalist.html",
        "ats-friendly-resume": "resumes/templates_layouts/ats_friendly.html",
        "creative-portfolio":  "resumes/templates_layouts/creative_portfolio.html",
        "executive-classic":   "resumes/templates_layouts/executive_classic.html",
        "tech-dark":           "resumes/templates_layouts/tech_dark.html",
        "two-column-elegant":  "resumes/templates_layouts/two_column_elegant.html",
        "academic-research":   "resumes/templates_layouts/academic_research.html",
        "bold-infographic":    "resumes/templates_layouts/bold_infographic.html",
        "compact-one-page":    "resumes/templates_layouts/compact_one_page.html",
    }
    return known.get(resume.template.slug, "resumes/templates_layouts/ats_friendly.html")


@login_required
def resume_preview(request, pk):
    resume = _owned_resume_or_404(request, pk)
    template_name = _template_html_name(resume)
    return render(request, template_name, {
        "resume": resume, "watermark": not request.user.profile.is_premium,
    })


@login_required
def resume_pdf(request, pk):
    resume = _owned_resume_or_404(request, pk)
    if not PDF_ENGINE_AVAILABLE:
        messages.error(
            request,
            "PDF export isn't available in this environment (WeasyPrint's system "
            "libraries are missing). It will work once deployed with the libraries "
            "from the deployment guide.",
        )
        return redirect("resumes:builder", pk=resume.pk)

    template_name = _template_html_name(resume)
    is_premium = request.user.profile.is_premium
    html_string = render_to_string(
        template_name,
        {"resume": resume, "watermark": not is_premium, "for_pdf": True},
        request=request,
    )
    base_url = request.build_absolute_uri("/")
    pdf_file = HTML(string=html_string, base_url=base_url).write_pdf()

    DownloadHistory.objects.create(user=request.user, resume=resume, file_format="pdf")

    response = HttpResponse(pdf_file, content_type="application/pdf")
    filename = (resume.title or "resume").replace(" ", "_")
    response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
    return response


@login_required
def template_picker(request, pk):
    resume = _owned_resume_or_404(request, pk)
    profile = request.user.profile
    if request.method == "POST":
        template_id = request.POST.get("template_id")
        template = get_object_or_404(Template, pk=template_id)
        if template.is_premium and not profile.is_premium:
            messages.warning(request, "That template is Premium-only. Upgrade to unlock it.")
            return redirect("resumes:template_picker", pk=resume.pk)
        resume.template = template
        resume.save(update_fields=["template", "updated_at"])
        messages.success(request, f"Switched to the {template.name} template.")
        return redirect("resumes:builder", pk=resume.pk)

    return render(request, "resumes/template_picker.html", {
        "resume": resume, "templates": Template.objects.all(), "profile": profile,
    })
