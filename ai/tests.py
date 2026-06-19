import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from resumes.models import Resume, Skill, PersonalInfo


def _make_openai_response(text: str):
    """Build a minimal mock openai ChatCompletion response."""
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@override_settings(AI_PROVIDER="openai", OPENAI_API_KEY="test-key")
class AIServiceUnitTests(TestCase):
    """Test the service functions with OpenAI mocked out."""

    @patch("ai.services._client")
    def test_rewrite_summary_returns_text(self, mock_client_fn):
        client_mock = MagicMock()
        client_mock.chat.completions.create.return_value = _make_openai_response(
            "Experienced engineer driving impact at scale."
        )
        mock_client_fn.return_value = client_mock

        from ai.services import rewrite_summary
        result = rewrite_summary("Old summary", "Backend Engineer", ["Django", "Python"])
        self.assertIn("engineer", result.lower())

    @patch("ai.services._client")
    def test_analyze_resume_returns_dict(self, mock_client_fn):
        payload = json.dumps({
            "score": 78,
            "strengths": ["Strong experience", "Good skill variety"],
            "improvements": ["Add more projects"],
            "ats_tips": ["Use plain section headings"],
        })
        client_mock = MagicMock()
        client_mock.chat.completions.create.return_value = _make_openai_response(payload)
        mock_client_fn.return_value = client_mock

        from ai.services import analyze_resume
        result = analyze_resume({"title": "Test CV", "summary": "", "experience_count": 2,
                                  "education_count": 1, "skill_count": 3, "sections_present": []})
        self.assertEqual(result["score"], 78)
        self.assertIn("strengths", result)

    @patch("ai.services._client")
    def test_career_suggestions_returns_list(self, mock_client_fn):
        client_mock = MagicMock()
        client_mock.chat.completions.create.return_value = _make_openai_response(
            '["Learn Kubernetes", "Contribute to open source", "Get AWS cert", "Start a blog"]'
        )
        mock_client_fn.return_value = client_mock

        from ai.services import career_suggestions
        result = career_suggestions("Backend Engineer", ["Django"], 5)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    @patch("ai.services._client")
    def test_improve_bullet_returns_string(self, mock_client_fn):
        client_mock = MagicMock()
        client_mock.chat.completions.create.return_value = _make_openai_response(
            "Reduced API latency by 40% through targeted query optimisation and Redis caching."
        )
        mock_client_fn.return_value = client_mock

        from ai.services import improve_bullet
        result = improve_bullet("Made the API faster", "Backend Engineer")
        self.assertIn("latency", result.lower())

    def test_missing_api_key_raises_error(self):
        from ai.services import AIServiceError, rewrite_summary
        with self.settings(AI_PROVIDER="openai", OPENAI_API_KEY=""):
            with self.assertRaises(AIServiceError):
                rewrite_summary("summary", "Title", [])

    @override_settings(
        AI_PROVIDER="zai",
        ZAI_API_KEY="test-key",
        ZAI_AI_MODEL="glm-5.2",
        ZAI_AI_ENDPOINT="https://api.z.ai/api/paas/v4/chat/completions",
    )
    @patch("requests.post")
    def test_zai_uses_configured_chat_completions_endpoint(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "choices": [{"message": {"content": "ZAI response text"}}],
        }
        mock_post.return_value = response

        from ai.services import rewrite_summary

        result = rewrite_summary("Old summary", "Backend Engineer", ["Django"])

        self.assertEqual(result, "ZAI response text")
        mock_post.assert_called_once()
        self.assertEqual(
            mock_post.call_args.args[0],
            "https://api.z.ai/api/paas/v4/chat/completions",
        )

    @patch("ai.services._client")
    def test_field_suggestions_returns_insertable_items(self, mock_client_fn):
        client_mock = MagicMock()
        client_mock.chat.completions.create.return_value = _make_openai_response(
            '[{"label": "Python", "value": "Python"}, {"label": "Django", "value": "Django"}]'
        )
        mock_client_fn.return_value = client_mock

        from ai.services import field_suggestions

        result = field_suggestions("skills", "Backend Engineer")

        self.assertEqual(result[0]["value"], "Python")
        self.assertEqual(result[1]["label"], "Django")


@override_settings(AI_PROVIDER="openai", OPENAI_API_KEY="test-key")
class AIViewTests(TestCase):
    """Test the AJAX view endpoints with OpenAI mocked."""

    def setUp(self):
        self.user = User.objects.create_user(username="ai_user", password="pass12345")
        self.client.login(username="ai_user", password="pass12345")
        self.client.post(reverse("resumes:create"))
        self.resume = Resume.objects.get(user=self.user)
        PersonalInfo.objects.filter(resume=self.resume).update(
            full_name="AI Tester", professional_title="Engineer"
        )
        Skill.objects.create(resume=self.resume, name="Python")

    @patch("ai.services._client")
    def test_rewrite_summary_endpoint(self, mock_client_fn):
        client_mock = MagicMock()
        client_mock.chat.completions.create.return_value = _make_openai_response(
            "A polished professional summary."
        )
        mock_client_fn.return_value = client_mock

        resp = self.client.post(reverse("ai:rewrite_summary", args=[self.resume.pk]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertIn("text", data)

    @patch("ai.services._client")
    def test_analyze_endpoint(self, mock_client_fn):
        payload = json.dumps({"score": 65, "strengths": ["Good"], "improvements": ["Add more"],
                               "ats_tips": ["Plain headings"]})
        client_mock = MagicMock()
        client_mock.chat.completions.create.return_value = _make_openai_response(payload)
        mock_client_fn.return_value = client_mock

        resp = self.client.post(reverse("ai:analyze", args=[self.resume.pk]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertIn("score", data)

    @patch("ai.services._client")
    def test_career_suggestions_endpoint(self, mock_client_fn):
        client_mock = MagicMock()
        client_mock.chat.completions.create.return_value = _make_openai_response(
            '["Learn Docker", "Build a side project"]'
        )
        mock_client_fn.return_value = client_mock

        resp = self.client.post(reverse("ai:career_suggestions", args=[self.resume.pk]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertIsInstance(data["suggestions"], list)

    @patch("ai.services._client")
    def test_improve_bullet_endpoint(self, mock_client_fn):
        import json as _json
        client_mock = MagicMock()
        client_mock.chat.completions.create.return_value = _make_openai_response(
            "Optimised API response time by 40% using Redis caching."
        )
        mock_client_fn.return_value = client_mock

        resp = self.client.post(
            reverse("ai:improve_bullet", args=[self.resume.pk]),
            data=_json.dumps({"bullet": "Made things faster", "job_title": "Backend Engineer"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertIn("improved", data)

    @patch("ai.views.field_suggestions")
    def test_field_suggestions_endpoint(self, mock_suggestions):
        mock_suggestions.return_value = [
            {"label": "Summary option", "value": "A focused backend engineer."}
        ]

        resp = self.client.post(
            reverse("ai:field_suggestions", args=[self.resume.pk]),
            data=json.dumps({"field_type": "summary", "current_value": ""}),
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["suggestions"][0]["value"], "A focused backend engineer.")

    def test_field_suggestions_bad_json_returns_400(self):
        resp = self.client.post(
            reverse("ai:field_suggestions", args=[self.resume.pk]),
            data="not json",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 400)

    def test_improve_bullet_missing_body_returns_400(self):
        resp = self.client.post(
            reverse("ai:improve_bullet", args=[self.resume.pk]),
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_ai_endpoint_requires_login(self):
        self.client.logout()
        resp = self.client.post(reverse("ai:rewrite_summary", args=[self.resume.pk]))
        self.assertEqual(resp.status_code, 302)  # redirect to login

    def test_ai_endpoint_owner_only(self):
        other = User.objects.create_user(username="other_ai_user", password="pass12345")
        other_client = self.client_class()
        other_client.login(username="other_ai_user", password="pass12345")
        resp = other_client.post(reverse("ai:rewrite_summary", args=[self.resume.pk]))
        self.assertEqual(resp.status_code, 404)
