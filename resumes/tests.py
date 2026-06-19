from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Experience, PersonalInfo, Resume, Skill, Template


class ResumeModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="modeluser", password="pass12345")
        self.template = Template.objects.first()

    def test_completion_percentage_increases_as_sections_fill(self):
        resume = Resume.objects.create(user=self.user, title="Test CV", template=self.template)
        self.assertEqual(resume.completion_percentage(), 0)

        PersonalInfo.objects.create(resume=resume, full_name="Test Person")
        self.assertGreater(resume.completion_percentage(), 0)

        resume.professional_summary = "A summary."
        resume.save()
        Experience.objects.create(
            resume=resume, job_title="Engineer", company="Acme",
            start_date="2020-01-01",
        )
        Skill.objects.create(resume=resume, name="Python")
        # 4 of 5 checks true (personal_info, summary, experience, skills) - missing education
        self.assertEqual(resume.completion_percentage(), 80)

    def test_accent_falls_back_to_template_color(self):
        resume = Resume.objects.create(user=self.user, title="Test CV", template=self.template)
        self.assertEqual(resume.accent, self.template.accent_color)
        resume.theme_color = "#123456"
        resume.save()
        self.assertEqual(resume.accent, "#123456")


class ResumeCRUDViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="crud_user", password="pass12345")
        self.client.login(username="crud_user", password="pass12345")

    def test_create_then_dashboard_shows_it(self):
        resp = self.client.post(reverse("resumes:create"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Resume.objects.filter(user=self.user).count(), 1)

        dashboard = self.client.get(reverse("resumes:dashboard"))
        self.assertContains(dashboard, "Untitled CV")

    def test_free_plan_limit_enforced(self):
        for _ in range(self.user.profile.FREE_PLAN_RESUME_LIMIT):
            self.client.post(reverse("resumes:create"))
        self.assertEqual(
            Resume.objects.filter(user=self.user).count(),
            self.user.profile.FREE_PLAN_RESUME_LIMIT,
        )
        # one more attempt should be blocked
        self.client.post(reverse("resumes:create"))
        self.assertEqual(
            Resume.objects.filter(user=self.user).count(),
            self.user.profile.FREE_PLAN_RESUME_LIMIT,
        )

    def test_owner_only_access(self):
        self.client.post(reverse("resumes:create"))
        resume = Resume.objects.get(user=self.user)

        other = User.objects.create_user(username="other_user", password="pass12345")
        other_client = self.client_class()
        other_client.login(username="other_user", password="pass12345")
        resp = other_client.get(reverse("resumes:builder", args=[resume.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_section_item_crud(self):
        self.client.post(reverse("resumes:create"))
        resume = Resume.objects.get(user=self.user)

        resp = self.client.post(
            reverse("resumes:section_add", args=[resume.pk, "skills"]),
            {"name": "Django", "category": "technical", "level": 4},
        )
        self.assertEqual(resp.status_code, 302)
        skill = Skill.objects.get(resume=resume)
        self.assertEqual(skill.name, "Django")

        resp = self.client.post(
            reverse("resumes:section_edit", args=[resume.pk, "skills", skill.pk]),
            {"name": "Django (Advanced)", "category": "technical", "level": 5},
        )
        self.assertEqual(resp.status_code, 302)
        skill.refresh_from_db()
        self.assertEqual(skill.name, "Django (Advanced)")

        resp = self.client.post(
            reverse("resumes:section_delete", args=[resume.pk, "skills", skill.pk])
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Skill.objects.filter(pk=skill.pk).exists())


class TemplateRenderingTests(TestCase):
    """Renders each of the 3 layouts with a fully populated resume to catch
    template errors. Does not invoke WeasyPrint here (see PdfExportTests)."""

    def setUp(self):
        self.user = User.objects.create_user(username="render_user", password="pass12345")
        self.client.login(username="render_user", password="pass12345")
        self.client.post(reverse("resumes:create"))
        self.resume = Resume.objects.get(user=self.user)
        PersonalInfo.objects.filter(resume=self.resume).update(full_name="Render Test")
        Experience.objects.create(
            resume=self.resume, job_title="Engineer", company="Acme", start_date="2020-01-01"
        )
        Skill.objects.create(resume=self.resume, name="Testing")

    def test_all_three_layouts_render(self):
        for slug in ["modern-corporate", "minimalist", "ats-friendly-resume"]:
            template = Template.objects.get(slug=slug)
            self.resume.template = template
            self.resume.save()
            resp = self.client.get(reverse("resumes:preview", args=[self.resume.pk]))
            self.assertEqual(resp.status_code, 200, f"{slug} failed to render")
            self.assertContains(resp, "Render Test")
            self.assertContains(resp, "Acme")


class PdfExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="pdf_user", password="pass12345")
        self.client.login(username="pdf_user", password="pass12345")
        self.client.post(reverse("resumes:create"))
        self.resume = Resume.objects.get(user=self.user)

    def test_pdf_download_returns_pdf_and_logs_history(self):
        resp = self.client.get(reverse("resumes:pdf", args=[self.resume.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertGreater(len(resp.content), 500)
        self.assertEqual(self.user.downloads.count(), 1)


class AllTenTemplateRenderTests(TestCase):
    """Render every template slug, confirm name appears and no 500."""

    ALL_SLUGS = [
        "modern-corporate", "minimalist", "ats-friendly-resume",
        "creative-portfolio", "executive-classic", "tech-dark",
        "two-column-elegant", "academic-research", "bold-infographic",
        "compact-one-page",
    ]

    def setUp(self):
        self.user = User.objects.create_user(username="all_tpl_user", password="pass12345")
        self.client.login(username="all_tpl_user", password="pass12345")
        self.client.post(reverse("resumes:create"))
        self.resume = Resume.objects.get(user=self.user)
        from resumes.models import PersonalInfo
        PersonalInfo.objects.filter(resume=self.resume).update(
            full_name="Test Person", professional_title="Test Role"
        )

    def test_all_templates_render_without_error(self):
        for slug in self.ALL_SLUGS:
            template = Template.objects.get(slug=slug)
            self.resume.template = template
            self.resume.save()
            resp = self.client.get(reverse("resumes:preview", args=[self.resume.pk]))
            self.assertEqual(resp.status_code, 200, f"{slug} returned {resp.status_code}")
            self.assertContains(resp, "Test Person", msg_prefix=f"{slug}: ")


class AllTenTemplatePdfTests(TestCase):
    """PDF export works for all 10 template slugs."""

    ALL_SLUGS = [
        "modern-corporate", "minimalist", "ats-friendly-resume",
        "creative-portfolio", "executive-classic", "tech-dark",
        "two-column-elegant", "academic-research", "bold-infographic",
        "compact-one-page",
    ]

    def setUp(self):
        self.user = User.objects.create_user(username="pdf10_user", password="pass12345")
        self.client.login(username="pdf10_user", password="pass12345")
        self.client.post(reverse("resumes:create"))
        self.resume = Resume.objects.get(user=self.user)

    def test_all_templates_produce_valid_pdf(self):
        for slug in self.ALL_SLUGS:
            template = Template.objects.get(slug=slug)
            self.resume.template = template
            self.resume.save()
            resp = self.client.get(reverse("resumes:pdf", args=[self.resume.pk]))
            self.assertEqual(resp.status_code, 200, f"{slug} PDF failed")
            self.assertEqual(resp["Content-Type"], "application/pdf", slug)
            self.assertGreater(len(resp.content), 500, f"{slug} PDF too small")
