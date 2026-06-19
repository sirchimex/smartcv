from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    """Extends the built-in User with plan/role info.

    NOTE: Payment processing (Stripe/Paystack/Flutterwave) is intentionally
    NOT wired up yet. `plan` can be changed by an admin in /admin/ for now;
    a real checkout flow is a follow-up phase once payment provider keys
    are available.
    """

    FREE = "free"
    PREMIUM = "premium"
    PLAN_CHOICES = [(FREE, "Free"), (PREMIUM, "Premium")]

    ADMIN = "admin"
    USER = "user"
    ROLE_CHOICES = [(ADMIN, "Admin"), (USER, "User")]

    FREE_PLAN_RESUME_LIMIT = 2

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default=FREE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=USER)
    stripe_customer_id = models.CharField(
        max_length=50, blank=True,
        help_text="Stripe customer ID — set automatically on first successful payment."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.plan})"

    @property
    def is_premium(self):
        return self.plan == self.PREMIUM or self.user.is_superuser

    def resume_limit_reached(self, current_count):
        if self.is_premium:
            return False
        return current_count >= self.FREE_PLAN_RESUME_LIMIT


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)
