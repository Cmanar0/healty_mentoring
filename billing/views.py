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
    else:
        pass  # ignore other events

    return HttpResponse(status=200)


def _handle_payment_intent_succeeded(obj):
    """Create or update Payment row for succeeded PaymentIntent. Idempotent."""
    from billing.models import Payment
    from billing import config
    from accounts.models import MentorProfile, UserProfile

    pi_id = obj.get("id")
    if not pi_id:
        return
    amount_cents = obj.get("amount") or 0
    currency = (obj.get("currency") or "usd").lower()[:10]
    metadata = obj.get("metadata") or {}
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

    # Use commission frozen in metadata at PaymentIntent creation; fallback for older events
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
    """Create or update Payment row for failed PaymentIntent. Idempotent."""
    from billing.models import Payment
    from billing import config
    from accounts.models import MentorProfile, UserProfile

    pi_id = obj.get("id")
    if not pi_id:
        return
    amount_cents = obj.get("amount") or 0
    currency = (obj.get("currency") or "usd").lower()[:10]
    metadata = obj.get("metadata") or {}
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

    # Use commission frozen in metadata at PaymentIntent creation; fallback for older events
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
            "status": "failed",
        },
    )
    logger.info("stripe_webhook: Payment updated pi=%s status=failed", pi_id)
