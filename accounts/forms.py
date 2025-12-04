from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField, UserCreationForm, UserChangeForm, AuthenticationForm
from .models import CustomUser, UserProfile

class CustomAuthenticationForm(AuthenticationForm):
    """Custom authentication form that normalizes email to lowercase"""
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            return username.lower().strip()
        return username

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ("email",)

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ("email",)

class RegisterForm(forms.Form):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('mentor', 'Mentor'),
    ]
    
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect, initial='user', required=True)
    password1 = forms.CharField(widget=forms.PasswordInput, required=True)
    password2 = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            email = email.lower().strip()
            if CustomUser.objects.filter(email=email).exists():
                raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match")
        return cleaned

from django.contrib.auth.forms import PasswordResetForm
from general.email_service import EmailService
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
import os

class CustomPasswordResetForm(PasswordResetForm):
    """Custom password reset form that normalizes email to lowercase"""
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            return email.lower().strip()
        return email
    
    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Override standard send_mail to use our EmailService.
        """
        # Reconstruct the reset URL from context
        # Context has: domain, uid, token, protocol, etc.
        # But EmailService expects a full URL.
        # We can reconstruct it using the same logic as Django or just pass the context if we modified EmailService.
        # But EmailService.send_password_reset_email takes (user, reset_url).
        # The user object is in context['user'].
        
        user = context.get('user')
        domain = context.get('domain')
        uid = context.get('uid')
        token = context.get('token')
        protocol = context.get('protocol')
        
        # Construct URL
        # We assume the URL pattern name is 'accounts:password_reset_confirm' or just 'password_reset_confirm'
        # In urls.py it is 'password_reset_confirm' (no namespace if included directly, but app_name='accounts' is set)
        # So it should be 'accounts:password_reset_confirm'
        
        try:
            reset_url = f"{protocol}://{domain}{reverse('accounts:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})}"
            EmailService.send_password_reset_email(user, reset_url)
        except Exception as e:
            print(f"Error sending password reset email: {e}")
            # Fallback to super if needed, or just log

