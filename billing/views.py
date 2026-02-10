"""
Billing views. Phase 1: Stripe status/health check only.
"""
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from billing.services.stripe_service import is_configured, check_api_ok


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
