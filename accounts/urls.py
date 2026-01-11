from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .views import RegisterView, VerifyEmailView, CustomLoginView, CustomPasswordResetConfirmView, CustomLogoutView, resend_verification_email
from .forms import CustomPasswordResetForm
from . import views

app_name = "accounts"
urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    path("verify/<uidb64>/<token>/", VerifyEmailView.as_view(), name="verify_email"),
    # Complete Registration (for booking-created users)
    path("complete-registration/<uidb64>/<token>/", views.complete_registration, name="complete_registration"),
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
    # Complete Invitation
    path("complete-invitation/<str:token>/", views.complete_invitation, name="complete_invitation"),
    # Session invitation landing (stable link for emails)
    path("session-invitation/<str:token>/", views.session_invitation_link, name="session_invitation_link"),
    # Session changes landing (stable link for emails)
    path("session-changes/", views.session_changes_link, name="session_changes_link"),
    # Confirm Mentor Invitation (for existing users)
    path("confirm-mentor-invitation/<str:token>/", views.confirm_mentor_invitation, name="confirm_mentor_invitation"),
    # Respond to Invitation (accept/deny)
    path("respond-invitation/<int:relationship_id>/", views.respond_to_invitation, name="respond_to_invitation"),
    # Welcome redirect (from welcome email)
    path("welcome/<uidb64>/<token>/", views.welcome_redirect, name="welcome_redirect"),
]
