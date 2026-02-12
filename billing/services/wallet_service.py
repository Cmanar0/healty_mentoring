"""
Client wallet service. All balance changes go through here and create a WalletTransaction.
Never modify wallet_balance_cents outside this module.
"""
from django.db import transaction

from accounts.models import UserProfile
from billing.models import WalletTransaction


class WalletError(Exception):
    """Raised when wallet operation fails (e.g. insufficient balance)."""
    pass


@transaction.atomic()
def add_credit(
    user_profile: UserProfile,
    amount_cents: int,
    reason: str,
    related_payment=None,
    related_session=None,
) -> None:
    """
    Add credit to wallet. Creates WalletTransaction (positive amount), increases balance.
    """
    if amount_cents <= 0:
        raise WalletError("add_credit requires positive amount_cents")
    WalletTransaction.objects.create(
        user=user_profile,
        amount_cents=amount_cents,
        reason=reason[:100],
        related_payment=related_payment,
        related_session=related_session,
    )
    user_profile.refresh_from_db()
    user_profile.wallet_balance_cents = (user_profile.wallet_balance_cents or 0) + amount_cents
    user_profile.save(update_fields=["wallet_balance_cents"])


@transaction.atomic()
def deduct_credit(
    user_profile: UserProfile,
    amount_cents: int,
    reason: str,
    related_session=None,
    related_payment=None,
) -> None:
    """
    Deduct credit from wallet. Checks sufficient balance; creates WalletTransaction (negative amount).
    Raises WalletError if insufficient balance.
    """
    if amount_cents <= 0:
        raise WalletError("deduct_credit requires positive amount_cents")
    user_profile.refresh_from_db()
    balance = user_profile.wallet_balance_cents or 0
    if balance < amount_cents:
        raise WalletError("Insufficient wallet balance.")
    WalletTransaction.objects.create(
        user=user_profile,
        amount_cents=-amount_cents,
        reason=reason[:100],
        related_payment=related_payment,
        related_session=related_session,
    )
    user_profile.wallet_balance_cents = balance - amount_cents
    user_profile.save(update_fields=["wallet_balance_cents"])


def refund_credit(
    user_profile: UserProfile,
    amount_cents: int,
    reason: str = "refund",
    related_payment=None,
    related_session=None,
) -> None:
    """Same as add_credit with reason='refund'. Restores wallet after refund."""
    add_credit(
        user_profile=user_profile,
        amount_cents=amount_cents,
        reason=reason[:100],
        related_payment=related_payment,
        related_session=related_session,
    )
