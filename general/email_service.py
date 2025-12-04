"""
Universal email service for sending transactional emails.
Provides a centralized way to send HTML emails with consistent branding.
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from typing import List, Optional, Dict, Any
import os


class EmailService:
    """Service for sending transactional emails with consistent templates."""
    
    @staticmethod
    def send_email(
        subject: str,
        recipient_email: str,
        template_name: str,
        context: Optional[Dict[str, Any]] = None,
        from_email: Optional[str] = None,
        fail_silently: bool = False,
    ) -> bool:
        """
        Send an HTML email using a template.
        
        Args:
            subject: Email subject line
            recipient_email: Recipient's email address
            template_name: Name of the email template (without .html extension)
            context: Dictionary of context variables for the template
            from_email: Sender email (defaults to DEFAULT_FROM_EMAIL)
            fail_silently: Whether to fail silently on errors
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if context is None:
            context = {}
        
        if from_email is None:
            from_email = settings.DEFAULT_FROM_EMAIL
        
        # Add default context variables
        context.setdefault('site_domain', os.getenv('SITE_DOMAIN', 'http://localhost:8000'))
        context.setdefault('site_name', 'Healthy Mentoring')
        context.setdefault('development_mode', os.getenv('DEVELOPMENT_MODE', 'dev').lower())
        
        # Render the email template
        html_content = render_to_string(
            f'emails/{template_name}.html',
            context
        )
        
        # Create email message
        msg = EmailMultiAlternatives(
            subject=subject,
            body='',  # Plain text version (empty, we only send HTML)
            from_email=from_email,
            to=[recipient_email],
        )
        msg.attach_alternative(html_content, "text/html")
        
        try:
            msg.send(fail_silently=fail_silently)
            return True
        except Exception as e:
            if not fail_silently:
                raise
            return False
    
    @staticmethod
    def send_verification_email(user, verification_url: str) -> bool:
        """
        Send email verification email to a user.
        
        Args:
            user: User instance (should have email and profile attributes)
            verification_url: Full URL for email verification
            
        Returns:
            bool: True if email was sent successfully
        """
        # Get user's name
        user_name = "there"
        if hasattr(user, 'profile') and user.profile:
            if hasattr(user.profile, 'first_name') and user.profile.first_name:
                user_name = user.profile.first_name
        
        context = {
            'user': user,
            'user_name': user_name,
            'verification_url': verification_url,
        }
        
        return EmailService.send_email(
            subject="Verify your Healthy Mentoring account",
            recipient_email=user.email,
            template_name='registration_verification',
            context=context,
        )
    
    @staticmethod
    def send_password_reset_email(user, reset_url: str) -> bool:
        """
        Send password reset email to a user.
        
        Args:
            user: User instance
            reset_url: Full URL for password reset
            
        Returns:
            bool: True if email was sent successfully
        """
        user_name = "there"
        if hasattr(user, 'profile') and user.profile:
            if hasattr(user.profile, 'first_name') and user.profile.first_name:
                user_name = user.profile.first_name
        
        context = {
            'user': user,
            'user_name': user_name,
            'reset_url': reset_url,
        }
        
        return EmailService.send_email(
            subject="Reset your Healthy Mentoring password",
            recipient_email=user.email,
            template_name='password_reset',
            context=context,
        )
    
    @staticmethod
    def send_welcome_email(user) -> bool:
        """
        Send welcome email to a newly registered user.
        
        Args:
            user: User instance
            
        Returns:
            bool: True if email was sent successfully
        """
        user_name = "there"
        if hasattr(user, 'profile') and user.profile:
            if hasattr(user.profile, 'first_name') and user.profile.first_name:
                user_name = user.profile.first_name
        
        context = {
            'user': user,
            'user_name': user_name,
        }
        
        return EmailService.send_email(
            subject="Welcome to Healthy Mentoring!",
            recipient_email=user.email,
            template_name='welcome',
            context=context,
        )

    @staticmethod
    def send_password_changed_email(user) -> bool:
        """
        Send password changed confirmation email to a user.
        
        Args:
            user: User instance (should have email and profile attributes)
            
        Returns:
            bool: True if email was sent successfully
        """
        # Get user's name
        user_name = "there"
        if hasattr(user, 'profile') and user.profile:
            if hasattr(user.profile, 'first_name') and user.profile.first_name:
                user_name = user.profile.first_name
        
        context = {
            'user': user,
            'user_name': user_name,
        }
        
        return EmailService.send_email(
            subject="Your password has been changed",
            recipient_email=user.email,
            template_name='password_changed',
            context=context,
        )
    
    @staticmethod
    def send_email_change_otp(user, new_email, otp):
        """
        Send OTP for email change verification.
        
        Args:
            user (CustomUser): The user requesting the change
            new_email (str): The new email address
            otp (str): The verification code
            
        Returns:
            bool: True if email was sent successfully
        """
        user_name = "there"
        if hasattr(user, 'profile') and user.profile:
            if hasattr(user.profile, 'first_name') and user.profile.first_name:
                user_name = user.profile.first_name
                
        context = {
            'user': user,
            'user_name': user_name,
            'new_email': new_email,
            'otp': otp,
        }
        
        return EmailService.send_email(
            subject="Verify your new email address",
            recipient_email=new_email,
            template_name='email_change_verify',
            context=context,
        )

