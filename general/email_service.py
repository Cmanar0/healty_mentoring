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
    def get_site_domain() -> str:
        """
        Get the site domain based on DEVELOPMENT_MODE setting.
        
        Returns:
            str: The full site domain URL (e.g., 'https://healthymentoring.com' or 'http://localhost:8000')
        """
        development_mode = getattr(settings, 'DEVELOPMENT_MODE', 'dev').lower()
        if development_mode == 'prod':
            # Use SITE_DOMAIN from env if available, otherwise default
            site_domain = os.getenv('SITE_DOMAIN', 'https://healthymentoring.com')
            # Ensure it has protocol
            if not site_domain.startswith(('http://', 'https://')):
                site_domain = f'https://{site_domain}'
            return site_domain
        else:
            return 'http://localhost:8000'
    
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
        # Determine site domain based on environment
        site_domain = EmailService.get_site_domain()
        development_mode = getattr(settings, 'DEVELOPMENT_MODE', 'dev').lower()
        context.setdefault('site_domain', site_domain)
        context.setdefault('site_name', 'Healthy Mentoring')
        context.setdefault('development_mode', development_mode)
        
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
        
        # Generate a secure token for the welcome link using Django's token generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator
        
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build welcome URL
        site_domain = EmailService.get_site_domain()
        welcome_url = f"{site_domain}/accounts/welcome/{uid}/{token}/"
        
        context = {
            'user': user,
            'user_name': user_name,
            'welcome_url': welcome_url,
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
    def send_payment_confirmation_email(user, amount_cents: int, payment_type: str, session=None, fail_silently: bool = True) -> bool:
        """
        Send payment confirmation email after successful wallet top-up or session payment.

        Args:
            user: CustomUser (recipient)
            amount_cents: Amount paid in cents
            payment_type: 'wallet_topup' or 'session_payment'
            session: Optional Session for session_payment (for date/mentor in template)
            fail_silently: If True, log and return False on error

        Returns:
            bool: True if email was sent successfully
        """
        user_name = "there"
        if hasattr(user, 'profile') and user.profile:
            if hasattr(user.profile, 'first_name') and user.profile.first_name:
                user_name = user.profile.first_name
        amount_dollars = amount_cents / 100.0
        context = {
            'user': user,
            'user_name': user_name,
            'amount_cents': amount_cents,
            'amount_dollars': amount_dollars,
            'payment_type': payment_type,
            'session': session,
        }
        if session:
            context['session'] = session
            if hasattr(session, 'created_by') and session.created_by:
                try:
                    mp = getattr(session.created_by, 'mentor_profile', None)
                    context['mentor_name'] = f"{mp.first_name} {mp.last_name}" if mp else getattr(session.created_by, 'email', 'Mentor')
                except Exception:
                    context['mentor_name'] = 'Mentor'
            else:
                context['mentor_name'] = 'Mentor'
        subject = "Payment confirmation – Healthy Mentoring"
        return EmailService.send_email(
            subject=subject,
            recipient_email=user.email,
            template_name='payment_confirmation',
            context=context,
            fail_silently=fail_silently,
        )

    @staticmethod
    def send_refund_notification_email(user, amount_cents: int, new_balance_cents: int, session=None, fail_silently: bool = True) -> bool:
        """
        Send email to client after a session refund (amount refunded and new wallet balance).

        Args:
            user: CustomUser (client)
            amount_cents: Refunded amount in cents
            new_balance_cents: Client's wallet balance after refund
            session: Optional Session (for context)
            fail_silently: If True, log and return False on error

        Returns:
            bool: True if email was sent successfully
        """
        user_name = "there"
        if hasattr(user, 'profile') and user.profile:
            if hasattr(user.profile, 'first_name') and user.profile.first_name:
                user_name = user.profile.first_name
        amount_dollars = amount_cents / 100.0
        new_balance_dollars = new_balance_cents / 100.0
        context = {
            'user': user,
            'user_name': user_name,
            'amount_cents': amount_cents,
            'amount_dollars': amount_dollars,
            'new_balance_cents': new_balance_cents,
            'new_balance_dollars': new_balance_dollars,
            'session': session,
        }
        if session and hasattr(session, 'created_by') and session.created_by:
            try:
                mp = getattr(session.created_by, 'mentor_profile', None)
                context['mentor_name'] = f"{mp.first_name} {mp.last_name}" if mp else getattr(session.created_by, 'email', 'Mentor')
            except Exception:
                context['mentor_name'] = 'Mentor'
        else:
            context['mentor_name'] = 'Mentor'
        subject = "Refund processed – Healthy Mentoring"
        return EmailService.send_email(
            subject=subject,
            recipient_email=user.email,
            template_name='refund_notification',
            context=context,
            fail_silently=fail_silently,
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
    
    @staticmethod
    def send_session_booking_confirmation_email(
        session,
        mentor_profile,
        user,
        user_timezone: str,
        is_free_session: bool = False,
        first_session_length: Optional[int] = None,
        regular_session_length: Optional[int] = None
    ) -> bool:
        """
        Send session booking confirmation email to user.
        
        Args:
            session: Session instance
            mentor_profile: MentorProfile instance
            user: CustomUser instance (can be None for new users)
            user_timezone: User's timezone (IANA string)
            is_free_session: Whether this is a free first session
            first_session_length: Length of first session in minutes (if free)
            regular_session_length: Length of regular sessions in minutes
            
        Returns:
            bool: True if email was sent successfully
        """
        from django.urls import reverse
        from zoneinfo import ZoneInfo
        from datetime import timezone as dt_timezone
        
        # Get user's name
        user_name = None
        user_email = None
        is_new_user = False
        
        if user:
            user_email = user.email
            if hasattr(user, 'profile') and user.profile:
                if hasattr(user.profile, 'first_name') and user.profile.first_name:
                    user_name = user.profile.first_name
            is_new_user = not user.is_email_verified
        else:
            # This shouldn't happen, but handle it
            return False
        
        # Convert session times to user's timezone
        try:
            tzinfo = ZoneInfo(str(user_timezone))
        except Exception:
            tzinfo = dt_timezone.utc
        
        session_date_local = None
        session_start_time_local = None
        session_end_time_local = None
        
        try:
            if session.start_datetime and session.end_datetime:
                start_local = session.start_datetime.astimezone(tzinfo)
                end_local = session.end_datetime.astimezone(tzinfo)
                
                session_date_local = start_local.strftime('%A, %B %d, %Y')
                session_start_time_local = start_local.strftime('%I:%M %p').lstrip('0')
                session_end_time_local = end_local.strftime('%I:%M %p').lstrip('0')
        except Exception:
            # Fallback to UTC if conversion fails
            if session.start_datetime:
                session_date_local = session.start_datetime.strftime('%A, %B %d, %Y')
                session_start_time_local = session.start_datetime.strftime('%I:%M %p').lstrip('0')
            if session.end_datetime:
                session_end_time_local = session.end_datetime.strftime('%I:%M %p').lstrip('0')
        
        # Build action URL - check if user needs to complete registration
        site_domain = EmailService.get_site_domain()
        action_url = None
        
        try:
            # Check if user needs to complete registration
            # (booking-created users have empty first_name/last_name)
            needs_registration = False
            if user and hasattr(user, 'user_profile'):
                profile = user.user_profile
                if not profile.first_name or not profile.last_name:
                    needs_registration = True
            
            if needs_registration:
                # Generate token for registration completion
                from django.utils.http import urlsafe_base64_encode
                from django.utils.encoding import force_bytes
                from django.contrib.auth.tokens import default_token_generator
                from django.urls import reverse
                
                reg_token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                action_url = f"{site_domain}{reverse('accounts:complete_registration', kwargs={'uidb64': uid, 'token': reg_token})}"
            else:
                # Link to my-sessions page (requires login)
                # URL pattern: /dashboard/user/my-sessions/
                action_url = f"{site_domain}/dashboard/user/my-sessions/"
        except Exception:
            pass
        
        # Get mentor name and profile URL
        mentor_name = f"{mentor_profile.first_name} {mentor_profile.last_name}"
        mentor_profile_url = None
        try:
            mentor_profile_url = f"{site_domain}{reverse('web:mentor_profile_detail', kwargs={'user_id': mentor_profile.user.id})}"
        except Exception:
            pass
        
        # Get note from session
        note = session.note or ''
        
        context = {
            'user': user,
            'user_name': user_name,
            'session': session,
            'mentor_name': mentor_name,
            'mentor_profile_url': mentor_profile_url,
            'session_date_local': session_date_local,
            'session_start_time_local': session_start_time_local,
            'session_end_time_local': session_end_time_local,
            'user_timezone': user_timezone,
            'session_price': session.session_price,
            'is_free_session': is_free_session,
            'first_session_length': first_session_length,
            'regular_session_length': regular_session_length,
            'note': note,
            'action_url': action_url,
            'is_new_user': is_new_user,
        }
        
        return EmailService.send_email(
            subject=f"Session Booking Confirmed with {mentor_name}",
            recipient_email=user_email,
            template_name='session_booking_confirmation',
            context=context,
        )
    
    @staticmethod
    def send_ticket_created_email(ticket) -> bool:
        """
        Send email to admin when a new ticket is created.
        
        Args:
            ticket: Ticket instance
            
        Returns:
            bool: True if email was sent successfully
        """
        from general.models import Ticket
        
        user_name = "Unknown User"
        user_email = "unknown@example.com"
        user_role = "Unknown"
        
        if hasattr(ticket.user, 'profile') and ticket.user.profile:
            user_name = f"{ticket.user.profile.first_name} {ticket.user.profile.last_name}".strip()
            user_role = ticket.user.profile.role
        user_email = ticket.user.email
        
        has_image = "Yes" if ticket.image else "No"
        
        context = {
            'ticket': ticket,
            'user_name': user_name,
            'user_email': user_email,
            'user_role': user_role,
            'has_image': has_image,
            'ticket_url': f"{EmailService.get_site_domain()}/dashboard/admin/tickets/{ticket.id}/",
        }
        
        return EmailService.send_email(
            subject=f"New Support Ticket: {ticket.title}",
            recipient_email="info@healthymentoring.com",
            template_name='ticket_created',
            context=context,
        )
    
    @staticmethod
    def send_ticket_comment_email(ticket, comment, commenter) -> bool:
        """
        Send email when a comment is added to a ticket.
        If admin comments, notify the ticket creator.
        If user/mentor comments, notify all admins.
        
        Args:
            ticket: Ticket instance
            comment: TicketComment instance
            commenter: User who made the comment
            
        Returns:
            bool: True if email was sent successfully
        """
        from accounts.models import CustomUser
        
        is_admin = hasattr(commenter, 'profile') and commenter.profile and commenter.profile.role == 'admin'
        
        if is_admin:
            # Admin commented - notify ticket creator
            user_name = "there"
            if hasattr(ticket.user, 'profile') and ticket.user.profile:
                if hasattr(ticket.user.profile, 'first_name') and ticket.user.profile.first_name:
                    user_name = ticket.user.profile.first_name
            
            context = {
                'ticket': ticket,
                'comment': comment,
                'user_name': user_name,
                'ticket_url': f"{EmailService.get_site_domain()}/dashboard/{ticket.user.profile.role}/tickets/{ticket.id}/",
            }
            
            return EmailService.send_email(
                subject=f"Update on your support ticket: {ticket.title}",
                recipient_email=ticket.user.email,
                template_name='ticket_comment_user',
                context=context,
            )
        else:
            # User/Mentor commented - notify admin
            user_name = "Unknown User"
            user_role = "Unknown"
            
            if hasattr(commenter, 'profile') and commenter.profile:
                user_name = f"{commenter.profile.first_name} {commenter.profile.last_name}".strip()
                user_role = commenter.profile.role
            
            context = {
                'ticket': ticket,
                'comment': comment,
                'user_name': user_name,
                'user_role': user_role,
                'ticket_url': f"{EmailService.get_site_domain()}/dashboard/admin/tickets/{ticket.id}/",
            }
            
            return EmailService.send_email(
                subject=f"New comment on ticket #{ticket.id}: {ticket.title}",
                recipient_email="info@healthymentoring.com",
                template_name='ticket_comment_admin',
                context=context,
            )
    
    @staticmethod
    def send_ticket_resolved_email(ticket) -> bool:
        """
        Send email when a ticket is marked as resolved.
        
        Args:
            ticket: Ticket instance
            
        Returns:
            bool: True if email was sent successfully
        """
        user_name = "there"
        if hasattr(ticket.user, 'profile') and ticket.user.profile:
            if hasattr(ticket.user.profile, 'first_name') and ticket.user.profile.first_name:
                user_name = ticket.user.profile.first_name
        
        context = {
            'ticket': ticket,
            'user_name': user_name,
            'ticket_url': f"{EmailService.get_site_domain()}/dashboard/{ticket.user.profile.role}/tickets/{ticket.id}/",
        }
        
        return EmailService.send_email(
            subject=f"Your support ticket has been resolved: {ticket.title}",
            recipient_email=ticket.user.email,
            template_name='ticket_resolved',
            context=context,
        )
    
    @staticmethod
    def send_timezone_change_email(user, new_timezone: str, old_timezone: str) -> bool:
        """
        Send timezone change notification email with upcoming sessions.
        
        Args:
            user: CustomUser instance
            new_timezone: New timezone IANA string (e.g., "Europe/Prague")
            old_timezone: Old timezone IANA string (for reference)
            
        Returns:
            bool: True if email was sent successfully
        """
        from general.models import Session
        from django.utils import timezone as django_timezone
        from zoneinfo import ZoneInfo
        from datetime import timezone as dt_timezone
        
        # Get user's name
        user_name = "there"
        if hasattr(user, 'profile') and user.profile:
            if hasattr(user.profile, 'first_name') and user.profile.first_name:
                user_name = user.profile.first_name
        
        # Get user's profile to determine role
        profile = None
        if hasattr(user, 'user_profile'):
            profile = user.user_profile
        elif hasattr(user, 'mentor_profile'):
            profile = user.mentor_profile
        
        if not profile:
            return False
        
        # Get upcoming sessions
        now = django_timezone.now()
        upcoming_sessions = []
        
        try:
            # Convert new timezone string to ZoneInfo
            try:
                tzinfo = ZoneInfo(str(new_timezone))
            except Exception:
                tzinfo = dt_timezone.utc
            
            # Get sessions based on user role
            if hasattr(user, 'user_profile') and user.user_profile:
                # Regular user - get sessions where user is an attendee
                sessions = Session.objects.filter(
                    attendees=user,
                    status__in=['invited', 'confirmed'],
                    start_datetime__gte=now
                ).order_by('start_datetime').prefetch_related('attendees', 'mentors__user')
            elif hasattr(user, 'mentor_profile') and user.mentor_profile:
                mentor_profile = user.mentor_profile
                sessions = mentor_profile.sessions.filter(
                    status__in=['invited', 'confirmed'],
                    start_datetime__gte=now
                ).order_by('start_datetime').prefetch_related('attendees')
            else:
                sessions = Session.objects.none()
            
            # Format sessions with new timezone
            for session in sessions:
                # Get mentor/client name
                mentor_name = None
                if hasattr(user, 'user_profile') and user.user_profile:
                    first_mentor = session.mentors.select_related('user').first()
                    if first_mentor:
                        mentor_name = f"{first_mentor.first_name} {first_mentor.last_name}".strip() or (first_mentor.user.email.split('@')[0] if getattr(first_mentor, 'user', None) else 'Mentor')
                    else:
                        mentor_name = 'Mentor'
                elif hasattr(user, 'mentor_profile') and user.mentor_profile:
                    # Mentor viewing sessions - get client name
                    client = session.attendees.first() if session.attendees.exists() else None
                    if client and hasattr(client, 'user_profile'):
                        mentor_name = f"{client.user_profile.first_name} {client.user_profile.last_name}".strip()
                        if not mentor_name:
                            mentor_name = client.email.split('@')[0]
                    else:
                        mentor_name = client.email.split('@')[0] if client else 'Client'
                
                # Convert session times to new timezone
                try:
                    start_local = session.start_datetime.astimezone(tzinfo)
                    end_local = session.end_datetime.astimezone(tzinfo)
                    
                    date_local = start_local.strftime('%A, %B %d, %Y')
                    start_time_local = start_local.strftime('%I:%M %p').lstrip('0')
                    end_time_local = end_local.strftime('%I:%M %p').lstrip('0')
                except Exception:
                    # Fallback to UTC formatting
                    date_local = session.start_datetime.strftime('%A, %B %d, %Y')
                    start_time_local = session.start_datetime.strftime('%I:%M %p').lstrip('0')
                    end_time_local = session.end_datetime.strftime('%I:%M %p').lstrip('0')
                
                upcoming_sessions.append({
                    'mentor_name': mentor_name or 'Session',
                    'status': session.status,
                    'date_local': date_local,
                    'start_time_local': start_time_local,
                    'end_time_local': end_time_local,
                })
        except Exception as e:
            # Log error but continue
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error formatting sessions for timezone change email: {str(e)}")
        
        # Format timezone name for display
        try:
            # Try to get a friendly timezone name
            tz_parts = new_timezone.split('/')
            timezone_display = tz_parts[-1].replace('_', ' ') if len(tz_parts) > 1 else new_timezone
        except Exception:
            timezone_display = new_timezone
        
        context = {
            'user': user,
            'user_name': user_name,
            'new_timezone': timezone_display,
            'old_timezone': old_timezone,
            'upcoming_sessions': upcoming_sessions,
        }
        
        return EmailService.send_email(
            subject="Your timezone has been updated",
            recipient_email=user.email,
            template_name='timezone_change_notification',
            context=context,
        )

    @staticmethod
    def send_project_assignment_email(project, client_profile) -> bool:
        """
        Send email to client to accept project assignment.
        
        Email contains secure link that:
        1. Logs out if wrong user is logged in
        2. Forces login if not logged in
        3. Redirects to project acceptance page after login
        
        Args:
            project: Project instance
            client_profile: UserProfile instance of the client
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator
        from django.urls import reverse
        
        try:
            client_user = client_profile.user
            
            # Generate secure token
            uidb64 = urlsafe_base64_encode(force_bytes(client_user.id))
            token = default_token_generator.make_token(client_user)
            
            # Build secure URL with logout parameter
            accept_url = reverse('general:dashboard_user:accept_project_assignment_secure', args=[uidb64, token])
            accept_url += '?logout=true'  # Trigger logout if wrong user
            
            # Get mentor name
            mentor_name = "Your mentor"
            if project.supervised_by:
                mentor_name = f"{project.supervised_by.first_name} {project.supervised_by.last_name}".strip()
                if not mentor_name:
                    mentor_name = project.supervised_by.user.email.split('@')[0]
            
            # Get client name
            client_name = f"{client_profile.first_name} {client_profile.last_name}".strip()
            if not client_name:
                client_name = client_user.email.split('@')[0]
            
            context = {
                'client_name': client_name,
                'mentor_name': mentor_name,
                'project': project,
                'accept_url': EmailService.get_site_domain() + accept_url,
            }
            
            return EmailService.send_email(
                subject=f"New Project Assignment: {project.title}",
                recipient_email=client_user.email,
                template_name='project_assignment',
                context=context,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Error sending project assignment email: {str(e)}')
            return False

