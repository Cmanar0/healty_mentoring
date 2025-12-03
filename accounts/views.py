from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.views import View
from django.contrib import messages
from .forms import RegisterForm
from .models import CustomUser, UserProfile, MentorProfile
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.http import HttpResponse
from general.email_service import EmailService
import os
import json

class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("general:index")
        form = RegisterForm()
        return render(request, "accounts/register.html", {"form": form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            print("DEBUG: Form is valid. Creating user...")
            try:
                email = form.cleaned_data["email"].lower()
                password = form.cleaned_data["password1"]
                first_name = form.cleaned_data["first_name"]
                last_name = form.cleaned_data["last_name"]
                role = form.cleaned_data["role"]
                
                # Create user
                user = CustomUser.objects.create_user(email=email, password=password)
                print(f"DEBUG: User {email} created successfully.")
                
                # Default manuals data for navigation tutorial
                default_manuals = [
                    {
                        "id": "createNewSection",
                        "title": "Create New Content",
                        "text": "Use these buttons to quickly create sessions, users, projects, marketing materials, and blog posts.",
                        "position": {"x": -350, "y": 0},
                        "displayed": False
                    },
                    {
                        "id": "statsCard",
                        "title": "Track Your Performance",
                        "text": "View your statistics and metrics here. Use the dropdown to filter by different time periods.",
                        "position": {"x": 0, "y": 300},
                        "displayed": False
                    },
                    {
                        "id": "backlogCard",
                        "title": "Your Backlog",
                        "text": "Items that require your action are displayed here. Stay on top of your tasks!",
                        "position": {"x": 0, "y": -180},
                        "displayed": False
                    }
                ]
                
                # Auto-detect timezone from request headers (if available) or use UTC as fallback
                # Note: This is a best-effort approach. JavaScript will detect the actual browser timezone
                # and the timezone checker will prompt to update if different
                detected_timezone = None
                try:
                    # Try to get timezone from Accept-Language or other headers
                    # For now, we'll let JavaScript handle the detection on first login
                    # But we could use a geolocation API here if needed
                    pass
                except:
                    pass
                
                # Create appropriate profile based on role
                if role == 'mentor':
                    MentorProfile.objects.create(
                        user=user,
                        first_name=first_name,
                        last_name=last_name,
                        role='mentor',
                        manuals=default_manuals,
                        # time_zone will be auto-detected by JavaScript on first login
                        # and saved via the timezone checker modal
                    )
                    print(f"DEBUG: MentorProfile created for {email}.")
                else:  # role == 'user'
                    UserProfile.objects.create(
                        user=user,
                        first_name=first_name,
                        last_name=last_name,
                        role='user',
                        manuals=default_manuals,
                        # time_zone will be auto-detected by JavaScript on first login
                        # and saved via the timezone checker modal
                    )
                    print(f"DEBUG: UserProfile created for {email}.")
                
                # Send verification email
                print("DEBUG: Attempting to send verification email...")
                send_verification_email(request, user)
                print("DEBUG: Email sent successfully.")
                
                return render(request, "accounts/email_verify_sent.html", {"email": email})
            except Exception as e:
                print(f"ERROR during registration: {e}")
                # If user was created but email failed, we might want to delete the user or warn
                # For now, just show the error on the form
                form.add_error(None, f"Registration failed: {e}")
        else:
            print("DEBUG: Form is invalid.")
            print(form.errors)
            
        return render(request, "accounts/register.html", {"form": form})

def send_verification_email(request, user):
    """Send email verification email using the universal email service."""
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    domain = os.getenv("SITE_DOMAIN", "http://localhost:8000")
    verify_url = f"{domain}{reverse('accounts:verify_email', kwargs={'uidb64': uid, 'token': token})}"
    
    # Use the universal email service
    EmailService.send_verification_email(user, verify_url)

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
