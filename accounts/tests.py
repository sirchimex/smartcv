from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class ProfileSignalTests(TestCase):
    def test_profile_auto_created_for_new_user(self):
        user = User.objects.create_user(username="alex", password="pass12345")
        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(user.profile.plan, "free")

    def test_free_plan_resume_limit(self):
        user = User.objects.create_user(username="sam", password="pass12345")
        profile = user.profile
        self.assertFalse(profile.resume_limit_reached(0))
        self.assertFalse(profile.resume_limit_reached(1))
        self.assertTrue(profile.resume_limit_reached(2))

    def test_premium_has_no_limit(self):
        user = User.objects.create_user(username="taylor", password="pass12345")
        user.profile.plan = "premium"
        user.profile.save()
        self.assertFalse(user.profile.resume_limit_reached(999))


class RegistrationViewTests(TestCase):
    def test_register_creates_user_and_logs_in(self):
        resp = self.client.post(reverse("accounts:register"), {
            "username": "newperson",
            "email": "newperson@example.com",
            "password1": "SuperSecret123!",
            "password2": "SuperSecret123!",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(username="newperson").exists())
        # logged in automatically -> dashboard should be reachable without a login redirect
        dashboard = self.client.get(reverse("resumes:dashboard"))
        self.assertEqual(dashboard.status_code, 200)

    def test_duplicate_email_rejected(self):
        User.objects.create_user(username="existing", email="dup@example.com", password="pass12345")
        resp = self.client.post(reverse("accounts:register"), {
            "username": "another",
            "email": "dup@example.com",
            "password1": "SuperSecret123!",
            "password2": "SuperSecret123!",
        })
        self.assertEqual(resp.status_code, 200)  # form re-rendered with error
        self.assertFalse(User.objects.filter(username="another").exists())
