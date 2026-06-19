from django.contrib import admin

from .models import (
    Award,
    Certification,
    CustomSection,
    DownloadHistory,
    Education,
    Experience,
    HobbyInterest,
    Language,
    PersonalInfo,
    Project,
    Publication,
    Reference,
    Resume,
    Skill,
    Template,
)


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_premium", "accent_color", "order"]
    list_editable = ["is_premium", "order"]
    prepopulated_fields = {"slug": ("name",)}


class PersonalInfoInline(admin.StackedInline):
    model = PersonalInfo
    extra = 0


class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 0


class EducationInline(admin.TabularInline):
    model = Education
    extra = 0


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 0


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "template", "is_public", "created_at", "updated_at"]
    list_filter = ["template", "is_public"]
    search_fields = ["title", "user__username", "user__email"]
    inlines = [PersonalInfoInline, ExperienceInline, EducationInline, SkillInline]


@admin.register(DownloadHistory)
class DownloadHistoryAdmin(admin.ModelAdmin):
    list_display = ["resume", "user", "file_format", "downloaded_at"]
    list_filter = ["file_format"]
    date_hierarchy = "downloaded_at"


for model in [Certification, Project, Language, Award, Publication, Reference, HobbyInterest, CustomSection]:
    admin.site.register(model)
