from django.contrib import admin
from .models import Payment, WalletTransaction


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("stripe_payment_intent_id", "mentor", "client", "session", "amount_cents", "currency", "status", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("stripe_payment_intent_id",)
    readonly_fields = ("stripe_payment_intent_id", "created_at", "updated_at")


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount_cents", "reason", "created_at")
    list_filter = ("reason",)
    search_fields = ("reason",)
    readonly_fields = ("created_at",)
