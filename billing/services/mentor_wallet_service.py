"""
Mentor wallet service. All mentor wallet changes go through this module.
Never modify mentor wallet_balance_cents directly outside this service.
"""
from django.db import transaction

from accounts.models import MentorProfile
from billing.models import MentorWalletTransaction


class MentorWalletError(Exception):
    pass


@transaction.atomic()
def credit_mentor(
    mentor_profile: MentorProfile,
    amount_cents: int,
    reason: str,
    related_payment=None,
    related_session=None,
) -> None:
    if amount_cents <= 0:
        raise MentorWalletError("credit_mentor requires positive amount_cents")
    MentorWalletTransaction.objects.create(
        mentor=mentor_profile,
        amount_cents=amount_cents,
        reason=reason[:100],
        related_payment=related_payment,
        related_session=related_session,
    )
    mentor_profile.refresh_from_db()
    mentor_profile.wallet_balance_cents = (mentor_profile.wallet_balance_cents or 0) + amount_cents
    mentor_profile.save(update_fields=["wallet_balance_cents"])


@transaction.atomic()
def deduct_mentor(
    mentor_profile: MentorProfile,
    amount_cents: int,
    reason: str,
    related_payment=None,
    related_session=None,
) -> None:
    if amount_cents <= 0:
        raise MentorWalletError("deduct_mentor requires positive amount_cents")
    mentor_profile.refresh_from_db()
    balance = mentor_profile.wallet_balance_cents or 0
    if balance < amount_cents:
        raise MentorWalletError("Insufficient mentor wallet balance.")
    MentorWalletTransaction.objects.create(
        mentor=mentor_profile,
        amount_cents=-amount_cents,
        reason=reason[:100],
        related_payment=related_payment,
        related_session=related_session,
    )
    mentor_profile.wallet_balance_cents = balance - amount_cents
    mentor_profile.save(update_fields=["wallet_balance_cents"])
