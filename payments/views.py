"""
Stripe payment integration for SmartCV Builder.

Flow:
  1. User clicks "Upgrade to Premium" → POST /payments/checkout/ →
     creates a Stripe Checkout Session → redirects to Stripe's hosted page.
  2. Stripe redirects back to /payments/success/ or /payments/cancel/.
  3. Stripe webhook (POST /payments/webhook/) delivers payment events;
     checkout.session.completed flips profile.plan = "premium".

Environment variables required (see README):
  STRIPE_SECRET_KEY       — sk_test_… or sk_live_…
  STRIPE_PUBLISHABLE_KEY  — pk_test_… or pk_live_…
  STRIPE_WEBHOOK_SECRET   — whsec_… from Stripe dashboard or `stripe listen`
  STRIPE_PREMIUM_PRICE_ID — price_… for the Premium subscription/one-time product
"""
import json
import logging

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


def _stripe_client():
    key = settings.STRIPE_SECRET_KEY
    if not key:
        raise ValueError(
            "STRIPE_SECRET_KEY is not configured. Add it to your environment."
        )
    stripe.api_key = key
    return stripe


# ---------------------------------------------------------------------------
# Checkout: create Stripe session, redirect user to hosted payment page
# ---------------------------------------------------------------------------
@login_required
@require_POST
def create_checkout_session(request):
    try:
        s = _stripe_client()
        price_id = settings.STRIPE_PREMIUM_PRICE_ID
        if not price_id:
            messages.error(request, "Payments are not configured yet — check back soon!")
            return redirect("resumes:dashboard")

        session = s.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",   # Change to "payment" for one-time purchase
            customer_email=request.user.email,
            client_reference_id=str(request.user.pk),
            success_url=request.build_absolute_uri("/payments/success/")
                        + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri("/payments/cancel/"),
        )
        return redirect(session.url, permanent=False)

    except Exception as exc:
        logger.exception("Stripe checkout error: %s", exc)
        messages.error(request, "Payment session could not be created. Please try again.")
        return redirect("resumes:dashboard")


# ---------------------------------------------------------------------------
# Success / cancel redirect pages
# ---------------------------------------------------------------------------
@login_required
def checkout_success(request):
    # The webhook (below) is the authoritative source of truth for updating
    # the plan; this page just shows a friendly confirmation.
    return render(request, "payments/success.html")


@login_required
def checkout_cancel(request):
    messages.info(request, "Upgrade cancelled. You're still on the Free plan.")
    return redirect("resumes:dashboard")


# ---------------------------------------------------------------------------
# Subscription management: let premium users see/cancel their sub
# ---------------------------------------------------------------------------
@login_required
def subscription(request):
    profile = request.user.profile
    stripe_sub = None
    portal_url = None

    if profile.is_premium and profile.stripe_customer_id:
        try:
            s = _stripe_client()
            # Redirect to Stripe Customer Portal for self-service management
            portal = s.billing_portal.Session.create(
                customer=profile.stripe_customer_id,
                return_url=request.build_absolute_uri("/payments/subscription/"),
            )
            portal_url = portal.url
            # Fetch active subscription details for display
            subs = s.Subscription.list(
                customer=profile.stripe_customer_id, status="active", limit=1
            )
            if subs.data:
                stripe_sub = subs.data[0]
        except Exception as exc:
            logger.warning("Could not fetch Stripe subscription: %s", exc)

    return render(request, "payments/subscription.html", {
        "profile": profile,
        "stripe_sub": stripe_sub,
        "portal_url": portal_url,
        "stripe_pk": settings.STRIPE_PUBLISHABLE_KEY,
    })


# ---------------------------------------------------------------------------
# Stripe Webhook — must be csrf_exempt (Stripe signs with its own secret)
# ---------------------------------------------------------------------------
@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if not webhook_secret:
        logger.warning("STRIPE_WEBHOOK_SECRET not set — skipping signature verification.")
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return HttpResponse(status=400)
    else:
        try:
            s = _stripe_client()
            event = s.Webhook.construct_event(payload, sig_header, webhook_secret)
        except stripe.error.SignatureVerificationError:
            logger.warning("Stripe webhook signature verification failed.")
            return HttpResponse(status=400)

    event_type = event.get("type") if isinstance(event, dict) else event["type"]
    data_obj = (event["data"]["object"] if isinstance(event, dict)
                else event.data.object)

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data_obj)

    elif event_type in ("customer.subscription.deleted",
                        "customer.subscription.updated"):
        _handle_subscription_change(data_obj)

    return HttpResponse(status=200)


# ---------------------------------------------------------------------------
# Private webhook handlers
# ---------------------------------------------------------------------------
def _handle_checkout_completed(session):
    """Flip the user's plan to premium on successful checkout."""
    user_id = session.get("client_reference_id")
    customer_id = session.get("customer")
    if not user_id:
        logger.warning("checkout.session.completed missing client_reference_id")
        return
    try:
        user = User.objects.get(pk=user_id)
        user.profile.plan = "premium"
        user.profile.stripe_customer_id = customer_id
        user.profile.save(update_fields=["plan", "stripe_customer_id"])
        logger.info("Upgraded user %s to premium (Stripe customer %s)", user_id, customer_id)
    except User.DoesNotExist:
        logger.error("checkout.session.completed: user %s not found", user_id)


def _handle_subscription_change(sub):
    """Downgrade user if their subscription is cancelled or expires."""
    customer_id = sub.get("customer") if isinstance(sub, dict) else sub["customer"]
    status = sub.get("status") if isinstance(sub, dict) else sub["status"]
    if status in ("canceled", "unpaid", "past_due"):
        from accounts.models import Profile
        updated = Profile.objects.filter(stripe_customer_id=customer_id).update(plan="free")
        if updated:
            logger.info("Downgraded customer %s to free (sub status: %s)", customer_id, status)
