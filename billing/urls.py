from django.urls import path
from . import views

app_name = "billing"

urlpatterns = [
    path("stripe-status/", views.stripe_status, name="stripe_status"),
    path("stripe-webhook/", views.stripe_webhook, name="stripe_webhook"),
]
