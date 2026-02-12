"""
Billing views. Phase 1: Stripe status. Phase 3: Stripe webhook.
"""
import logging

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings

from billing.services.stripe_service import is_configured, check_api_ok

logger = logging.getLogger(__name__)


@staff_member_required
def stripe_status(request):
    """
    GET /api/billing/stripe-status/
    Staff-only. Returns JSON: stripe_configured, api_ok (optional Stripe API check).
    """
    return JsonResponse({
        "stripe_configured": is_configured(),
        "api_ok": check_api_ok() if is_configured() else False,
    })


@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    """
    POST /api/billing/stripe-webhook/
    Stripe webhook endpoint. Verifies signature, handles payment_intent.succeeded
    and payment_intent.payment_failed. Idempotent (update_or_create by pi_id).
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE") or request.META.get("Stripe-Signature", "")
    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "") or ""

    if not webhook_secret or not sig_header:
        logger.warning("stripe_webhook: missing STRIPE_WEBHOOK_SECRET or Stripe-Signature header")
        return HttpResponse(status=400)

    try:
        import stripe
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError as e:
        logger.warning("stripe_webhook: invalid payload %s", e)
        return HttpResponse(status=400)
    except Exception as e:
        logger.warning("stripe_webhook: signature verification failed %s", e)
        return HttpResponse(status=400)

    if event.type == "payment_intent.succeeded":
        _handle_payment_intent_succeeded(event.data.object)
    elif event.type == "payment_intent.payment_failed":
        _handle_payment_intent_failed(event.data.object)
    elif event.type == "charge.refunded":
        _handle_charge_refunded(event.data.object)
    else:
        pass  # ignore other events

    return HttpResponse(status=200)


def _handle_payment_intent_succeeded(obj):
    """Create or update Payment row for succeeded PaymentIntent. Idempotent. Branches by payment_type."""
    from billing.models import Payment
    from billing import config
    from billing.services.wallet_service import add_credit
    from accounts.models import MentorProfile, UserProfile

    pi_id = obj.get("id")
    if not pi_id:
        return
    amount_cents = obj.get("amount") or 0
    currency = (obj.get("currency") or "usd").lower()[:10]
    metadata = obj.get("metadata") or {}
    payment_type = metadata.get("payment_type") or ""

    if payment_type == "wallet_topup":
        client_id_raw = metadata.get("client_id")
        if not client_id_raw:
            logger.warning("stripe_webhook: wallet_topup missing metadata.client_id pi=%s", pi_id)
            return
        try:
            client = UserProfile.objects.get(id=int(client_id_raw))
        except (ValueError, TypeError, UserProfile.DoesNotExist):
            logger.warning("stripe_webhook: UserProfile not found for client_id=%s pi=%s", client_id_raw, pi_id)
            return
        platform_commission_cents = int(metadata.get("platform_commission_cents") or 0)
        payment, _ = Payment.objects.update_or_create(
            stripe_payment_intent_id=pi_id,
            defaults={
                "mentor": None,
                "client": client,
                "amount_cents": amount_cents,
                "currency": currency,
                "platform_commission_cents": platform_commission_cents,
                "status": "succeeded",
            },
        )
        add_credit(client, amount_cents, "wallet_topup", related_payment=payment)
        logger.info("stripe_webhook: Payment wallet_topup pi=%s add_credit done", pi_id)
        # Notify user and send payment confirmation email
        try:
            from general.models import Notification
            import uuid
            amount_dollars = amount_cents / 100.0
            Notification.objects.create(
                user=client.user,
                batch_id=uuid.uuid4(),
                target_type='single',
                title='Wallet topped up',
                description=f'${amount_dollars:.2f} has been added to your wallet.',
            )
            from general.email_service import EmailService
            EmailService.send_payment_confirmation_email(
                client.user, amount_cents, 'wallet_topup', session=None, fail_silently=True
            )
        except Exception as e:
            logger.warning("stripe_webhook: wallet_topup notification/email failed: %s", e)
        return

    if payment_type == "session_accept":
        from general.models import Session
        session_id_raw = metadata.get("session_id")
        mentor_id = metadata.get("mentor_id")
        client_id_raw = metadata.get("client_id")
        if not session_id_raw or not mentor_id:
            logger.warning("stripe_webhook: session_accept missing session_id or mentor_id pi=%s", pi_id)
            return
        try:
            session = Session.objects.get(id=int(session_id_raw))
            mentor_profile = MentorProfile.objects.get(user_id=mentor_id)
        except (ValueError, TypeError, Session.DoesNotExist, MentorProfile.DoesNotExist):
            logger.warning("stripe_webhook: session_accept Session or Mentor not found pi=%s", pi_id)
            return
        client = None
        if client_id_raw:
            try:
                client = UserProfile.objects.filter(id=int(client_id_raw)).first()
            except (ValueError, TypeError):
                pass
        platform_commission_cents = int(metadata.get("platform_commission_cents") or 0)
        if platform_commission_cents <= 0:
            platform_commission_cents = int(round(amount_cents * config.PLATFORM_COMMISSION_PERCENT))
        Payment.objects.update_or_create(
            stripe_payment_intent_id=pi_id,
            defaults={
                "mentor": mentor_profile,
                "client": client,
                "session": session,
                "amount_cents": amount_cents,
                "currency": currency,
                "platform_commission_cents": platform_commission_cents,
                "status": "succeeded",
            },
        )
        logger.info("stripe_webhook: Payment session_accept pi=%s session=%s", pi_id, session_id_raw)
        return

    # Session booking flow
    mentor_id = metadata.get("mentor_id")
    client_id_raw = metadata.get("client_id")
    if not mentor_id:
        logger.warning("stripe_webhook: payment_intent.succeeded missing metadata.mentor_id pi=%s", pi_id)
        return
    try:
        mentor_profile = MentorProfile.objects.get(user_id=mentor_id)
    except MentorProfile.DoesNotExist:
        logger.warning("stripe_webhook: MentorProfile not found for mentor_id=%s pi=%s", mentor_id, pi_id)
        return

    client = None
    if client_id_raw:
        try:
            client = UserProfile.objects.filter(id=int(client_id_raw)).first()
        except (ValueError, TypeError):
            pass

    platform_commission_cents = int(metadata.get("platform_commission_cents") or 0)
    if platform_commission_cents <= 0:
        platform_commission_cents = int(round(amount_cents * config.PLATFORM_COMMISSION_PERCENT))

    Payment.objects.update_or_create(
        stripe_payment_intent_id=pi_id,
        defaults={
            "mentor": mentor_profile,
            "client": client,
            "amount_cents": amount_cents,
            "currency": currency,
            "platform_commission_cents": platform_commission_cents,
            "status": "succeeded",
        },
    )
    logger.info("stripe_webhook: Payment updated pi=%s status=succeeded", pi_id)


def _handle_payment_intent_failed(obj):
    """Create or update Payment row for failed PaymentIntent. Idempotent. Handles wallet_topup and session."""
    from billing.models import Payment
    from billing import config
    from accounts.models import MentorProfile, UserProfile

    pi_id = obj.get("id")
    if not pi_id:
        return
    amount_cents = obj.get("amount") or 0
    currency = (obj.get("currency") or "usd").lower()[:10]
    metadata = obj.get("metadata") or {}
    payment_type = metadata.get("payment_type") or ""
    platform_commission_cents = int(metadata.get("platform_commission_cents") or 0)

    if payment_type == "wallet_topup":
        client_id_raw = metadata.get("client_id")
        client = None
        if client_id_raw:
            try:
                client = UserProfile.objects.filter(id=int(client_id_raw)).first()
            except (ValueError, TypeError):
                pass
        Payment.objects.update_or_create(
            stripe_payment_intent_id=pi_id,
            defaults={
                "mentor": None,
                "client": client,
                "amount_cents": amount_cents,
                "currency": currency,
                "platform_commission_cents": platform_commission_cents,
                "status": "failed",
            },
        )
        logger.info("stripe_webhook: Payment wallet_topup failed pi=%s", pi_id)
        return

    if payment_type == "session_accept":
        from general.models import Session
        session_id_raw = metadata.get("session_id")
        mentor_id = metadata.get("mentor_id")
        client_id_raw = metadata.get("client_id")
        if session_id_raw and mentor_id:
            try:
                session = Session.objects.get(id=int(session_id_raw))
                mentor_profile = MentorProfile.objects.get(user_id=mentor_id)
                client = None
                if client_id_raw:
                    try:
                        client = UserProfile.objects.filter(id=int(client_id_raw)).first()
                    except (ValueError, TypeError):
                        pass
                if platform_commission_cents <= 0:
                    platform_commission_cents = int(round(amount_cents * config.PLATFORM_COMMISSION_PERCENT))
                Payment.objects.update_or_create(
                    stripe_payment_intent_id=pi_id,
                    defaults={
                        "mentor": mentor_profile,
                        "client": client,
                        "session": session,
                        "amount_cents": amount_cents,
                        "currency": currency,
                        "platform_commission_cents": platform_commission_cents,
                        "status": "failed",
                    },
                )
            except (ValueError, TypeError, Session.DoesNotExist, MentorProfile.DoesNotExist):
                pass
        logger.info("stripe_webhook: Payment session_accept failed pi=%s", pi_id)
        return

    mentor_id = metadata.get("mentor_id")
    client_id_raw = metadata.get("client_id")
    if not mentor_id:
        logger.warning("stripe_webhook: payment_intent.payment_failed missing metadata.mentor_id pi=%s", pi_id)
        return
    try:
        mentor_profile = MentorProfile.objects.get(user_id=mentor_id)
    except MentorProfile.DoesNotExist:
        logger.warning("stripe_webhook: MentorProfile not found for mentor_id=%s pi=%s", mentor_id, pi_id)
        return

    client = None
    if client_id_raw:
        try:
            client = UserProfile.objects.filter(id=int(client_id_raw)).first()
        except (ValueError, TypeError):
            pass

    if platform_commission_cents <= 0:
        platform_commission_cents = int(round(amount_cents * config.PLATFORM_COMMISSION_PERCENT))

    Payment.objects.update_or_create(
        stripe_payment_intent_id=pi_id,
        defaults={
            "mentor": mentor_profile,
            "client": client,
            "amount_cents": amount_cents,
            "currency": currency,
            "platform_commission_cents": platform_commission_cents,
            "status": "failed",
        },
    )
    logger.info("stripe_webhook: Payment updated pi=%s status=failed", pi_id)


def _handle_charge_refunded(charge_obj):
    """On Stripe refund: update Payment.status, session.status/refunded_at, add wallet credit."""
    from billing.models import Payment
    from billing.services.wallet_service import add_credit
    from django.utils import timezone as dj_timezone

    pi_id = charge_obj.get("payment_intent")
    if isinstance(pi_id, dict):
        pi_id = pi_id.get("id")
    if not pi_id:
        return
    amount_refunded = charge_obj.get("amount_refunded") or 0
    payment = Payment.objects.filter(stripe_payment_intent_id=pi_id).first()
    if not payment:
        return
    payment.status = "refunded"
    payment.save(update_fields=["status"])
    session = getattr(payment, "session", None)
    if session:
        session.status = "refunded"
        session.refunded_at = dj_timezone.now()
        session.save(update_fields=["status", "refunded_at"])
    if payment.client and amount_refunded > 0:
        add_credit(
            payment.client,
            amount_refunded,
            reason="refund",
            related_payment=payment,
            related_session=session,
        )
        payment.client.refresh_from_db()
        new_balance_cents = getattr(payment.client, "wallet_balance_cents", 0) or 0
        client_user = getattr(payment.client, "user", None)
        if client_user:
            try:
                from general.models import Notification
                import uuid
                amount_dollars = amount_refunded / 100.0
                new_balance_dollars = new_balance_cents / 100.0
                Notification.objects.create(
                    user=client_user,
                    batch_id=uuid.uuid4(),
                    target_type="single",
                    title="Refund processed",
                    description=f"${amount_dollars:.2f} has been refunded to your wallet. Your balance is now ${new_balance_dollars:.2f}.",
                )
                from general.email_service import EmailService
                EmailService.send_refund_notification_email(
                    client_user,
                    amount_refunded,
                    new_balance_cents,
                    session=session,
                    fail_silently=True,
                )
            except Exception as e:
                logger.warning("stripe_webhook: charge.refunded notification/email failed: %s", e)
    logger.info("stripe_webhook: charge.refunded pi=%s Payment refunded, wallet credited", pi_id)
