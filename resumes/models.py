from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Template(models.Model):
    """A selectable CV layout/theme. Seeded via data migration."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    is_premium = models.BooleanField(default=False)
    accent_color = models.CharField(
        max_length=7, default="#2563eb", help_text="Default accent hex color for this layout"
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Resume(models.Model):
    """A single CV/resume document owned by a user."""

    SIDEBAR_LEFT = "left"
    SIDEBAR_RIGHT = "right"
    SIDEBAR_NONE = "none"
    SIDEBAR_CHOICES = [
        (SIDEBAR_LEFT, "Left"),
        (SIDEBAR_RIGHT, "Right"),
        (SIDEBAR_NONE, "No sidebar"),
    ]

    FONT_CHOICES = [
        ("'Inter', sans-serif", "Inter"),
        ("'Georgia', serif", "Georgia"),
        ("'Roboto Slab', serif", "Roboto Slab"),
        ("'Source Sans Pro', sans-serif", "Source Sans Pro"),
        ("'JetBrains Mono', monospace", "JetBrains Mono"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resumes"
    )
    title = models.CharField(
        max_length=150, help_text="Internal name, e.g. 'Backend Engineer - 2026'"
    )
    template = models.ForeignKey(
        Template, on_delete=models.PROTECT, related_name="resumes"
    )
    professional_summary = models.TextField(blank=True)

    # Customization
    theme_color = models.CharField(max_length=7, blank=True, help_text="Hex color override")
    font_family = models.CharField(
        max_length=60, choices=FONT_CHOICES, default="'Inter', sans-serif"
    )
    sidebar_position = models.CharField(
        max_length=10, choices=SIDEBAR_CHOICES, default=SIDEBAR_LEFT
    )

    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title} ({self.user})"

    def get_absolute_url(self):
        return reverse("resumes:builder", args=[self.pk])

    @property
    def accent(self):
        return self.theme_color or self.template.accent_color

    def completion_percentage(self):
        """Rough estimate of how 'complete' this CV is, used on the dashboard."""
        checks = [
            hasattr(self, "personal_info") and bool(self.personal_info.full_name),
            bool(self.professional_summary),
            self.experiences.exists(),
            self.educations.exists(),
            self.skills.exists(),
        ]
        done = sum(1 for c in checks if c)
        return int(done / len(checks) * 100)


class PersonalInfo(models.Model):
    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
        ("prefer_not_to_say", "Prefer not to say"),
    ]

    resume = models.OneToOneField(
        Resume, on_delete=models.CASCADE, related_name="personal_info"
    )
    full_name = models.CharField(max_length=150)
    professional_title = models.CharField(max_length=150, blank=True)
    profile_picture = models.ImageField(
        upload_to="profile_pictures/", blank=True, null=True
    )
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    nationality = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    linkedin = models.URLField(blank=True)
    github = models.URLField(blank=True)
    portfolio_website = models.URLField(blank=True)

    def __str__(self):
        return self.full_name or f"Personal info for {self.resume}"


class OrderedSectionItem(models.Model):
    """Abstract base for repeatable CV sections."""

    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ["order", "id"]


class Experience(OrderedSectionItem):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="experiences")
    job_title = models.CharField(max_length=150)
    company = models.CharField(max_length=150)
    location = models.CharField(max_length=150, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.job_title} @ {self.company}"


class Education(OrderedSectionItem):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="educations")
    institution = models.CharField(max_length=150)
    degree = models.CharField(max_length=150)
    field_of_study = models.CharField(max_length=150, blank=True)
    gpa = models.CharField(max_length=20, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.degree}, {self.institution}"


class Skill(OrderedSectionItem):
    TECHNICAL = "technical"
    SOFT = "soft"
    CATEGORY_CHOICES = [(TECHNICAL, "Technical"), (SOFT, "Soft skill")]

    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=TECHNICAL)
    level = models.PositiveSmallIntegerField(
        default=3, help_text="1 (beginner) to 5 (expert)"
    )

    def __str__(self):
        return self.name


class Certification(OrderedSectionItem):
    resume = models.ForeignKey(
        Resume, on_delete=models.CASCADE, related_name="certifications"
    )
    name = models.CharField(max_length=150)
    issuing_organization = models.CharField(max_length=150)
    issue_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    credential_url = models.URLField(blank=True)

    def __str__(self):
        return self.name


class Project(OrderedSectionItem):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    technologies_used = models.CharField(max_length=255, blank=True)
    github_link = models.URLField(blank=True)
    live_url = models.URLField(blank=True)

    def __str__(self):
        return self.name


class Language(OrderedSectionItem):
    BASIC = "basic"
    CONVERSATIONAL = "conversational"
    FLUENT = "fluent"
    NATIVE = "native"
    PROFICIENCY_CHOICES = [
        (BASIC, "Basic"),
        (CONVERSATIONAL, "Conversational"),
        (FLUENT, "Fluent"),
        (NATIVE, "Native"),
    ]

    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="languages")
    name = models.CharField(max_length=80)
    proficiency = models.CharField(
        max_length=20, choices=PROFICIENCY_CHOICES, default=CONVERSATIONAL
    )

    def __str__(self):
        return self.name


class Award(OrderedSectionItem):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="awards")
    title = models.CharField(max_length=150)
    organization = models.CharField(max_length=150, blank=True)
    date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title


class Publication(OrderedSectionItem):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="publications")
    title = models.CharField(max_length=200)
    publisher = models.CharField(max_length=150, blank=True)
    date = models.DateField(blank=True, null=True)
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title


class Reference(OrderedSectionItem):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="references")
    name = models.CharField(max_length=150)
    position = models.CharField(max_length=150, blank=True)
    company = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return self.name


class HobbyInterest(OrderedSectionItem):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="hobbies")
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class CustomSection(OrderedSectionItem):
    resume = models.ForeignKey(
        Resume, on_delete=models.CASCADE, related_name="custom_sections"
    )
    title = models.CharField(max_length=150)
    content = models.TextField(blank=True)

    def __str__(self):
        return self.title


class DownloadHistory(models.Model):
    FORMAT_PDF = "pdf"
    FORMAT_CHOICES = [(FORMAT_PDF, "PDF")]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="downloads"
    )
    resume = models.ForeignKey(
        Resume, on_delete=models.CASCADE, related_name="download_history"
    )
    file_format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default=FORMAT_PDF)
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-downloaded_at"]

    def __str__(self):
        return f"{self.resume.title} - {self.downloaded_at:%Y-%m-%d %H:%M}"
