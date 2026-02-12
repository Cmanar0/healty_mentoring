from datetime import timedelta
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from django.utils import timezone

from billing.services.session_finance_service import (
    PayoutError,
    mark_session_payout_available,
    refund_completed_session,
    withdraw_session_payout,
)


class SessionFinanceServiceHardeningTests(TestCase):
    def _locked_session_chain(self, locked_session):
        manager = Mock()
        locked = Mock()
        related = Mock()
        manager.select_for_update.return_value = locked
        locked.select_related.return_value = related
        related.get.return_value = locked_session
        return manager

    @patch("billing.services.session_finance_service.add_credit")
    @patch("billing.services.session_finance_service._get_client_profile")
    @patch("billing.services.session_finance_service.Session")
    def test_refund_keeps_commission_immutable(self, session_model, get_client_profile, add_credit):
        now = timezone.now()
        payment = SimpleNamespace(
            status="succeeded",
            platform_commission_cents=250,
            save=Mock(),
        )
        locked_session = SimpleNamespace(
            id=101,
            status="completed",
            end_datetime=now - timedelta(days=1),
            payment=payment,
            refunded_at=None,
            save=Mock(),
            session_price=20,
        )
        session_model.objects = self._locked_session_chain(locked_session)
        get_client_profile.return_value = (SimpleNamespace(id=1), SimpleNamespace(id=2))

        refunded_amount = refund_completed_session(locked_session, now=now)

        self.assertEqual(refunded_amount, 2000)
        self.assertEqual(payment.status, "refunded")
        self.assertEqual(payment.platform_commission_cents, 250)
        payment.save.assert_called_once_with(update_fields=["status"])
        add_credit.assert_called_once()

    @patch("billing.services.session_finance_service.credit_mentor")
    @patch("billing.services.session_finance_service.Session")
    def test_mark_payout_available_sets_status_before_credit(self, session_model, credit_mentor):
        now = timezone.now()
        mentor_profile = SimpleNamespace(id=10)
        payment = SimpleNamespace(amount_cents=10000, platform_commission_cents=1000)
        locked_session = SimpleNamespace(
            id=202,
            status="completed",
            end_datetime=now - timedelta(days=30),
            payment=payment,
            created_by=SimpleNamespace(mentor_profile=mentor_profile),
            save=Mock(),
        )
        session_model.objects = self._locked_session_chain(locked_session)

        with patch("billing.models.MentorWalletTransaction.objects.filter") as tx_filter:
            tx_filter.return_value.exists.return_value = False

            def assert_status_flipped(*args, **kwargs):
                self.assertEqual(locked_session.status, "payout_available")

            credit_mentor.side_effect = assert_status_flipped
            amount = mark_session_payout_available(locked_session, now=now)

        self.assertEqual(amount, 9000)
        locked_session.save.assert_called_once_with(update_fields=["status"])
        credit_mentor.assert_called_once()

    @patch("billing.services.session_finance_service.Session")
    def test_withdraw_rejects_non_payout_available_status(self, session_model):
        now = timezone.now()
        mentor_profile = SimpleNamespace(user_id=5)
        locked_session = SimpleNamespace(
            id=303,
            status="completed",
            created_by_id=5,
            payment=SimpleNamespace(amount_cents=10000, platform_commission_cents=1000),
        )
        session_model.objects = self._locked_session_chain(locked_session)

        with self.assertRaises(PayoutError):
            withdraw_session_payout(locked_session, mentor_profile, now=now)
