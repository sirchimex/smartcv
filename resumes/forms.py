from django import forms
from django.forms import inlineformset_factory

from .models import (
    Award,
    Certification,
    CustomSection,
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

BASE_WIDGET_CLASS = "form-control"
DATE_ATTRS = {"type": "date", "class": BASE_WIDGET_CLASS}


def _style(fields):
    """Apply a consistent Bootstrap class to every field's widget."""
    for f in fields.values():
        existing = f.widget.attrs.get("class", "")
        if isinstance(f.widget, (forms.CheckboxInput,)):
            f.widget.attrs["class"] = (existing + " form-check-input").strip()
        elif isinstance(f.widget, (forms.Select,)):
            f.widget.attrs["class"] = (existing + " form-select").strip()
        else:
            f.widget.attrs["class"] = (existing + " " + BASE_WIDGET_CLASS).strip()


class ResumeForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ["title", "template", "professional_summary"]
        widgets = {
            "professional_summary": forms.Textarea(
                attrs={"rows": 6, "placeholder": "A 2-4 sentence pitch for who you are professionally..."}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["template"].queryset = Template.objects.all()
        _style(self.fields)


class ResumeCustomizeForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ["template", "theme_color", "font_family", "sidebar_position"]
        widgets = {
            "theme_color": forms.TextInput(attrs={"type": "color"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class PersonalInfoForm(forms.ModelForm):
    class Meta:
        model = PersonalInfo
        exclude = ["resume"]
        widgets = {
            "date_of_birth": forms.DateInput(attrs=DATE_ATTRS),
            "address": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        exclude = ["resume", "order"]
        widgets = {
            "start_date": forms.DateInput(attrs=DATE_ATTRS),
            "end_date": forms.DateInput(attrs=DATE_ATTRS),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        exclude = ["resume", "order"]
        widgets = {
            "start_date": forms.DateInput(attrs=DATE_ATTRS),
            "end_date": forms.DateInput(attrs=DATE_ATTRS),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


ExperienceFormSet = inlineformset_factory(
    Resume, Experience, form=ExperienceForm, extra=1, can_delete=True
)
EducationFormSet = inlineformset_factory(
    Resume, Education, form=EducationForm, extra=1, can_delete=True
)


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        exclude = ["resume", "order"]
        widgets = {"level": forms.NumberInput(attrs={"min": 1, "max": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class CertificationForm(forms.ModelForm):
    class Meta:
        model = Certification
        exclude = ["resume", "order"]
        widgets = {
            "issue_date": forms.DateInput(attrs=DATE_ATTRS),
            "expiry_date": forms.DateInput(attrs=DATE_ATTRS),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        exclude = ["resume", "order"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class LanguageForm(forms.ModelForm):
    class Meta:
        model = Language
        exclude = ["resume", "order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class AwardForm(forms.ModelForm):
    class Meta:
        model = Award
        exclude = ["resume", "order"]
        widgets = {
            "date": forms.DateInput(attrs=DATE_ATTRS),
            "description": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class PublicationForm(forms.ModelForm):
    class Meta:
        model = Publication
        exclude = ["resume", "order"]
        widgets = {
            "date": forms.DateInput(attrs=DATE_ATTRS),
            "description": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class ReferenceForm(forms.ModelForm):
    class Meta:
        model = Reference
        exclude = ["resume", "order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class HobbyInterestForm(forms.ModelForm):
    class Meta:
        model = HobbyInterest
        exclude = ["resume", "order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class CustomSectionForm(forms.ModelForm):
    class Meta:
        model = CustomSection
        exclude = ["resume", "order"]
        widgets = {"content": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


# Registry that drives the generic add/edit/delete views + builder hub for
# every "simple repeatable" section (i.e. everything except Experience and
# Education, which use formsets for inline dynamic add/remove).
SIMPLE_SECTION_REGISTRY = {
    "skills": {
        "model": Skill,
        "form": SkillForm,
        "related_name": "skills",
        "label": "Skills",
        "icon": "bi-lightning-charge",
    },
    "certifications": {
        "model": Certification,
        "form": CertificationForm,
        "related_name": "certifications",
        "label": "Certifications",
        "icon": "bi-patch-check",
    },
    "projects": {
        "model": Project,
        "form": ProjectForm,
        "related_name": "projects",
        "label": "Projects",
        "icon": "bi-kanban",
    },
    "languages": {
        "model": Language,
        "form": LanguageForm,
        "related_name": "languages",
        "label": "Languages",
        "icon": "bi-translate",
    },
    "awards": {
        "model": Award,
        "form": AwardForm,
        "related_name": "awards",
        "label": "Awards & Achievements",
        "icon": "bi-trophy",
    },
    "publications": {
        "model": Publication,
        "form": PublicationForm,
        "related_name": "publications",
        "label": "Publications",
        "icon": "bi-journal-text",
    },
    "references": {
        "model": Reference,
        "form": ReferenceForm,
        "related_name": "references",
        "label": "References",
        "icon": "bi-person-check",
    },
    "hobbies": {
        "model": HobbyInterest,
        "form": HobbyInterestForm,
        "related_name": "hobbies",
        "label": "Hobbies & Interests",
        "icon": "bi-controller",
    },
    "custom_sections": {
        "model": CustomSection,
        "form": CustomSectionForm,
        "related_name": "custom_sections",
        "label": "Custom Sections",
        "icon": "bi-plus-square",
    },
}
