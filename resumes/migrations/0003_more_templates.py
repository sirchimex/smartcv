from django.db import migrations


def add_templates(apps, schema_editor):
    Template = apps.get_model("resumes", "Template")
    new_templates = [
        {
            "name": "Creative Portfolio",
            "slug": "creative-portfolio",
            "description": "Bold accent banner, two-column body with pill tags. Great for designers, marketers, and creatives.",
            "is_premium": False,
            "accent_color": "#7c3aed",
            "order": 4,
        },
        {
            "name": "Executive Classic",
            "slug": "executive-classic",
            "description": "Formal serif typography, centred header, double rule. Ideal for senior leadership and board-level roles.",
            "is_premium": False,
            "accent_color": "#1e3a5f",
            "order": 5,
        },
        {
            "name": "Tech Dark",
            "slug": "tech-dark",
            "description": "Dark background, monospace accents, code-comment section labels. Built for developers who want to stand out.",
            "is_premium": True,
            "accent_color": "#22d3ee",
            "order": 6,
        },
        {
            "name": "Two-Column Elegant",
            "slug": "two-column-elegant",
            "description": "Refined two-column layout with dot-bar skill ratings and thin-rule dividers. Polished and professional.",
            "is_premium": False,
            "accent_color": "#be185d",
            "order": 7,
        },
        {
            "name": "Academic & Research",
            "slug": "academic-research",
            "description": "Publications-first, dense, serif layout that mirrors standard academic CV conventions.",
            "is_premium": False,
            "accent_color": "#14532d",
            "order": 8,
        },
        {
            "name": "Bold Infographic",
            "slug": "bold-infographic",
            "description": "Dark header band, photo support, animated-style skill bars. High visual impact for competitive industries.",
            "is_premium": True,
            "accent_color": "#f59e0b",
            "order": 9,
        },
        {
            "name": "Compact One-Page",
            "slug": "compact-one-page",
            "description": "Tighter margins, smaller type, two-column — engineered to fit a complete career history onto a single A4 page.",
            "is_premium": False,
            "accent_color": "#0369a1",
            "order": 10,
        },
    ]
    for data in new_templates:
        Template.objects.update_or_create(slug=data["slug"], defaults=data)


def remove_templates(apps, schema_editor):
    Template = apps.get_model("resumes", "Template")
    Template.objects.filter(slug__in=[
        "creative-portfolio", "executive-classic", "tech-dark",
        "two-column-elegant", "academic-research", "bold-infographic", "compact-one-page",
    ]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("resumes", "0002_seed_templates"),
    ]
    operations = [
        migrations.RunPython(add_templates, remove_templates),
    ]
