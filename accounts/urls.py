from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .views import RegisterView, VerifyEmailView, CustomLoginView, CustomPasswordResetConfirmView, resend_verification_email
from .forms import CustomPasswordResetForm
from . import views

app_name = "accounts"
urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    path("verify/<uidb64>/<token>/", VerifyEmailView.as_view(), name="verify_email"),
    # Password reset
    path("password_reset/", auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset.html",
        form_class=CustomPasswordResetForm,
        success_url=reverse_lazy("accounts:password_reset_done")
    ), name="password_reset"),
    path("password_reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", CustomPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"), name="password_reset_complete"),
    # Email Change
    path("email/initiate/", views.initiate_email_change, name="initiate_email_change"),
    path("email/verify/", views.verify_email_change, name="verify_email_change"),
    path("email/check-pending/", views.check_pending_email_change, name="check_pending_email_change"),
    # Resend Verification Email
    path("resend-verification/", resend_verification_email, name="resend_verification_email"),
]
