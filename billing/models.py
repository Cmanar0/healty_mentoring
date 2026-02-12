"""
Billing models. Phase 3: Payment persistence from Stripe webhooks.
Stripe is the source of truth; we persist payment state for reporting and idempotency.
"""
from django.db import models


class Payment(models.Model):
    """One row per Stripe PaymentIntent; updated by webhooks (idempotent)."""

    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)

    mentor = models.ForeignKey(
        "accounts.MentorProfile",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    client = models.ForeignKey(
        "accounts.UserProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payments",
    )

    session = models.ForeignKey(
        "general.Session",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )

    amount_cents = models.IntegerField()
    currency = models.CharField(max_length=10, default="usd")

    platform_commission_cents = models.IntegerField()

    status = models.CharField(max_length=50)  # succeeded, failed

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.stripe_payment_intent_id} ({self.status})"
