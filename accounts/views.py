from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.views import View
from django.contrib import messages
from .forms import RegisterForm
from .models import CustomUser
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse
import os

class RegisterView(View):
    def get(self, request):
        form = RegisterForm()
        return render(request, "accounts/register.html", {"form": form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            password = form.cleaned_data["password1"]
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            # Create user
            user = CustomUser.objects.create_user(email=email, password=password)
            # Add profile data
            profile = user.profile
            profile.first_name = first_name
            profile.last_name = last_name
            profile.save()
            # Send verification email
            send_verification_email(request, user)
            return render(request, "accounts/email_verify_sent.html", {"email": email})
        return render(request, "accounts/register.html", {"form": form})

def send_verification_email(request, user):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    domain = os.getenv("SITE_DOMAIN", "http://localhost:8000")
    verify_url = f"{domain}{reverse('accounts:verify_email', kwargs={'uidb64': uid, 'token': token})}"
    subject = "Verify your Healthy Mentoring account"
    html_message = render_to_string("accounts/verify_email.html", {"user": user, "verify_url": verify_url})
    send_mail(subject, "", settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_message, fail_silently=False)

class VerifyEmailView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except Exception:
            user = None
        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return render(request, "accounts/verify_success.html")
        else:
            return HttpResponse("Invalid verification link", status=400)
