from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("checkout/",     views.create_checkout_session, name="checkout"),
    path("success/",      views.checkout_success,        name="success"),
    path("cancel/",       views.checkout_cancel,         name="cancel"),
    path("subscription/", views.subscription,            name="subscription"),
    path("webhook/",      views.stripe_webhook,          name="webhook"),
]
