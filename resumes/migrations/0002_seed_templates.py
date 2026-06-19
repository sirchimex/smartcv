from django.db import migrations


def seed_templates(apps, schema_editor):
    Template = apps.get_model("resumes", "Template")
    templates = [
        {
            "name": "Modern Corporate",
            "slug": "modern-corporate",
            "description": "Bold sidebar layout with a strong header band. Great for management and corporate roles.",
            "is_premium": False,
            "accent_color": "#1d4ed8",
            "order": 1,
        },
        {
            "name": "Minimalist",
            "slug": "minimalist",
            "description": "Single column, generous whitespace, quiet typography. Works for any industry.",
            "is_premium": False,
            "accent_color": "#111827",
            "order": 2,
        },
        {
            "name": "ATS-Friendly Resume",
            "slug": "ats-friendly-resume",
            "description": "Plain single-column structure tuned to parse cleanly through applicant tracking systems.",
            "is_premium": False,
            "accent_color": "#0f766e",
            "order": 3,
        },
    ]
    for data in templates:
        Template.objects.update_or_create(slug=data["slug"], defaults=data)


def unseed_templates(apps, schema_editor):
    Template = apps.get_model("resumes", "Template")
    Template.objects.filter(
        slug__in=["modern-corporate", "minimalist", "ats-friendly-resume"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("resumes", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_templates, unseed_templates),
    ]
