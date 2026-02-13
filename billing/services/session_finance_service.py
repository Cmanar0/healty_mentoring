"""
Centralized cancellation/refund/payout lifecycle rules (Phase 5).
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from billing import config
from billing.services.wallet_service import add_credit
from billing.services.mentor_wallet_service import credit_mentor, deduct_mentor, MentorWalletError
from general.models import Session


class CancellationError(Exception):
    pass


class RefundError(Exception):
    pass


class PayoutError(Exception):
    pass


def _session_amount_cents(session) -> int:
    return int(round(float(getattr(session, "session_price", 0) or 0) * 100))


def _get_client_profile(session):
    client_user = session.attendees.first()
    if not client_user:
        return None, None
    profile = getattr(client_user, "user_profile", None) or getattr(client_user, "profile", None)
    return client_user, profile


@transaction.atomic()
def cancel_session_with_refund(session, now=None):
    now = now or timezone.now()
    session = Session.objects.select_for_update().select_related("payment", "created_by").get(id=session.id)
    if session.status not in ("invited", "confirmed"):
        raise CancellationError("Only invited/confirmed sessions can be cancelled.")
    deadline = session.start_datetime - timedelta(hours=config.SESSION_CANCELLATION_WINDOW_HOURS)
    if now > deadline:
        raise CancellationError("Cancellation window has passed.")

    amount_cents = _session_amount_cents(session)
    payment = getattr(session, "payment", None)
    if amount_cents > 0:
        _, client_profile = _get_client_profile(session)
        if not client_profile:
            raise CancellationError("Cannot find client profile for refund.")
        add_credit(
            client_profile,
            amount_cents,
            reason="cancellation_refund",
            related_payment=payment,
            related_session=session,
        )
        if payment:
            payment.status = "refunded"
            payment.save(update_fields=["status"])
        session.refunded_at = now

    session.status = "cancelled"
    session.save(update_fields=["status", "refunded_at"] if amount_cents > 0 else ["status"])
    return amount_cents


@transaction.atomic()
def decline_invitation(session, now=None):
    """
    Decline an invitation (status='invited') without cancellation window restriction.
    This is different from cancel_session_with_refund which is for confirmed sessions
    that need refunds and have cancellation window restrictions.
    """
    now = now or timezone.now()
    session = Session.objects.select_for_update().select_related("payment", "created_by").get(id=session.id)
    if session.status != "invited":
        raise CancellationError("Only invited sessions can be declined via this function.")
    
    # No cancellation window check - invitations can always be declined
    # No refund needed since payment hasn't been made yet for invited sessions
    session.status = "cancelled"
    session.save(update_fields=["status"])
    return 0


@transaction.atomic()
def refund_completed_session(session, now=None):
    now = now or timezone.now()
    session = Session.objects.select_for_update().select_related("payment", "created_by").get(id=session.id)
    if session.status in ("payout_available", "paid_out", "refunded"):
        raise RefundError("Cannot refund a payout-available or paid-out session.")
    if session.status != "completed":
        raise RefundError("Only completed sessions can be refunded.")
    refund_deadline = session.end_datetime + timedelta(days=config.SESSION_REFUND_WINDOW_DAYS)
    if now > refund_deadline:
        raise RefundError("Refund window has passed.")

    amount_cents = _session_amount_cents(session)
    payment = getattr(session, "payment", None)
    if amount_cents > 0:
        _, client_profile = _get_client_profile(session)
        if not client_profile:
            raise RefundError("Cannot find client profile for refund.")
        add_credit(
            client_profile,
            amount_cents,
            reason="refund",
            related_payment=payment,
            related_session=session,
        )
        if payment:
            payment.status = "refunded"
            payment.save(update_fields=["status"])

    session.status = "refunded"
    session.refunded_at = now
    session.save(update_fields=["status", "refunded_at"])
    return amount_cents


@transaction.atomic()
def mark_session_payout_available(session, now=None):
    now = now or timezone.now()
    session = Session.objects.select_for_update().select_related("payment", "created_by").get(id=session.id)
    if session.status != "completed":
        return 0
    eligible_at = session.end_datetime + timedelta(days=config.SESSION_REFUND_WINDOW_DAYS)
    if now < eligible_at:
        return 0
    payment = getattr(session, "payment", None)
    mentor_user = getattr(session, "created_by", None)
    mentor_profile = getattr(mentor_user, "mentor_profile", None) if mentor_user else None

    mentor_amount = 0
    # Critical ordering: status transition before wallet credit.
    session.status = "payout_available"
    session.save(update_fields=["status"])

    if payment and mentor_profile:
        # Idempotency: avoid double-crediting if cleanup runs multiple times.
        from billing.models import MentorWalletTransaction
        already_credited = MentorWalletTransaction.objects.filter(
            related_session=session,
            reason="payout_available",
        ).exists()
        mentor_amount = int((payment.amount_cents or 0) - (payment.platform_commission_cents or 0))
        if mentor_amount < 0:
            mentor_amount = 0
        if mentor_amount > 0 and not already_credited:
            credit_mentor(
                mentor_profile,
                mentor_amount,
                reason="payout_available",
                related_payment=payment,
                related_session=session,
            )
    return mentor_amount


@transaction.atomic()
def withdraw_session_payout(session, mentor_profile, now=None):
    now = now or timezone.now()
    session = Session.objects.select_for_update().select_related("payment", "created_by").get(id=session.id)
    if session.status != "payout_available":
        raise PayoutError("Only payout_available sessions can be withdrawn.")
    if not mentor_profile or session.created_by_id != mentor_profile.user_id:
        raise PayoutError("Not authorized for this session payout.")
    payment = getattr(session, "payment", None)
    if not payment:
        raise PayoutError("No payment found for this session.")
    amount_cents = int((payment.amount_cents or 0) - (payment.platform_commission_cents or 0))
    if amount_cents <= 0:
        raise PayoutError("No payout amount available.")
    try:
        deduct_mentor(
            mentor_profile,
            amount_cents,
            reason="payout_withdrawal",
            related_payment=payment,
            related_session=session,
        )
    except MentorWalletError as e:
        raise PayoutError(str(e))
    session.status = "paid_out"
    session.paid_out_at = now
    session.save(update_fields=["status", "paid_out_at"])
    return amount_cents
