from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from django.conf import settings
from accounts.models import MentorClientRelationship, MentorProfile, UserProfile, CustomUser
from dashboard_user.models import Project, Questionnaire, Question, QuestionnaireResponse, Task
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from general.models import Notification
from general.email_service import EmailService
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from urllib.parse import quote
import json
from decimal import Decimal

@login_required
def dashboard(request):
    # Ensure only users can access
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing user dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'user':
        return redirect('general:index')
    
    user_profile = request.user.user_profile if hasattr(request.user, 'user_profile') else None
    
    # Fetch upcoming sessions (invited and confirmed only, future dates, max 4)
    upcoming_sessions = []
    has_more_sessions = False
    
    try:
        from general.models import Session
        from zoneinfo import ZoneInfo
        from datetime import timezone as dt_timezone
        
        if user_profile:
            # Display timezone: prefer selected_timezone (same as booking modal and my-sessions)
            user_timezone = user_profile.selected_timezone or user_profile.detected_timezone or user_profile.time_zone or 'UTC'
            user_tzinfo = None
            try:
                user_tzinfo = ZoneInfo(str(user_timezone))
            except Exception:
                user_tzinfo = dt_timezone.utc
            
            now = timezone.now()
            # Get all upcoming sessions (invited and confirmed)
            all_upcoming = Session.objects.filter(
                attendees=request.user,
                status__in=['invited', 'confirmed'],
                start_datetime__gte=now
            ).order_by('start_datetime').prefetch_related('attendees', 'mentors__user')
            
            # Get total count to check if there are more than 4
            total_count = all_upcoming.count()
            has_more_sessions = total_count > 4
            
            # Get first 4 sessions
            sessions_queryset = all_upcoming[:4]
            
            # Format sessions for template
            for session in sessions_queryset:
                first_mentor = session.mentors.select_related('user').first()
                mentor_name = 'Mentor'
                if first_mentor:
                    mentor_name = f"{first_mentor.first_name} {first_mentor.last_name}".strip() or (first_mentor.user.email.split('@')[0] if getattr(first_mentor, 'user', None) else 'Mentor')
                
                # Convert to user's timezone
                start_datetime_local = session.start_datetime
                end_datetime_local = session.end_datetime
                try:
                    start_datetime_local = session.start_datetime.astimezone(user_tzinfo)
                    end_datetime_local = session.end_datetime.astimezone(user_tzinfo)
                except Exception:
                    pass
                
                upcoming_sessions.append({
                    'id': session.id,
                    'start_datetime': start_datetime_local,
                    'end_datetime': end_datetime_local,
                    'status': session.status,
                    'mentor_name': mentor_name,
                    'note': session.note,
                })
    except Exception as e:
        # Log error but don't fail the request
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching upcoming sessions: {str(e)}")
    
    # Get user's active backlog tasks (limit to 5 for dashboard)
    backlog_tasks = []
    if user_profile:
        from dashboard_user.models import Task
        backlog_tasks_queryset = Task.objects.filter(
            user_active_backlog=user_profile,
            completed=False
        ).select_related('project', 'stage').order_by('order', 'created_at')[:5]
        
        # Prepare tasks with status information
        today = timezone.now().date()
        week_from_now = today + timedelta(days=7)
        for task in backlog_tasks_queryset:
            task_dict = {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'deadline': task.deadline,
                'priority': task.priority,
                'completed': task.completed,
                'project': task.project,
                'is_overdue': task.deadline and task.deadline < today if task.deadline else False,
                'is_due_this_week': task.deadline and task.deadline <= week_from_now if task.deadline else False,
            }
            backlog_tasks.append(task_dict)
    
    # Get user credit and coins (placeholder values - these would come from a payment/wallet system)
    user_credit = getattr(user_profile, 'account_balance', 0.00) if user_profile else 0.00  # USD balance
    user_coins = getattr(user_profile, 'coins_balance', 0) if user_profile else 0  # Virtual coins
    
    # Get user's projects (owned projects only, exclude pending assignments)
    user_projects = []
    if user_profile:
        from dashboard_user.models import Project
        user_projects = Project.objects.filter(
            project_owner=user_profile
        ).exclude(assignment_status='assigned').select_related('template', 'supervised_by', 'supervised_by__user').order_by('-created_at')[:6]  # Limit to 6 for dashboard
    
    # Get mentor relationships for the mentor selection modal
    mentor_relationships = []
    if user_profile:
        mentor_relationships = MentorClientRelationship.objects.filter(
            client=user_profile,
            confirmed=True
        ).select_related('mentor', 'mentor__user').order_by('-created_at')
    
    # Activate user timezone so template |date shows upcoming session times in user's selected timezone
    user_tzinfo_activate = None
    if user_profile:
        try:
            from zoneinfo import ZoneInfo
            from datetime import timezone as dt_timezone
            utz = user_profile.selected_timezone or user_profile.detected_timezone or user_profile.time_zone or 'UTC'
            user_tzinfo_activate = ZoneInfo(str(utz))
        except Exception:
            from datetime import timezone as dt_timezone
            user_tzinfo_activate = dt_timezone.utc
    if user_tzinfo_activate:
        timezone.activate(user_tzinfo_activate)
    try:
        return render(request, 'dashboard_user/dashboard_user.html', {
            'upcoming_sessions': upcoming_sessions,
            'has_more_sessions': has_more_sessions,
            'backlog_tasks': backlog_tasks,
            'user_credit': user_credit,
            'user_coins': user_coins,
            'user_projects': user_projects,
            'mentor_relationships': mentor_relationships,
        })
    finally:
        timezone.deactivate()

@login_required
def profile(request):
    """User profile page - for editing profile information (first name, last name, profile picture)"""
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing user dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'user':
        return redirect('general:index')
    
    user = request.user
    profile = user.profile
    
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "update_picture":
            if 'profile_picture' in request.FILES:
                # Delete old profile picture if it exists
                if profile.profile_picture:
                    old_picture = profile.profile_picture
                    # Delete the file from storage using storage API
                    if old_picture.name:
                        old_picture.storage.delete(old_picture.name)
                    # Clear the field reference
                    profile.profile_picture = None
                    profile.save(update_fields=['profile_picture'])
                
                # Save new profile picture
                profile.profile_picture = request.FILES['profile_picture']
                profile.save()
            return redirect("/dashboard/user/profile/")
        
        elif action == "update_profile":
            # Update basic fields
            first_name = request.POST.get("first_name")
            last_name = request.POST.get("last_name")
            time_zone = request.POST.get("time_zone")
            instagram_name = request.POST.get("instagram_name")
            linkedin_name = request.POST.get("linkedin_name")
            personal_website = request.POST.get("personal_website")
            video_introduction_url = request.POST.get("video_introduction_url")
            
            if first_name is not None:
                profile.first_name = first_name
            if last_name is not None:
                profile.last_name = last_name
            if instagram_name is not None:
                profile.instagram_name = (instagram_name or '').strip() or None
            if linkedin_name is not None:
                profile.linkedin_name = (linkedin_name or '').strip() or None
            if personal_website is not None:
                profile.personal_website = (personal_website or '').strip() or None
            if video_introduction_url is not None:
                profile.video_introduction_url = (video_introduction_url or '').strip() or None
            
            # Store old timezone before updating
            old_selected_timezone = profile.selected_timezone
            
            if time_zone is not None:
                profile.selected_timezone = time_zone
                # Also update legacy time_zone field for backward compatibility
                profile.time_zone = time_zone
            
            profile.save()
            
            # Send email if timezone was changed (not first time setting)
            # Condition: old_selected_timezone was not empty AND it's different from new one
            if old_selected_timezone and old_selected_timezone.strip() and old_selected_timezone != time_zone and time_zone:
                try:
                    from general.email_service import EmailService
                    EmailService.send_timezone_change_email(
                        user=request.user,
                        new_timezone=time_zone,
                        old_timezone=old_selected_timezone
                    )
                except Exception as e:
                    # Log error but don't fail the request
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error sending timezone change email: {str(e)}")
            return redirect("/dashboard/user/profile/")
    
    # Compute profile completion percentage
    filled = 0
    total = 0
    missing_fields = []

    def consider(value, field_name, display_name):
        nonlocal filled, total
        total += 1
        if value:
            filled += 1
        else:
            missing_fields.append(display_name)

    consider(profile.first_name, 'first_name', 'First Name')
    consider(profile.last_name, 'last_name', 'Last Name')
    consider(user.email, 'email', 'Email')
    timezone_value = profile.selected_timezone or profile.time_zone
    consider(timezone_value, 'time_zone', 'Time Zone')
    consider(profile.profile_picture, 'profile_picture', 'Profile Picture')
    
    profile_completion = int(round((filled / total) * 100)) if total else 0

    return render(request, 'dashboard_user/profile.html', {
        'user': user,
        'profile': profile,
        'profile_completion': profile_completion,
        'missing_fields': missing_fields,
    })

@login_required
def account(request):
    """User account page - for account settings (email change with verification, password change, name updates)"""
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing user dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'user':
        return redirect('general:index')

    user = request.user
    profile = user.profile

    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "update_name":
            # Update basic name fields
            first_name = request.POST.get("first_name")
            last_name = request.POST.get("last_name")
            if first_name is not None:
                profile.first_name = first_name
            if last_name is not None:
                profile.last_name = last_name
            profile.save()
            messages.success(request, 'Name updated successfully!')
            return redirect("/dashboard/user/account/")
        
        elif action == "update_password":
            # Handle password change
            new_password = request.POST.get("new_password")
            new_password_again = request.POST.get("new_password_again")
            if new_password and new_password_again and new_password == new_password_again:
                from django.contrib.auth import update_session_auth_hash
                from general.email_service import EmailService

                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                
                # Send password changed confirmation email
                try:
                    EmailService.send_password_changed_email(user)
                except Exception as e:
                    # Log error but don't fail the request
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error sending password changed email: {str(e)}")
                
                messages.success(request, 'Password updated successfully!')
            else:
                messages.error(request, 'Passwords do not match.')
            return redirect("/dashboard/user/account/")

    return render(request, 'dashboard_user/account.html', {
        'user': user,
        'profile': profile,
    })

@login_required
def settings_view(request):
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing user dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'user':
        return redirect('general:index')
    
    user = request.user
    profile = user.profile
    
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "update_timezone":
            time_zone = request.POST.get("time_zone", "")
            
            # Store old timezone before updating
            old_selected_timezone = profile.selected_timezone
            
            if time_zone:
                profile.selected_timezone = time_zone
                # Also update legacy time_zone field for backward compatibility
                profile.time_zone = time_zone
                profile.confirmed_timezone_mismatch = False
            
            profile.save()
            
            # Send email if timezone was changed (not first time setting)
            # Condition: old_selected_timezone was not empty AND it's different from new one
            if old_selected_timezone and old_selected_timezone.strip() and old_selected_timezone != time_zone and time_zone:
                try:
                    from general.email_service import EmailService
                    EmailService.send_timezone_change_email(
                        user=request.user,
                        new_timezone=time_zone,
                        old_timezone=old_selected_timezone
                    )
                except Exception as e:
                    # Log error but don't fail the request
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error sending timezone change email: {str(e)}")
            
            messages.success(request, "Timezone updated successfully.")
            return redirect("/dashboard/user/settings/")
    
    return render(
        request,
        'dashboard_user/settings.html',
        {
            'debug': settings.DEBUG,
        },
    )

@login_required
def support_view(request):
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing user dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'user':
        return redirect('general:index')
    
    from general.forms import TicketForm
    from general.models import Ticket
    
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.save()
            
            # Send email to admin
            from general.email_service import EmailService
            try:
                EmailService.send_ticket_created_email(ticket)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Error sending ticket created email: {str(e)}')
            
            messages.success(request, 'Your support ticket has been submitted successfully. We will get back to you soon!')
            return redirect('general:dashboard_user:support')
    else:
        form = TicketForm()
    
    # Get user's tickets
    user_tickets = Ticket.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    return render(
        request,
        'dashboard_user/support.html',
        {
            'debug': settings.DEBUG,
            'form': form,
            'user_tickets': user_tickets,
        },
    )


@login_required
def ticket_detail(request, ticket_id):
    """View ticket details and add comments"""
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing user dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'user':
        return redirect('general:index')
    
    from general.models import Ticket, TicketComment
    from general.forms import TicketCommentForm
    from general.email_service import EmailService
    from accounts.models import CustomUser
    
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_comment':
            form = TicketCommentForm(request.POST, request.FILES)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.ticket = ticket
                comment.user = request.user
                comment.save()
                
                # Send email to admin and create notification for all admins
                try:
                    EmailService.send_ticket_comment_email(ticket, comment, request.user)
                    
                    # Create notification for all admin users
                    admin_users = CustomUser.objects.filter(
                        is_active=True,
                        admin_profile__isnull=False
                    )
                    from general.models import Notification
                    import uuid
                    batch_id = uuid.uuid4()
                    
                    from django.urls import reverse
                    from general.email_service import EmailService
                    user_name = ticket.user.profile.first_name if hasattr(ticket.user, 'profile') and ticket.user.profile and ticket.user.profile.first_name else ticket.user.email.split('@')[0]
                    ticket_url = f"{EmailService.get_site_domain()}{reverse('general:dashboard_admin:ticket_detail', args=[ticket.id])}"
                    for admin_user in admin_users:
                        Notification.objects.create(
                            user=admin_user,
                            batch_id=batch_id,
                            target_type='single',
                            title=f"New comment on ticket #{ticket.id}",
                            description=f"{user_name} added a comment to ticket: {ticket.title}. <a href=\"{ticket_url}\" style=\"color: #10b981; text-decoration: underline;\">View ticket</a>"
                        )
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f'Error sending ticket comment email: {str(e)}')
                
                messages.success(request, 'Your comment has been added.')
                return redirect('general:dashboard_user:ticket_detail', ticket_id=ticket.id)
    
    form = TicketCommentForm()
    comments = ticket.comments.all().order_by('created_at')
    
    return render(
        request,
        'dashboard_user/ticket_detail.html',
        {
            'ticket': ticket,
            'form': form,
            'comments': comments,
        },
    )

@login_required
def my_sessions(request):
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing user dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'user':
        return redirect('general:index')
    
    from general.models import Session
    from django.utils import timezone
    from zoneinfo import ZoneInfo
    from datetime import timezone as dt_timezone
    
    # Display timezone: prefer selected_timezone (same as dashboard and booking modal)
    user_profile = request.user.profile
    user_timezone = user_profile.selected_timezone or user_profile.detected_timezone or user_profile.time_zone or 'UTC'
    user_tzinfo = None
    try:
        user_tzinfo = ZoneInfo(str(user_timezone))
    except Exception:
        user_tzinfo = dt_timezone.utc
    
    now = timezone.now()
    
    # Get all upcoming sessions where user is an attendee (invited and confirmed)
    initial_sessions = []
    try:
        all_upcoming = Session.objects.filter(
            attendees=request.user,
            status__in=['invited', 'confirmed'],
            start_datetime__gte=now
        ).order_by('start_datetime').prefetch_related('attendees', 'mentors__user')
        
        # Get first 10 sessions for initial load
        sessions_queryset = all_upcoming[:10]
        
        # Format sessions for template
        for session in sessions_queryset:
            first_mentor = session.mentors.select_related('user').first()
            mentor_name = 'Mentor'
            if first_mentor:
                mentor_name = f"{first_mentor.first_name} {first_mentor.last_name}".strip() or (first_mentor.user.email.split('@')[0] if getattr(first_mentor, 'user', None) else 'Mentor')
            
            # Convert to user's timezone
            start_datetime_local = session.start_datetime
            end_datetime_local = session.end_datetime
            try:
                start_datetime_local = session.start_datetime.astimezone(user_tzinfo)
                end_datetime_local = session.end_datetime.astimezone(user_tzinfo)
            except Exception:
                pass
            
            initial_sessions.append({
                'id': session.id,
                'start_datetime': start_datetime_local,
                'end_datetime': end_datetime_local,
                'status': session.status,
                'mentor_name': mentor_name,
                'note': session.note,
            })
    except Exception as e:
        # Log error but don't fail the request
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching initial sessions: {str(e)}")
    
    # Activate user timezone so template |date filter shows times in user's selected timezone
    try:
        if user_tzinfo:
            timezone.activate(user_tzinfo)
    except Exception:
        pass
    try:
        return render(request, 'dashboard_user/my_sessions.html', {
            'initial_sessions': initial_sessions,
            'user_timezone': user_timezone,
        })
    finally:
        timezone.deactivate()


@login_required
def get_sessions_paginated(request):
    """API endpoint for paginated sessions (infinite scroll) for users"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        from general.models import Session
        from django.utils import timezone
        from django.core.paginator import Paginator
        from zoneinfo import ZoneInfo
        from datetime import timezone as dt_timezone
        
        # Get user's timezone
        user_profile = request.user.profile
        user_timezone = user_profile.selected_timezone or user_profile.detected_timezone or user_profile.time_zone or 'UTC'
        user_tzinfo = None
        try:
            user_tzinfo = ZoneInfo(str(user_timezone))
        except Exception:
            user_tzinfo = dt_timezone.utc
        
        # Get pagination parameters
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 10))
        
        now = timezone.now()
        
        # Get all upcoming sessions where user is an attendee (invited and confirmed)
        all_upcoming = Session.objects.filter(
            attendees=request.user,
            status__in=['invited', 'confirmed'],
            start_datetime__gte=now
        ).order_by('start_datetime').prefetch_related('attendees', 'mentors__user')
        
        # Paginate
        paginator = Paginator(all_upcoming, per_page)
        page_obj = paginator.get_page(page)
        
        # Format sessions for JSON response
        sessions_data = []
        for session in page_obj:
            first_mentor = session.mentors.select_related('user').first()
            mentor_name = 'Mentor'
            if first_mentor:
                mentor_name = f"{first_mentor.first_name} {first_mentor.last_name}".strip() or (first_mentor.user.email.split('@')[0] if getattr(first_mentor, 'user', None) else 'Mentor')
            
            # Convert to user's timezone for JSON response
            start_dt = session.start_datetime
            end_dt = session.end_datetime
            try:
                start_dt = session.start_datetime.astimezone(user_tzinfo)
                end_dt = session.end_datetime.astimezone(user_tzinfo)
            except Exception:
                pass
            
            sessions_data.append({
                'id': session.id,
                'start_datetime': start_dt.isoformat(),
                'end_datetime': end_dt.isoformat(),
                'status': session.status,
                'mentor_name': mentor_name,
                'note': session.note or '',
            })
        
        return JsonResponse({
            'success': True,
            'sessions': sessions_data,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'current_page': page,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching paginated sessions: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def mentors_list(request):
    """Display list of all mentors for the logged-in user"""
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing user dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'user':
        return redirect('general:index')
    
    from accounts.models import MentorClientRelationship
    from general.models import Review
    
    user_profile = request.user.user_profile
    relationships = MentorClientRelationship.objects.filter(
        client=user_profile
    ).select_related('mentor', 'mentor__user').order_by('-created_at')
    
    # Get published reviews for each mentor
    mentor_ids = [rel.mentor.id for rel in relationships]
    published_reviews = Review.objects.filter(
        client=user_profile,
        mentor_id__in=mentor_ids,
        status='published'
    ).values_list('mentor_id', flat=True)
    
    # Create a set for quick lookup
    mentors_with_reviews = set(published_reviews)
    
    # Add review status to each relationship
    for relationship in relationships:
        relationship.has_published_review = relationship.mentor.id in mentors_with_reviews
    
    return render(request, 'dashboard_user/mentors.html', {
        'relationships': relationships,
    })


@login_required
def session_invitation(request, token: str):
    """
    Validates session invitation token and redirects to session management page
    which shows all pending invitations and changes.
    """
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing user dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'user':
        return redirect('general:index')

    from general.models import SessionInvitation
    inv = SessionInvitation.objects.select_related('session', 'mentor', 'mentor__user').filter(token=token).first()
    if not inv:
        messages.error(request, 'Invalid or expired session invitation link.')
        return redirect('general:dashboard_user:session_management')

    # Expired/cancelled
    if inv.cancelled_at:
        messages.error(request, 'This session invitation is no longer valid.')
        return redirect('general:dashboard_user:session_management')
    if inv.is_expired():
        messages.error(request, 'This session invitation has expired. Please ask your mentor to resend it.')
        return redirect('general:dashboard_user:session_management')

    # Ensure correct user is logged in
    user_email = (request.user.email or '').strip().lower()
    invited_email = (inv.invited_email or '').strip().lower()
    if (inv.invited_user and inv.invited_user_id != request.user.id) or (invited_email and invited_email != user_email):
        logout(request)
        messages.warning(request, f'This invitation is for {inv.invited_email}. Please log in with that account.')
        return redirect(f"/accounts/login/?next=/dashboard/user/session-invitation/{token}/")

    # Valid token and user - redirect to session management to see all invitations and changes
    return redirect('general:dashboard_user:session_management')


@login_required
def session_management(request):
    """
    Page for clients to manage all session invitations and changes.
    Shows invitations and changes separately, allows confirm/decline for each.
    """
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing user dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'user':
        return redirect('general:index')
    
    from general.models import Session, SessionInvitation
    from accounts.models import MentorClientRelationship
    from django.contrib.auth import logout
    
    user_email = (request.user.email or '').strip().lower()
    
    # Get user's timezone for converting session times
    user_profile = request.user.profile
    user_timezone = user_profile.selected_timezone or user_profile.detected_timezone or user_profile.time_zone or 'UTC'
    user_tzinfo = None
    try:
        from zoneinfo import ZoneInfo
        user_tzinfo = ZoneInfo(str(user_timezone))
    except Exception:
        from datetime import timezone as dt_timezone
        user_tzinfo = dt_timezone.utc
    
    # Get all pending invitations for this user
    # Filter out invitations for expired sessions
    invitations = SessionInvitation.objects.filter(
        invited_email=user_email,
        cancelled_at__isnull=True,
        accepted_at__isnull=True,
        session__status__in=['invited', 'confirmed']  # Only show invitations for non-expired sessions
    ).select_related('session', 'mentor', 'mentor__user').order_by('-created_at')
    
    # Calculate duration in minutes and convert times to user's timezone for each invitation
    for inv in invitations:
        if inv.session.start_datetime and inv.session.end_datetime:
            duration = inv.session.end_datetime - inv.session.start_datetime
            inv.session.duration_minutes = int(duration.total_seconds() / 60)
            
            # Convert to user's timezone
            try:
                inv.session.start_datetime_local = inv.session.start_datetime.astimezone(user_tzinfo)
                inv.session.end_datetime_local = inv.session.end_datetime.astimezone(user_tzinfo)
            except Exception:
                inv.session.start_datetime_local = inv.session.start_datetime
                inv.session.end_datetime_local = inv.session.end_datetime
        else:
            inv.session.duration_minutes = 0
            inv.session.start_datetime_local = None
            inv.session.end_datetime_local = None
    
    # Get all sessions linked to this user (via attendees OR via invitations)
    # First, get session IDs from invitations
    invitation_session_ids = set(invitations.values_list('session_id', flat=True))
    
    # Get all sessions where user is an attendee
    attendee_sessions = Session.objects.filter(attendees=request.user).prefetch_related('mentors__user')
    attendee_session_ids = set(attendee_sessions.values_list('id', flat=True))
    
    # Combine all session IDs (needed for both GET and POST)
    all_user_session_ids = invitation_session_ids | attendee_session_ids
    
    # Get all sessions with pending changes
    # Check both previous_data/changes_requested_by AND original_data/changed_by
    # IMPORTANT: Exclude sessions that are 'invited' and have an active invitation
    # (those should only appear in the invitations list, not as changes)
    changed_sessions = []
    if all_user_session_ids:
        all_user_sessions = Session.objects.filter(id__in=all_user_session_ids).prefetch_related('mentors', 'mentors__user')
        
        for session in all_user_sessions:
            # Skip expired sessions
            if session.status == 'expired':
                continue
            
            # Skip sessions that are 'invited' and have an active invitation
            # These should only appear as invitations, not as changes
            if session.status == 'invited' and session.id in invitation_session_ids:
                continue
            
            has_pending_change = False
            change_data = None
            
            # Check for previous_data/changes_requested_by (primary fields)
            if session.previous_data and session.changes_requested_by == 'mentor':
                has_pending_change = True
                change_data = session.previous_data
            # Also check original_data/changed_by (alternative fields)
            elif session.original_data and session.changed_by == 'mentor':
                has_pending_change = True
                change_data = session.original_data
            
            if has_pending_change and change_data:
                # Parse ISO datetime strings from change_data to timezone-aware datetime objects for template
                if isinstance(change_data, dict):
                    from datetime import datetime
                    from django.utils import timezone as dj_timezone
                    try:
                        if 'start_datetime' in change_data and isinstance(change_data['start_datetime'], str):
                            dt = datetime.fromisoformat(change_data['start_datetime'].replace('Z', '+00:00'))
                            if dt.tzinfo is None:
                                dt = dj_timezone.make_aware(dt)
                            change_data['start_datetime'] = dt
                        if 'end_datetime' in change_data and isinstance(change_data['end_datetime'], str):
                            dt = datetime.fromisoformat(change_data['end_datetime'].replace('Z', '+00:00'))
                            if dt.tzinfo is None:
                                dt = dj_timezone.make_aware(dt)
                            change_data['end_datetime'] = dt
                    except Exception:
                        pass
                # Store the change data in the appropriate field for template access
                # Use previous_data if it exists, otherwise use original_data
                if session.previous_data:
                    session.previous_data = change_data
                else:
                    session.original_data = change_data
                
                # Check which fields actually changed
                date_changed = False
                price_changed = False
                
                if change_data:
                    from django.utils import timezone as dj_timezone
                    from datetime import timezone as dt_timezone
                    # Check if date/time changed
                    old_start_parsed = None
                    old_end_parsed = None
                    
                    if 'start_datetime' in change_data and change_data['start_datetime']:
                        old_start = change_data['start_datetime']
                        if isinstance(old_start, str):
                            try:
                                old_start_parsed = datetime.fromisoformat(old_start.replace('Z', '+00:00'))
                                if old_start_parsed.tzinfo is None:
                                    old_start_parsed = dj_timezone.make_aware(old_start_parsed)
                                # Normalize to UTC for comparison
                                if old_start_parsed.tzinfo:
                                    old_start_parsed = old_start_parsed.astimezone(dt_timezone.utc)
                            except:
                                old_start_parsed = None
                        elif isinstance(old_start, datetime):
                            old_start_parsed = old_start
                            if old_start_parsed.tzinfo is None:
                                old_start_parsed = dj_timezone.make_aware(old_start_parsed)
                            if old_start_parsed.tzinfo:
                                old_start_parsed = old_start_parsed.astimezone(dt_timezone.utc)
                    
                    if 'end_datetime' in change_data and change_data['end_datetime']:
                        old_end = change_data['end_datetime']
                        if isinstance(old_end, str):
                            try:
                                old_end_parsed = datetime.fromisoformat(old_end.replace('Z', '+00:00'))
                                if old_end_parsed.tzinfo is None:
                                    old_end_parsed = dj_timezone.make_aware(old_end_parsed)
                                # Normalize to UTC for comparison
                                if old_end_parsed.tzinfo:
                                    old_end_parsed = old_end_parsed.astimezone(dt_timezone.utc)
                            except:
                                old_end_parsed = None
                        elif isinstance(old_end, datetime):
                            old_end_parsed = old_end
                            if old_end_parsed.tzinfo is None:
                                old_end_parsed = dj_timezone.make_aware(old_end_parsed)
                            if old_end_parsed.tzinfo:
                                old_end_parsed = old_end_parsed.astimezone(dt_timezone.utc)
                    
                    # Compare datetimes only if we successfully parsed them
                    if old_start_parsed is not None:
                        new_start_normalized = session.start_datetime
                        if new_start_normalized.tzinfo:
                            new_start_normalized = new_start_normalized.astimezone(dt_timezone.utc)
                        if old_start_parsed != new_start_normalized:
                            date_changed = True
                    
                    if old_end_parsed is not None:
                        new_end_normalized = session.end_datetime
                        if new_end_normalized.tzinfo:
                            new_end_normalized = new_end_normalized.astimezone(dt_timezone.utc)
                        if old_end_parsed != new_end_normalized:
                            date_changed = True
                    
                    # Check if price changed
                    old_price = change_data.get('session_price')
                    new_price = session.session_price
                    
                    # Normalize for comparison: handle None, empty string, and numeric values
                    # Convert to comparable format (float or None)
                    def normalize_price(price):
                        if price is None:
                            return None
                        if price == '':
                            return None
                        try:
                            return float(price)
                        except (ValueError, TypeError):
                            return None
                    
                    old_price_normalized = normalize_price(old_price)
                    new_price_normalized = normalize_price(new_price)
                    
                    # Only mark as changed if values are actually different
                    if old_price_normalized != new_price_normalized:
                        price_changed = True
                
                # Add flags to session object for template (no underscore for Django template access)
                session.date_changed = date_changed
                session.price_changed = price_changed
                
                # Calculate duration in minutes
                if session.start_datetime and session.end_datetime:
                    duration = session.end_datetime - session.start_datetime
                    session.duration_minutes = int(duration.total_seconds() / 60)
                    
                    # Convert to user's timezone
                    try:
                        session.start_datetime_local = session.start_datetime.astimezone(user_tzinfo)
                        session.end_datetime_local = session.end_datetime.astimezone(user_tzinfo)
                    except Exception:
                        session.start_datetime_local = session.start_datetime
                        session.end_datetime_local = session.end_datetime
                else:
                    session.duration_minutes = 0
                    session.start_datetime_local = None
                    session.end_datetime_local = None
                
                # Also convert change_data datetimes to user's timezone
                if change_data and isinstance(change_data, dict):
                    try:
                        if 'start_datetime' in change_data and change_data['start_datetime']:
                            if isinstance(change_data['start_datetime'], datetime):
                                change_data['start_datetime_local'] = change_data['start_datetime'].astimezone(user_tzinfo)
                        if 'end_datetime' in change_data and change_data['end_datetime']:
                            if isinstance(change_data['end_datetime'], datetime):
                                change_data['end_datetime_local'] = change_data['end_datetime'].astimezone(user_tzinfo)
                    except Exception:
                        pass
                
                changed_sessions.append(session)
    
    changed_sessions.sort(key=lambda s: s.start_datetime, reverse=True)
    
    # Handle POST requests for confirm/decline
    if request.method == 'POST':
        action = request.POST.get('action')
        session_id = request.POST.get('session_id')
        invitation_id = request.POST.get('invitation_id')
        
        try:
            if action == 'confirm_change' and session_id:
                if all_user_session_ids:
                    try:
                        session = Session.objects.get(id=session_id, id__in=all_user_session_ids)
                        # Clear both sets of change tracking fields, set status to confirmed
                        session.previous_data = None
                        session.changes_requested_by = None
                        session.original_data = None
                        session.changed_by = None
                        session.status = 'confirmed'
                        session.save()
                        session.ensure_meeting_url()
                        messages.success(request, f'Session #{session_id} changes confirmed.')
                    except Session.DoesNotExist:
                        messages.error(request, 'Session not found.')
                else:
                    messages.error(request, 'Session not found.')
            
            elif action == 'decline_change' and session_id:
                if all_user_session_ids:
                    try:
                        session = Session.objects.get(id=session_id, id__in=all_user_session_ids)
                        # Clear both sets of change tracking fields, set status to cancelled
                        session.previous_data = None
                        session.changes_requested_by = None
                        session.original_data = None
                        session.changed_by = None
                        session.status = 'cancelled'
                        session.save()
                        messages.success(request, f'Session #{session_id} changes declined.')
                    except Session.DoesNotExist:
                        messages.error(request, 'Session not found.')
                else:
                    messages.error(request, 'Session not found.')
            
            elif action == 'confirm_invitation' and invitation_id:
                inv = invitations.filter(id=invitation_id).first()
                if inv:
                    session = inv.session
                    try:
                        session.attendees.add(request.user)
                    except Exception:
                        pass
                    session.status = 'confirmed'
                    session.save()
                    session.ensure_meeting_url()
                    inv.accepted_at = timezone.now()
                    inv.save()
                    
                    # Mark first session as scheduled if not already
                    if inv.mentor and user_profile:
                        relationship = MentorClientRelationship.objects.filter(
                            mentor=inv.mentor,
                            client=user_profile
                        ).first()
                        if relationship and not relationship.first_session_scheduled:
                            relationship.first_session_scheduled = True
                            relationship.save(update_fields=['first_session_scheduled'])
                    
                    messages.success(request, 'Session invitation confirmed.')
            
            elif action == 'decline_invitation' and invitation_id:
                inv = invitations.filter(id=invitation_id).first()
                if inv:
                    inv.cancelled_at = timezone.now()
                    inv.save()
                    if inv.session:
                        inv.session.status = 'cancelled'
                        inv.session.save()
                    messages.success(request, 'Session invitation declined.')
            
            elif action == 'confirm_all':
                # Confirm all invitations
                confirmed_count = 0
                for inv in invitations:
                    session = inv.session
                    try:
                        session.attendees.add(request.user)
                    except Exception:
                        pass
                    session.status = 'confirmed'
                    session.save()
                    session.ensure_meeting_url()
                    inv.accepted_at = timezone.now()
                    inv.save()
                    
                    # Mark first session as scheduled if not already
                    if inv.mentor and user_profile:
                        relationship = MentorClientRelationship.objects.filter(
                            mentor=inv.mentor,
                            client=user_profile
                        ).first()
                        if relationship and not relationship.first_session_scheduled:
                            relationship.first_session_scheduled = True
                            relationship.save(update_fields=['first_session_scheduled'])
                    
                    confirmed_count += 1
                
                # Confirm all changes
                for session in changed_sessions:
                    # Clear both sets of change tracking fields
                    session.previous_data = None
                    session.changes_requested_by = None
                    session.original_data = None
                    session.changed_by = None
                    session.status = 'confirmed'
                    session.save()
                    session.ensure_meeting_url()
                    confirmed_count += 1
                
                if confirmed_count > 0:
                    messages.success(request, f'Confirmed {confirmed_count} session(s).')
            
            return redirect('general:dashboard_user:session_management')
        except Exception as e:
            messages.error(request, f'Error processing request: {str(e)}')
            return redirect('general:dashboard_user:session_management')
    
    pending_count = len(invitations) + len(changed_sessions)
    
    return render(request, 'dashboard_user/session_management.html', {
        'invitations': invitations,
        'changed_sessions': changed_sessions,
        'pending_count': pending_count,
    })


@require_POST
def create_booking_payment_intent(request):
    """
    Create a Stripe PaymentIntent for a paid booking (no confirmation).
    Frontend must call confirmCardPayment(client_secret) then book_session(payment_intent_id).
    Handles 3DS / SCA.
    """
    try:
        from billing.services.payment_service import (
            create_booking_payment_intent as billing_create_pi,
            session_price_cents,
            BillingError,
        )
        data = json.loads(request.body)
        mentor_id = data.get('mentor_id')
        slot_key = (data.get('slot_key') or '').strip()
        attempt_id = (data.get('attempt_id') or '').strip()
        is_logged_in = data.get('is_logged_in', False)
        email = (data.get('email') or '').strip().lower() if not is_logged_in else None

        if not mentor_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing mentor_id.',
            }, status=400)

        try:
            mentor_user = CustomUser.objects.get(id=mentor_id)
            mentor_profile = mentor_user.mentor_profile
        except (CustomUser.DoesNotExist, AttributeError):
            return JsonResponse({'success': False, 'error': 'Mentor not found'}, status=404)

        amount_cents = session_price_cents(mentor_profile)
        if amount_cents <= 0:
            return JsonResponse({'success': False, 'error': 'This session has no price set.'}, status=400)

        if is_logged_in:
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'User not authenticated'}, status=401)
            if hasattr(request.user, 'mentor_profile'):
                return JsonResponse({'success': False, 'error': 'Mentors cannot book sessions.'}, status=400)
            try:
                user_profile = request.user.profile
            except AttributeError:
                return JsonResponse({'success': False, 'error': 'User profile not found'}, status=400)
            relationship = MentorClientRelationship.objects.filter(
                mentor=mentor_profile,
                client=user_profile
            ).first()
            is_first_session = relationship is None or not relationship.first_session_scheduled
            if mentor_profile.first_session_free and is_first_session:
                return JsonResponse({
                    'success': False,
                    'error': 'No payment required for your first session with this mentor.',
                }, status=400)
            client_email = request.user.email
            client_id = user_profile.id
        else:
            if not email:
                return JsonResponse({'success': False, 'error': 'Email is required.'}, status=400)
            import re
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
                return JsonResponse({'success': False, 'error': 'Invalid email format.'}, status=400)
            if mentor_profile.first_session_free:
                return JsonResponse({
                    'success': False,
                    'error': 'No payment required for your first session with this mentor.',
                }, status=400)
            client_email = email
            client_id = None
            is_first_session = True

        try:
            result = billing_create_pi(
                amount_cents=amount_cents,
                mentor_profile=mentor_profile,
                client_email=client_email or '',
                client_id=client_id,
                is_first_session=is_first_session,
                session_description=f"Session with {mentor_profile.first_name} {mentor_profile.last_name}",
                slot_key=slot_key or None,
                attempt_id=attempt_id or None,
            )
        except BillingError as e:
            return JsonResponse({'success': False, 'error': e.message}, status=400)

        return JsonResponse({
            'success': True,
            'payment_intent_id': result['payment_intent_id'],
            'client_secret': result['client_secret'],
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error('create_booking_payment_intent: %s', e, exc_info=True)
        return JsonResponse({'success': False, 'error': 'An error occurred.'}, status=500)


@require_POST
def book_session(request):
    """
    Book a session from the booking modal.
    Handles both logged-in users and non-logged-in users (new and existing).
    For paid sessions, pass payment_intent_id (after frontend confirmCardPayment).
    """
    try:
        from datetime import datetime
        from django.utils.crypto import get_random_string
        from general.models import Session, SessionInvitation
        from general.email_service import EmailService
        from zoneinfo import ZoneInfo
        from datetime import timezone as dt_timezone
        
        data = json.loads(request.body)
        mentor_id = data.get('mentor_id')
        start_datetime_str = data.get('start_datetime')
        end_datetime_str = data.get('end_datetime')
        adjusted_end_datetime_str = data.get('adjusted_end_datetime')  # For first session with different length
        availability_slot_id = data.get('availability_slot_id')
        recurring_id = data.get('recurring_id')
        instance_date = data.get('instance_date')
        is_logged_in = data.get('is_logged_in', False)
        
        # For non-logged-in users
        email = data.get('email', '').strip().lower() if not is_logged_in else None
        note = data.get('note', '').strip() if not is_logged_in else ''
        timezone_str = data.get('timezone', 'UTC') if not is_logged_in else None
        
        # Validation
        if not mentor_id or not start_datetime_str or not end_datetime_str:
            return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)
        
        if not availability_slot_id and not (recurring_id and instance_date):
            return JsonResponse({'success': False, 'error': 'Missing availability slot information'}, status=400)
        
        # Get mentor profile
        try:
            mentor_user = CustomUser.objects.get(id=mentor_id)
            mentor_profile = mentor_user.mentor_profile
        except (CustomUser.DoesNotExist, AttributeError):
            return JsonResponse({'success': False, 'error': 'Mentor not found'}, status=404)
        
        # Parse datetimes
        try:
            start_dt = datetime.fromisoformat(start_datetime_str.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_datetime_str.replace('Z', '+00:00'))
            
            # Use adjusted end datetime if provided (for first session with different length)
            if adjusted_end_datetime_str:
                end_dt = datetime.fromisoformat(adjusted_end_datetime_str.replace('Z', '+00:00'))
            
            if start_dt.tzinfo is None:
                start_dt = timezone.make_aware(start_dt)
            if end_dt.tzinfo is None:
                end_dt = timezone.make_aware(end_dt)
            
            # Ensure UTC
            if start_dt.tzinfo != dt_timezone.utc:
                start_dt = start_dt.astimezone(dt_timezone.utc)
            if end_dt.tzinfo != dt_timezone.utc:
                end_dt = end_dt.astimezone(dt_timezone.utc)
            
            # Validate future
            if start_dt <= timezone.now():
                return JsonResponse({'success': False, 'error': 'Cannot book sessions in the past'}, status=400)
            
            if end_dt <= start_dt:
                return JsonResponse({'success': False, 'error': 'Invalid session duration'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Invalid datetime format: {str(e)}'}, status=400)
        
        # Calculate duration
        duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
        
        # Determine user and first session status
        # IMPORTANT: Check user/email BEFORE updating availability slots
        # This prevents slots from being removed if booking should fail
        user = None
        user_profile = None
        is_first_session = False
        is_free_session = False
        session_length_minutes = mentor_profile.session_length or 60
        is_new_user_account = False  # Track if we created a new user account
        
        if is_logged_in:
            # Logged-in user
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'error': 'User not authenticated'}, status=401)
            
            # Check if user is mentor
            if hasattr(request.user, 'mentor_profile'):
                return JsonResponse({'success': False, 'error': 'Mentors cannot book sessions with other mentors'}, status=400)
            
            user = request.user
            try:
                user_profile = user.profile
            except AttributeError:
                return JsonResponse({'success': False, 'error': 'User profile not found'}, status=400)
            
            # Check first session free
            relationship = MentorClientRelationship.objects.filter(
                mentor=mentor_profile,
                client=user_profile
            ).first()
            
            is_first_session = relationship is None or not relationship.first_session_scheduled
            
            if is_first_session and mentor_profile.first_session_free:
                price = Decimal('0')
                session_length_minutes = mentor_profile.first_session_length or 30
                is_free_session = True
            else:
                price = mentor_profile.price_per_session or Decimal('0')
                is_free_session = False
            
            # Use user's timezone for email
            user_timezone = user_profile.selected_timezone or user_profile.detected_timezone or user_profile.time_zone or 'UTC'
        else:
            # Not logged in - need email
            if not email:
                return JsonResponse({'success': False, 'error': 'Email is required'}, status=400)
            
            # Validate email format
            import re
            email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not re.match(email_regex, email):
                return JsonResponse({'success': False, 'error': 'Invalid email format'}, status=400)
            
            # Check if user exists
            existing_user = CustomUser.objects.filter(email=email).first()
            
            if existing_user:
                # Existing user - return special error to preserve booking info
                if hasattr(existing_user, 'mentor_profile'):
                    return JsonResponse({'success': False, 'error': 'This email belongs to a mentor account. Please use a different email.'}, status=400)
                
                # Return error indicating account exists, with preserved booking info
                # IMPORTANT: Return early - do NOT proceed with booking or remove availability slot
                return JsonResponse({
                    'success': False,
                    'error': 'account_exists',
                    'message': 'Account with this email already exists',
                    'preserved_data': {
                        'email': email,
                        'note': note,
                        'start_datetime': start_datetime_str,
                        'end_datetime': end_datetime_str,
                        'adjusted_end_datetime': adjusted_end_datetime_str,
                        'availability_slot_id': availability_slot_id,
                        'recurring_id': recurring_id,
                        'instance_date': instance_date,
                        'mentor_id': mentor_id,
                        'timezone': timezone_str
                    }
                }, status=400)
            else:
                # New user
                # Validate timezone
                if not timezone_str or timezone_str == 'UTC':
                    timezone_str = 'UTC'
                else:
                    try:
                        ZoneInfo(timezone_str)
                    except Exception:
                        timezone_str = 'UTC'
                
                # Check first session free (no relationship exists yet)
                if mentor_profile.first_session_free:
                    price = Decimal('0')
                    session_length_minutes = mentor_profile.first_session_length or 30
                    is_free_session = True
                else:
                    price = mentor_profile.price_per_session or Decimal('0')
                    is_free_session = False
                
                # Create user account
                temp_password = get_random_string(32)
                user = CustomUser.objects.create_user(
                    email=email,
                    password=temp_password,
                    is_email_verified=False,
                    is_active=True
                )
                
                user_profile = UserProfile.objects.create(
                    user=user,
                    first_name='',
                    last_name='',
                    role='user',
                    selected_timezone=timezone_str,
                    detected_timezone=timezone_str,
                    time_zone=timezone_str
                )
                
                user_timezone = timezone_str
                is_first_session = True
                is_new_user_account = True
        
        # Payment (Phase 2): require verified payment_intent_id when price > 0 (frontend confirms via confirmCardPayment)
        payment_intent_id = None
        if price > 0:
            from billing.services.payment_service import (
                verify_payment_intent_succeeded,
                session_price_cents,
                BillingError,
            )
            payment_intent_id = (data.get('payment_intent_id') or '').strip()
            if not payment_intent_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Payment is required. Please complete the payment step (card and 3D Secure if shown) then try again.',
                }, status=400)
            amount_cents = session_price_cents(mentor_profile)
            if amount_cents <= 0:
                return JsonResponse({'success': False, 'error': 'This session has no price set.'}, status=400)
            try:
                result = verify_payment_intent_succeeded(
                    payment_intent_id=payment_intent_id,
                    expected_amount_cents=amount_cents,
                    expected_mentor_id=str(mentor_profile.user.id),
                )
                price = Decimal(result['amount_cents']) / 100
            except BillingError as e:
                return JsonResponse({'success': False, 'error': e.message}, status=400)
        
        # NOW handle availability slot - only after we've confirmed the booking can proceed (and payment if any)
        # This ensures slots aren't removed if the booking should fail
        try:
            if availability_slot_id:
                # One-time slot: delete it
                slots = list(mentor_profile.one_time_slots or [])
                before_len = len(slots)
                slots = [s for s in slots if str(s.get('id', '')) != str(availability_slot_id)]
                if len(slots) == before_len:
                    return JsonResponse({'success': False, 'error': 'This availability slot is no longer available. Please refresh and try again.'}, status=400)
                mentor_profile.one_time_slots = slots
                mentor_profile.save(update_fields=['one_time_slots'])
            elif recurring_id and instance_date:
                # Recurring slot: add to booked_dates
                rules = list(mentor_profile.recurring_slots or [])
                updated = False
                for r in rules:
                    if str(r.get('id', '')) == str(recurring_id):
                        booked = r.get('booked_dates') or []
                        if not isinstance(booked, list):
                            booked = []
                        if instance_date not in booked:
                            booked.append(instance_date)
                        r['booked_dates'] = booked
                        updated = True
                        break
                if not updated:
                    return JsonResponse({'success': False, 'error': 'This availability series is no longer available. Please refresh and try again.'}, status=400)
                mentor_profile.recurring_slots = rules
                mentor_profile.save(update_fields=['recurring_slots'])
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Could not update availability: {str(e)}'}, status=500)
        
        # Create session
        # Store note in first_lesson_user_note if it's the first session, otherwise in note
        session_note = ''
        first_lesson_note = None
        if is_first_session and note:
            first_lesson_note = note
        elif note:
            session_note = note
        
        session = Session.objects.create(
            start_datetime=start_dt,
            end_datetime=end_dt,
            note=session_note,
            first_lesson_user_note=first_lesson_note,
            session_type='individual',
            status='confirmed',
            session_price=price,
            tasks=[],
            created_by=mentor_user,  # Set created_by to mentor user
        )
        session.ensure_meeting_url()
        mentor_profile.sessions.add(session)
        
        if user:
            session.attendees.add(user)
        
        # Link Payment to Session (Phase 3.1): webhook creates Payment; we only attach session.
        # Only update when session is not yet set (idempotent: retries do not overwrite).
        if payment_intent_id:
            from billing.models import Payment
            Payment.objects.filter(
                stripe_payment_intent_id=payment_intent_id,
                session__isnull=True,
            ).update(session=session)
        
        # Create or update relationship - automatically confirm since user booked a session
        relationship = MentorClientRelationship.objects.filter(
            mentor=mentor_profile,
            client=user_profile
        ).first()
        
        if not relationship:
            # Create confirmed relationship since user booked a session
            relationship = MentorClientRelationship.objects.create(
                mentor=mentor_profile,
                client=user_profile,
                status='confirmed',
                confirmed=True,
                verified_at=timezone.now(),
                invitation_token=None,  # No invitation token needed for booking-created relationships
                first_session_scheduled=True  # Mark that first session has been scheduled
            )
            # Add to mentor's clients ManyToMany relationship
            if user_profile not in mentor_profile.clients.all():
                mentor_profile.clients.add(user_profile)
        else:
            # Update existing relationship to confirmed if not already
            update_fields = []
            if not relationship.confirmed or relationship.status != 'confirmed':
                relationship.status = 'confirmed'
                relationship.confirmed = True
                if not relationship.verified_at:
                    relationship.verified_at = timezone.now()
                relationship.invitation_token = None  # Clear invitation token
                update_fields.extend(['status', 'confirmed', 'verified_at', 'invitation_token'])
            
            # Mark first session as scheduled if not already
            if not relationship.first_session_scheduled:
                relationship.first_session_scheduled = True
                update_fields.append('first_session_scheduled')
            
            if update_fields:
                relationship.save(update_fields=update_fields)
            
            # Ensure it's in the ManyToMany relationship
            if user_profile not in mentor_profile.clients.all():
                mentor_profile.clients.add(user_profile)
        
        # Note: We don't create SessionInvitation for confirmed sessions
        # The session is already confirmed, so no invitation/confirmation needed
        
        # Send confirmation email
        try:
            EmailService.send_session_booking_confirmation_email(
                session=session,
                mentor_profile=mentor_profile,
                user=user,
                user_timezone=user_timezone,
                is_free_session=is_free_session,
                first_session_length=session_length_minutes if is_free_session else None,
                regular_session_length=mentor_profile.session_length or 60
            )
        except Exception as e:
            # Log error but don't fail the booking
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Error sending booking confirmation email: {str(e)}')
        
        # Send verification email for new users
        if is_new_user_account:
            try:
                from django.utils.http import urlsafe_base64_encode
                from django.utils.encoding import force_bytes
                from django.contrib.auth.tokens import default_token_generator
                
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                site_domain = EmailService.get_site_domain()
                verify_url = f"{site_domain}/accounts/verify/{uid}/{token}/"
                
                EmailService.send_verification_email(user, verify_url)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Error sending verification email: {str(e)}')
        
        # Get email for response
        user_email = user.email if user else email
        
        response_data = {
            'success': True,
            'message': 'Session booked successfully',
            'session_id': session.id,
            'email': user_email,
            'is_new_user': is_new_user_account,
        }
        if payment_intent_id:
            response_data['payment_intent_id'] = payment_intent_id
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error booking session: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'}, status=500)


@login_required
def booking_modal_partial(request, mentor_user_id):
    """Return booking modal HTML for a specific mentor (for dashboard use)"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        mentor_user = get_object_or_404(CustomUser, id=mentor_user_id)
        mentor_profile = mentor_user.mentor_profile
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Mentor not found'}, status=404)
    
    # Check if it's first session
    is_first_session = True
    try:
        user_profile = request.user.user_profile
        relationship = MentorClientRelationship.objects.filter(
            mentor=mentor_profile,
            client=user_profile
        ).first()
        is_first_session = relationship is None or not relationship.first_session_scheduled
    except Exception:
        is_first_session = True
    
    # Get Stripe publishable key
    from django.conf import settings
    stripe_publishable_key = getattr(settings, "STRIPE_PUBLISHABLE_KEY", "") or ""
    
    # Debug: Check availability data
    import logging
    logger = logging.getLogger(__name__)
    try:
        one_time_slots = mentor_profile.one_time_slots or []
        recurring_slots = mentor_profile.recurring_slots or []
        logger.info(f'Booking modal partial - Mentor {mentor_user_id}: one_time_slots={len(one_time_slots)}, recurring_slots={len(recurring_slots)}')
    except Exception as e:
        logger.error(f'Error getting availability data: {e}')
    
    # Render booking modal partial
    html = render_to_string('dashboard_user/popups/booking_modal.html', {
        'request': request,
        'user': request.user,
        'mentor_user': mentor_user,
        'mentor_profile': mentor_profile,
        'is_first_session': is_first_session,
        'stripe_publishable_key': stripe_publishable_key,
    })
    
    return JsonResponse({
        'success': True,
        'html': html
    })


@login_required
def notification_list(request):
    """List all notifications for the logged-in user with pagination"""
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing user dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'user':
        return redirect('general:index')
    
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    paginator = Paginator(notifications, 20)  # 20 notifications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    unread_count = Notification.objects.filter(user=request.user, is_opened=False).count()
    
    return render(request, 'dashboard_user/notifications.html', {
        'page_obj': page_obj,
        'notifications': page_obj,
        'unread_count': unread_count,
    })


@login_required
def notification_detail(request, notification_id):
    """Display notification detail and mark as opened"""
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing user dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'user':
        return redirect('general:index')
    
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    
    # Mark as opened when viewing detail page
    if not notification.is_opened:
        notification.is_opened = True
        notification.save()
    
    return render(request, 'dashboard_user/notification_detail.html', {
        'notification': notification,
    })


@login_required
@require_POST
def notification_mark_read(request, notification_id):
    """Mark a single notification as read"""
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing user dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'user':
        return redirect('general:index')
    
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_opened = True
    notification.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('general:dashboard_user:notification_detail', notification_id=notification_id)


@login_required
@require_POST
def notification_mark_all_read(request):
    """Mark all notifications as read for the logged-in user"""
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing user dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'user':
        return redirect('general:index')
    
    Notification.objects.filter(user=request.user, is_opened=False).update(is_opened=True)
    
    messages.success(request, 'All notifications marked as read.')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('general:dashboard_user:notification_list')


@login_required
@require_http_methods(["GET", "POST"])
def notification_modal_detail(request, notification_id):
    """View for modal popup - returns notification details and marks as opened"""
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing user dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'user':
        return redirect('general:index')
    
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    
    # Mark as opened when viewing in modal
    if not notification.is_opened:
        notification.is_opened = True
        notification.save()
    
    if request.method == 'POST':
        # If POST, return JSON for AJAX requests
        return JsonResponse({
            'success': True,
            'notification': {
                'id': notification.id,
                'title': notification.title,
                'description': notification.description,
                'created_at': notification.created_at.isoformat(),
                'is_opened': notification.is_opened,
            }
        })
    
    # If GET, return HTML template for modal content
    return render(request, 'general/notifications/modal_content.html', {
        'notification': notification,
    })


# ============================================================================
# REVIEWS SYSTEM
# ============================================================================

@login_required
def mentor_detail(request, mentor_id):
    """User's view of a specific mentor detail page"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return redirect('general:index')
    
    user_profile = request.user.user_profile
    mentor_user = get_object_or_404(CustomUser, id=mentor_id)
    
    try:
        mentor_profile = mentor_user.mentor_profile
    except AttributeError:
        messages.error(request, 'Mentor profile not found.')
        return redirect('general:dashboard_user:mentors_list')
    
    # Get relationship
    relationship = MentorClientRelationship.objects.filter(
        mentor=mentor_profile,
        client=user_profile
    ).first()
    
    # Get all sessions between user and mentor
    from general.models import Session
    sessions = mentor_profile.sessions.filter(
        attendees=request.user
    ).order_by('-start_datetime').prefetch_related('mentors__user')
    
    # Check if first session is completed
    has_completed_session = sessions.filter(status='completed').exists()
    
    # Get review if exists
    from general.models import Review
    review = Review.objects.filter(
        mentor=mentor_profile,
        client=user_profile
    ).select_related('reply').first()
    
    return render(request, 'dashboard_user/mentor_detail.html', {
        'mentor_user': mentor_user,
        'mentor_profile': mentor_profile,
        'relationship': relationship,
        'sessions': sessions,
        'has_completed_session': has_completed_session,
        'review': review,
    })


@login_required
def write_review(request, mentor_id, uid, token):
    """User review writing page (from email link) - redirects to mentor detail page"""
    # Simply redirect to mentor detail page where review can be written
    # The mentor_detail page already has all the review functionality
    return redirect('general:dashboard_user:mentor_detail', mentor_id=mentor_id)


@login_required
def create_edit_review(request, review_id=None):
    """AJAX endpoint for user to create or edit review"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    # Only allow POST and PUT methods
    if request.method not in ['POST', 'PUT']:
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    user_profile = request.user.user_profile
    
    try:
        data = json.loads(request.body)
        mentor_id = data.get('mentor_id')
        rating = data.get('rating')
        text = data.get('text', '').strip()
        publish = data.get('publish', False)  # Flag to publish immediately
    except json.JSONDecodeError:
        mentor_id = request.POST.get('mentor_id')
        rating = request.POST.get('rating')
        text = request.POST.get('text', '').strip()
        publish = request.POST.get('publish', 'false').lower() == 'true'
    
    if not mentor_id:
        return JsonResponse({'success': False, 'error': 'Mentor ID is required'}, status=400)
    
    try:
        mentor_user = CustomUser.objects.get(id=mentor_id)
        mentor_profile = mentor_user.mentor_profile
    except (CustomUser.DoesNotExist, AttributeError):
        return JsonResponse({'success': False, 'error': 'Mentor not found'}, status=404)
    
    # Validate rating
    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            return JsonResponse({'success': False, 'error': 'Rating must be between 1 and 5'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid rating'}, status=400)
    
    if not text:
        return JsonResponse({'success': False, 'error': 'Review text is required'}, status=400)
    
    # Check relationship
    relationship = MentorClientRelationship.objects.filter(
        mentor=mentor_profile,
        client=user_profile
    ).first()
    
    if not relationship:
        return JsonResponse({'success': False, 'error': 'No relationship found'}, status=404)
    
    # Check if at least one session is completed
    from general.models import Session
    has_completed_session = mentor_profile.sessions.filter(
        attendees=request.user,
        status='completed'
    ).exists()
    
    if not has_completed_session:
        return JsonResponse({'success': False, 'error': 'You must complete at least one session before writing a review'}, status=400)
    
    # Create review (no updates allowed)
    from general.models import Review
    
    # Check if review already exists
    existing_review = Review.objects.filter(
        mentor=mentor_profile,
        client=user_profile
    ).first()
    
    if existing_review:
        return JsonResponse({'success': False, 'error': 'Review already exists. Please delete the existing review to create a new one.'}, status=400)
    
    # Create new review
    status = 'published' if publish else 'draft'
    review = Review.objects.create(
        mentor=mentor_profile,
        client=user_profile,
        rating=rating,
        text=text,
        status=status
    )
    
    # If published immediately, send email and notification
    if publish:
        # Update relationship
        relationship.review_provided = True
        relationship.save(update_fields=['review_provided'])
        
        mentor_name = f"{mentor_profile.first_name} {mentor_profile.last_name}"
        client_name = f"{user_profile.first_name} {user_profile.last_name}"
        
        # Generate secure link with token
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator
        from django.urls import reverse
        
        token = default_token_generator.make_token(review.mentor.user)
        uid = urlsafe_base64_encode(force_bytes(review.mentor.user.pk))
        site_domain = EmailService.get_site_domain()
        review_url = f"{site_domain}{reverse('general:dashboard_mentor:view_reviews_secure', args=[uid, token])}?logout=true"
        
        try:
            EmailService.send_email(
                subject=f"New review from {client_name}",
                recipient_email=review.mentor.user.email,
                template_name='review_published',
                context={
                    'mentor_name': mentor_name,
                    'client_name': client_name,
                    'rating': review.rating,
                    'review_text': review.text,
                    'review_url': review_url,
                }
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Error sending review published email: {str(e)}')
        
        # Create notification for mentor
        from general.models import Notification
        import uuid
        batch_id = uuid.uuid4()
        
        Notification.objects.create(
            user=review.mentor.user,
            batch_id=batch_id,
            target_type='single',
            title=f"New review from {client_name}",
            description=f"{client_name} published a {review.rating}-star review. <a href=\"{review_url}\" style=\"color: #10b981; text-decoration: underline;\">View review</a>"
        )
    
    return JsonResponse({
        'success': True,
        'message': 'Review published successfully' if publish else 'Review saved successfully',
        'review': {
            'id': review.id,
            'rating': review.rating,
            'text': review.text,
            'status': review.status,
        }
    })


@login_required
@require_POST
def publish_review(request, review_id):
    """AJAX endpoint for user to publish review"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    user_profile = request.user.user_profile
    
    from general.models import Review
    review = get_object_or_404(Review, id=review_id, client=user_profile)
    
    # Check if at least one session is completed
    from general.models import Session
    has_completed_session = Session.objects.filter(
        mentors=review.mentor,
        attendees=request.user,
        status='completed'
    ).exists()
    
    if not has_completed_session:
        return JsonResponse({'success': False, 'error': 'You must complete at least one session before publishing a review'}, status=400)
    
    # Publish review
    review.status = 'published'
    review.save()
    
    # Update relationship
    relationship = MentorClientRelationship.objects.filter(
        mentor=review.mentor,
        client=user_profile
    ).first()
    
    if relationship:
        relationship.review_provided = True
        relationship.save(update_fields=['review_provided'])
    
    # Send email to mentor
    mentor_name = f"{review.mentor.first_name} {review.mentor.last_name}"
    client_name = f"{user_profile.first_name} {user_profile.last_name}"
    
    # Generate secure link with token
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.contrib.auth.tokens import default_token_generator
    from django.urls import reverse
    
    token = default_token_generator.make_token(review.mentor.user)
    uid = urlsafe_base64_encode(force_bytes(review.mentor.user.pk))
    site_domain = EmailService.get_site_domain()
    review_url = f"{site_domain}{reverse('general:dashboard_mentor:view_reviews_secure', args=[uid, token])}?logout=true"
    
    try:
        EmailService.send_email(
            subject=f"New review from {client_name}",
            recipient_email=review.mentor.user.email,
            template_name='review_published',
            context={
                'mentor_name': mentor_name,
                'client_name': client_name,
                'rating': review.rating,
                'review_text': review.text,
                'review_url': review_url,
            }
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error sending review published email: {str(e)}')
    
    # Create notification for mentor
    from general.models import Notification
    import uuid
    batch_id = uuid.uuid4()
    
    Notification.objects.create(
        user=review.mentor.user,
        batch_id=batch_id,
        target_type='single',
        title=f"New review from {client_name}",
        description=f"{client_name} published a {review.rating}-star review. <a href=\"{review_url}\" style=\"color: #10b981; text-decoration: underline;\">View review</a>"
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Review published successfully',
        'review': {
            'id': review.id,
            'status': review.status,
            'published_at': review.published_at.isoformat() if review.published_at else None,
        }
    })


@login_required
@require_POST
def delete_review(request, review_id):
    """AJAX endpoint for user to delete review"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    user_profile = request.user.user_profile
    
    from general.models import Review
    review = get_object_or_404(Review, id=review_id, client=user_profile)
    
    # Get relationship and mentor info before deleting
    relationship = MentorClientRelationship.objects.filter(
        mentor=review.mentor,
        client=user_profile
    ).first()
    
    # Store info for email/notification before deleting
    mentor_profile = review.mentor
    mentor_name = f"{mentor_profile.first_name} {mentor_profile.last_name}"
    client_name = f"{user_profile.first_name} {user_profile.last_name}"
    was_published = review.status == 'published'
    review_rating = review.rating
    
    # Store info for email/notification before deleting
    mentor_profile = review.mentor
    mentor_name = f"{mentor_profile.first_name} {mentor_profile.last_name}"
    client_name = f"{user_profile.first_name} {user_profile.last_name}"
    was_published = review.status == 'published'
    review_rating = review.rating
    
    # Delete review (cascade deletes reply)
    review.delete()
    
    # Update relationship
    if relationship:
        relationship.review_provided = False
        relationship.save(update_fields=['review_provided'])
    
    # Send email to mentor if review was published
    if was_published:
        # Generate secure link with token
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator
        from django.urls import reverse
        
        token = default_token_generator.make_token(mentor_profile.user)
        uid = urlsafe_base64_encode(force_bytes(mentor_profile.user.pk))
        site_domain = EmailService.get_site_domain()
        review_url = f"{site_domain}{reverse('general:dashboard_mentor:view_reviews_secure', args=[uid, token])}?logout=true"
        
        try:
            EmailService.send_email(
                subject=f"Review deleted by {client_name}",
                recipient_email=mentor_profile.user.email,
                template_name='review_deleted',
                context={
                    'mentor_name': mentor_name,
                    'client_name': client_name,
                    'review_url': review_url,
                }
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Error sending review deleted email: {str(e)}')
        
        # Create notification for mentor
        from general.models import Notification
        import uuid
        batch_id = uuid.uuid4()
        
        Notification.objects.create(
            user=mentor_profile.user,
            batch_id=batch_id,
            target_type='single',
            title=f"Review deleted by {client_name}",
            description=f"{client_name} deleted their {review_rating}-star review."
        )
    
    return JsonResponse({
        'success': True,
        'message': 'Review deleted successfully'
    })


@login_required
def session_detail(request, session_id):
    """User's session detail page"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return redirect('general:index')
    
    user_profile = request.user.user_profile
    from general.models import Session
    
    # Get session where user is an attendee
    session = Session.objects.filter(
        id=session_id,
        attendees=request.user
    ).prefetch_related('mentors__user').first()
    
    if not session:
        messages.error(request, 'Session not found.')
        return redirect('general:dashboard_user:my_sessions')
    
    first_mentor = session.mentors.select_related('user').first()
    mentor_name = None
    mentor_email = None
    if first_mentor:
        mentor_name = f"{first_mentor.first_name} {first_mentor.last_name}".strip()
        mentor_email = getattr(first_mentor.user, 'email', None) if getattr(first_mentor, 'user', None) else None
    
    # Convert times to user's timezone
    user_timezone = user_profile.selected_timezone or user_profile.detected_timezone or user_profile.time_zone or 'UTC'
    start_local = None
    end_local = None
    
    try:
        from zoneinfo import ZoneInfo
        from datetime import timezone as dt_timezone
        tzinfo = ZoneInfo(str(user_timezone))
        start_local = session.start_datetime.astimezone(tzinfo) if session.start_datetime else None
        end_local = session.end_datetime.astimezone(tzinfo) if session.end_datetime else None
    except Exception:
        start_local = session.start_datetime
        end_local = session.end_datetime
    
    # Calculate duration
    duration_minutes = 0
    if session.start_datetime and session.end_datetime:
        duration = session.end_datetime - session.start_datetime
        duration_minutes = int(duration.total_seconds() / 60)
    
    return render(request, 'dashboard_user/session_detail.html', {
        'session': session,
        'mentor_name': mentor_name,
        'mentor_email': mentor_email,
        'user_timezone': user_timezone,
        'start_local': start_local,
        'end_local': end_local,
        'duration_minutes': duration_minutes,
    })


@login_required
def session_detail_api(request, session_id):
    """Return session detail as JSON for the session detail modal (user as attendee)."""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)
    from general.models import Session
    session = Session.objects.filter(
        id=session_id,
        attendees=request.user,
    ).prefetch_related('mentors__user').first()
    if not session:
        return JsonResponse({'success': False, 'error': 'Session not found'}, status=404)
    user_profile = request.user.user_profile
    user_tz_str = user_profile.selected_timezone or user_profile.detected_timezone or getattr(user_profile, 'time_zone', None) or 'UTC'
    start_local = None
    end_local = None
    try:
        from zoneinfo import ZoneInfo
        tzinfo = ZoneInfo(str(user_tz_str))
        start_local = session.start_datetime.astimezone(tzinfo).isoformat() if session.start_datetime else None
        end_local = session.end_datetime.astimezone(tzinfo).isoformat() if session.end_datetime else None
    except Exception:
        start_local = session.start_datetime.isoformat() if session.start_datetime else None
        end_local = session.end_datetime.isoformat() if session.end_datetime else None
    first_mentor = session.mentors.select_related('user').first()
    mentor_name = None
    mentor_email = None
    if first_mentor:
        mentor_name = f"{first_mentor.first_name} {first_mentor.last_name}".strip() or (getattr(first_mentor.user, 'email', '') or 'Mentor').split('@')[0]
        mentor_email = getattr(first_mentor.user, 'email', None) if getattr(first_mentor, 'user', None) else None
    duration_minutes = 0
    if session.start_datetime and session.end_datetime:
        duration_minutes = int((session.end_datetime - session.start_datetime).total_seconds() / 60)
    return JsonResponse({
        'success': True,
        'session': {
            'id': session.id,
            'status': session.status or 'draft',
            'mentor_name': mentor_name or 'Mentor',
            'mentor_email': mentor_email or '',
            'user_timezone': user_tz_str,
            'start_local': start_local,
            'end_local': end_local,
            'duration_minutes': duration_minutes,
            'meeting_url': getattr(session, 'meeting_url', None) or None,
            'note': session.note or '',
            'session_price': str(session.session_price) if session.session_price is not None else None,
            'session_type': getattr(session, 'session_type', None) or 'individual',
            'first_lesson_user_note': getattr(session, 'first_lesson_user_note', None) or '',
            'tasks': session.tasks if isinstance(getattr(session, 'tasks', None), list) else [],
        }
    })


@login_required
@require_POST
def cancel_session(request, session_id):
    """Client cancel: 1 attendee = cancel session and notify mentors. >1 attendees = leave_only: remove self from attendees and notify mentors + other attendees."""
    import logging
    import json
    logger = logging.getLogger(__name__)

    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)
    from general.models import Session
    session = Session.objects.filter(
        id=session_id,
        attendees=request.user,
        status__in=['invited', 'confirmed'],
    ).prefetch_related('mentors__user', 'attendees').first()
    if not session:
        return JsonResponse({'success': False, 'error': 'Session not found or cannot be cancelled'}, status=404)

    attendee_count = session.attendees.count()
    leave_only = False
    try:
        body = json.loads(request.body or '{}')
        leave_only = body.get('leave_only', False)
    except Exception:
        pass

    client_name = (getattr(request.user, 'get_full_name', lambda: '')() or '').strip()
    if not client_name:
        try:
            up = getattr(request.user, 'user_profile', None)
            if up is not None:
                client_name = f"{getattr(up, 'first_name', '')} {getattr(up, 'last_name', '')}".strip()
        except Exception:
            pass
    if not client_name:
        client_name = (getattr(request.user, 'email', None) or 'A client').strip()

    from django.utils.dateformat import DateFormat
    session_date = ''
    session_time = ''
    if getattr(session, 'start_datetime', None) and getattr(session, 'end_datetime', None):
        session_date = DateFormat(session.start_datetime).format('M d, Y')
        session_time = DateFormat(session.start_datetime).format('g:i A') + ' - ' + DateFormat(session.end_datetime).format('g:i A')

    # Multiple attendees: only "leave" is allowed (remove self); cancel whole session not supported from client
    if attendee_count > 1:
        if not leave_only:
            return JsonResponse({'success': False, 'error': 'Multiple attendees: confirm leave to remove yourself from this session.', 'require_leave_confirm': True}, status=400)
        # leave_only path
        session.attendees.remove(request.user)
        recipient_name_ctx = 'there'
        for mp in session.mentors.select_related('user').all():
            email = (getattr(mp.user, 'email', None) or '').strip()
            if email:
                try:
                    rname = f"{getattr(mp, 'first_name', '')} {getattr(mp, 'last_name', '')}".strip() or recipient_name_ctx
                    EmailService.send_email(
                        subject='Session update: client left',
                        recipient_email=email,
                        template_name='session_client_left_notification',
                        context={
                            'recipient_name': rname,
                            'client_name': client_name,
                            'session_id': session.id,
                            'session_date': session_date,
                            'session_time': session_time,
                        },
                        fail_silently=True,
                    )
                except Exception as e:
                    logger.exception('Session client left: email to mentor %s: %s', email, e)
        for att in session.attendees.all():
            email = (getattr(att, 'email', None) or '').strip()
            if email:
                try:
                    EmailService.send_email(
                        subject='Session update: participant left',
                        recipient_email=email,
                        template_name='session_client_left_notification',
                        context={
                            'recipient_name': 'there',
                            'client_name': client_name,
                            'session_id': session.id,
                            'session_date': session_date,
                            'session_time': session_time,
                        },
                        fail_silently=True,
                    )
                except Exception as e:
                    logger.exception('Session client left: email to attendee %s: %s', email, e)
        return JsonResponse({'success': True})

    # Single attendee: cancel whole session and notify all mentors
    session.status = 'cancelled'
    session.previous_data = None
    session.changes_requested_by = None
    session.save(update_fields=['status', 'previous_data', 'changes_requested_by'])

    try:
        session_price = str(session.session_price) if getattr(session, 'session_price', None) is not None else None
        start_date = end_date = start_time = end_time = ''
        if getattr(session, 'start_datetime', None) and getattr(session, 'end_datetime', None):
            try:
                from zoneinfo import ZoneInfo
                from django.utils.dateformat import DateFormat
                start_local = session.start_datetime
                end_local = session.end_datetime
                start_date = DateFormat(start_local).format('M d, Y')
                end_date = DateFormat(end_local).format('M d, Y')
                start_time = DateFormat(start_local).format('g:i A')
                end_time = DateFormat(end_local).format('g:i A')
            except Exception:
                start_date = str(session.start_datetime.date()) if session.start_datetime else ''
                end_date = str(session.end_datetime.date()) if session.end_datetime else ''
                start_time = str(session.start_datetime.time())[:5] if session.start_datetime else ''
                end_time = str(session.end_datetime.time())[:5] if session.end_datetime else ''

        recipients = []
        try:
            for mp in session.mentors.select_related('user').all():
                if not mp or not getattr(mp, 'user', None):
                    continue
                email = (getattr(mp.user, 'email', None) or '').strip()
                if email and not any(r[0] == email for r in recipients):
                    recipients.append((email, mp))
        except Exception:
            pass

        for mentor_email, mentor_profile_obj in recipients:
            mentor_name = 'there'
            tz_name = 'UTC'
            if mentor_profile_obj is not None:
                mentor_name = f"{getattr(mentor_profile_obj, 'first_name', '')} {getattr(mentor_profile_obj, 'last_name', '')}".strip() or mentor_name
                tz_name = getattr(mentor_profile_obj, 'selected_timezone', None) or getattr(mentor_profile_obj, 'detected_timezone', None) or getattr(mentor_profile_obj, 'time_zone', None) or 'UTC'

            if tz_name and getattr(session, 'start_datetime', None) and getattr(session, 'end_datetime', None):
                try:
                    from zoneinfo import ZoneInfo
                    from django.utils.dateformat import DateFormat
                    tzinfo = ZoneInfo(str(tz_name))
                    start_local = session.start_datetime.astimezone(tzinfo)
                    end_local = session.end_datetime.astimezone(tzinfo)
                    start_date = DateFormat(start_local).format('M d, Y')
                    end_date = DateFormat(end_local).format('M d, Y')
                    start_time = DateFormat(start_local).format('g:i A')
                    end_time = DateFormat(end_local).format('g:i A')
                except Exception:
                    pass

            try:
                EmailService.send_email(
                    subject='Session Cancelled by Client',
                    recipient_email=mentor_email,
                    template_name='session_cancelled_by_client_notification',
                    context={
                        'mentor_name': mentor_name,
                        'client_name': client_name,
                        'session_id': session.id,
                        'start_date': start_date,
                        'end_date': end_date,
                        'start_time': start_time,
                        'end_time': end_time,
                        'session_price': session_price,
                    },
                    fail_silently=True,
                )
            except Exception as e:
                logger.exception('Session cancelled by client: email failed to %s: %s', mentor_email, str(e))

        if not recipients:
            logger.warning('Session cancelled by client: no mentor email for session id=%s.', session_id)
    except Exception as e:
        logger.exception('Session cancelled by client: notify mentors failed: %s', str(e))

    return JsonResponse({'success': True})


def accept_project_assignment_secure(request, uidb64, token):
    """
    Secure link handler for project assignment emails.
    Ensures correct user is logged in before managing projects.
    Link always works, even after project acceptance/rejection.
    """
    user_id = None
    user = None
    token_valid = False
    
    # Try to validate token
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        try:
            user = CustomUser.objects.get(id=user_id)
            if default_token_generator.check_token(user, token):
                token_valid = True
        except CustomUser.DoesNotExist:
            # User doesn't exist, token invalid
            pass
    except Exception:
        # Token validation failed, but we'll still allow access if user is logged in
        pass
    
    # If token is valid, handle logout if requested
    if token_valid and request.GET.get('logout') == 'true' and request.user.is_authenticated:
        # Verify token matches current user
        try:
            if str(request.user.id) != user_id:
                logout(request)
                messages.info(request, 'Please log in with the correct account to manage your projects.')
        except Exception:
            logout(request)
            messages.info(request, 'Please log in to manage your projects.')
    
    # If token is valid, ensure correct user is logged in
    if token_valid:
        if not request.user.is_authenticated or request.user.id != user.id:
            messages.info(request, 'Please log in to manage your projects.')
            # Redirect directly to manage invitations page after login
            next_url = reverse("general:dashboard_user:manage_project_invitations")
            return redirect(f'/accounts/login/?next={quote(next_url)}')
    else:
        # Token invalid or expired - still allow access if user is logged in
        if not request.user.is_authenticated:
            messages.info(request, 'Please log in to manage your projects.')
            next_url = reverse("general:dashboard_user:manage_project_invitations")
            return redirect(f'/accounts/login/?next={quote(next_url)}')
    
    # Always redirect to manage invitations page (works even after acceptance/rejection)
    return redirect('general:dashboard_user:manage_project_invitations')


@login_required
@require_POST
def accept_project_assignment(request, project_id):
    """Client accepts project assignment (after authentication)"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    project = get_object_or_404(Project, id=project_id)
    
    # Verify user is the assigned client
    if project.project_owner != request.user.user_profile:
        return JsonResponse({'success': False, 'error': 'You are not authorized to accept this project.'}, status=403)
    
    # Accept the project
    project.assignment_status = 'accepted'
    project.assignment_token = None
    project.save()
    
    messages.success(request, f'Project "{project.title}" has been assigned to you!')
    return JsonResponse({
        'success': True,
        'message': f'Project "{project.title}" has been assigned to you!',
        'redirect_url': reverse('general:dashboard_user:project_detail', args=[project.id])
    })


@login_required
@require_POST
def reject_project_assignment(request, project_id):
    """Client rejects project assignment"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    project = get_object_or_404(Project, id=project_id)
    
    # Verify user is the assigned client
    if project.project_owner != request.user.user_profile:
        return JsonResponse({'success': False, 'error': 'You are not authorized to reject this project.'}, status=403)
    
    # Remove assignment
    project.project_owner = None
    project.assignment_status = 'pending'
    project.assignment_token = None
    project.save()
    
    messages.info(request, f'Project "{project.title}" assignment has been rejected.')
    return JsonResponse({
        'success': True,
        'message': f'Project "{project.title}" assignment has been rejected.'
    })


@login_required
def projects_list(request):
    """User's projects list page"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return redirect('general:index')
    
    user_profile = request.user.user_profile
    
    # Get all projects owned by this user (accepted + own projects)
    # Exclude pending assignments (those are shown on manage invitations page)
    all_projects = Project.objects.filter(
        project_owner=user_profile
    ).exclude(assignment_status='assigned').select_related('template', 'supervised_by', 'supervised_by__user').order_by('-created_at')
    
    # Get pending assignments count for badge
    pending_count = Project.objects.filter(
        project_owner=user_profile,
        assignment_status='assigned'
    ).count()
    
    # Get default templates for create project modal (no custom templates)
    from dashboard_user.models import ProjectTemplate
    default_templates = ProjectTemplate.objects.filter(author__isnull=True).order_by('name')
    
    context = {
        'projects': all_projects,
        'pending_count': pending_count,
        'default_templates': default_templates,
    }
    
    return render(request, 'dashboard_user/projects/projects_list.html', context)


@login_required
def manage_project_invitations(request):
    """Page for users to manage all pending project assignment invitations"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return redirect('general:index')
    
    user_profile = request.user.user_profile
    
    # Get all pending project assignments (assigned but not accepted)
    pending_projects = Project.objects.filter(
        project_owner=user_profile,
        assignment_status='assigned'
    ).select_related('template', 'supervised_by', 'supervised_by__user').order_by('-created_at')
    
    return render(request, 'dashboard_user/projects/manage_invitations.html', {
        'pending_projects': pending_projects,
        'pending_count': pending_projects.count(),
    })


@login_required
def project_detail(request, project_id):
    """User's project detail page (also accessible by mentors)"""
    project = get_object_or_404(
        Project.objects.select_related('template', 'supervised_by', 'project_owner'),
        id=project_id
    )
    
    # Check if user is the owner or the supervisor (mentor)
    is_owner = False
    is_supervisor = False
    
    if hasattr(request.user, 'profile'):
        if request.user.profile.role == 'user':
            user_profile = request.user.user_profile
            is_owner = (project.project_owner == user_profile)
        elif request.user.profile.role == 'mentor':
            mentor_profile = request.user.mentor_profile
            is_supervisor = (project.supervised_by == mentor_profile)
    
    # Only allow access if user is owner or supervisor
    if not (is_owner or is_supervisor):
        return redirect('general:index')
    
    # Handle POST requests (update/delete)
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            # Only project owner can edit/delete
            if not is_owner:
                return JsonResponse({'success': False, 'error': 'Only project owner can perform this action'}, status=403)
            
            if action == 'update':
                title = data.get('title', '').strip()
                description = data.get('description', '').strip()
                
                if not title:
                    return JsonResponse({'success': False, 'error': 'Project title is required'}, status=400)
                
                project.title = title
                project.description = description
                project.save()
                
                return JsonResponse({'success': True, 'message': 'Project updated successfully'})
            
            elif action == 'update_target_date':
                target_date_str = data.get('target_date')
                
                if target_date_str:
                    try:
                        from datetime import datetime
                        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
                        project.target_completion_date = target_date
                    except ValueError:
                        return JsonResponse({'success': False, 'error': 'Invalid date format'}, status=400)
                else:
                    project.target_completion_date = None
                
                project.save()
                return JsonResponse({'success': True, 'message': 'Target date updated successfully'})
            
            elif action == 'remove_supervisor':
                project.supervised_by = None
                project.save()
                return JsonResponse({'success': True, 'message': 'Supervisor removed successfully'})
            
            elif action == 'assign_supervisor':
                mentor_id = data.get('mentor_id')
                if not mentor_id:
                    return JsonResponse({'success': False, 'error': 'Mentor ID is required'}, status=400)
                
                try:
                    from accounts.models import MentorProfile
                    mentor_profile = MentorProfile.objects.get(id=mentor_id)
                    # Verify the user has a relationship with this mentor
                    from accounts.models import MentorClientRelationship
                    relationship = MentorClientRelationship.objects.filter(
                        mentor=mentor_profile,
                        client=user_profile,
                        confirmed=True
                    ).first()
                    
                    if not relationship:
                        return JsonResponse({'success': False, 'error': 'You do not have a relationship with this mentor'}, status=403)
                    
                    project.supervised_by = mentor_profile
                    project.save()
                    return JsonResponse({'success': True, 'message': 'Supervisor assigned successfully'})
                except MentorProfile.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Mentor not found'}, status=404)
            
            elif action == 'delete':
                project.delete()
                return JsonResponse({'success': True, 'message': 'Project deleted successfully'})
            
            else:
                return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Error in project_detail POST: {str(e)}', exc_info=True)
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    user_profile = getattr(request.user, 'user_profile', None)
    
    # Get questions for this project
    # If project has a template with questionnaire, get those questions
    questions = []
    answers = {}
    questionnaire_response = None
    
    if project.template and hasattr(project.template, 'questionnaire'):
        questionnaire = project.template.questionnaire
        questions = questionnaire.questions.all().order_by('order')
        
        # Get existing response if exists
        try:
            questionnaire_response = QuestionnaireResponse.objects.get(
                project=project,
                questionnaire=questionnaire
            )
            answers = questionnaire_response.answers
        except QuestionnaireResponse.DoesNotExist:
            pass
    
    # Get active modules
    active_modules = project.module_instances.filter(is_active=True).select_related('module').order_by('order')
    
    # Get stages
    stages = project.stages.all().order_by('order')
    
    # Get available mentors for project owner (if user is owner)
    available_mentors = []
    if is_owner and user_profile:
        from accounts.models import MentorClientRelationship
        relationships = MentorClientRelationship.objects.filter(
            client=user_profile,
            confirmed=True
        ).select_related('mentor', 'mentor__user').order_by('mentor__first_name', 'mentor__last_name')
        available_mentors = [rel.mentor for rel in relationships]
    
    # Calculate project progress for sidebar
    total_tasks = 0
    completed_tasks = 0
    for stage in stages:
        if not getattr(stage, 'is_disabled', False):
            # Get tasks in this stage
            from dashboard_user.models import Task
            stage_tasks = Task.objects.filter(stage=stage)
            total_tasks += stage_tasks.count()
            completed_tasks += stage_tasks.filter(completed=True).count()
    
    project_progress = 0
    if total_tasks > 0:
        project_progress = round((completed_tasks / total_tasks) * 100)
    
    context = {
        'project': project,
        'user_profile': user_profile,
        'questions': questions,
        'answers': answers,
        'questionnaire_completed': project.questionnaire_completed,
        'active_modules': active_modules,
        'stages': stages,
        'is_owner': is_owner,
        'is_supervisor': is_supervisor,
        'project_progress': project_progress,
        'available_mentors': available_mentors,
    }
    
    return render(request, 'dashboard_user/projects/project_detail.html', context)


@login_required
def module_detail(request, project_id, module_id):
    """Module detail page - default template for all modules"""
    from dashboard_user.models import ProjectModuleInstance
    
    project = get_object_or_404(
        Project.objects.select_related('template', 'supervised_by', 'project_owner'),
        id=project_id
    )
    
    # Check if user is the owner or the supervisor (mentor)
    is_owner = False
    is_supervisor = False
    
    if hasattr(request.user, 'profile'):
        if request.user.profile.role == 'user':
            user_profile = request.user.user_profile
            is_owner = (project.project_owner == user_profile)
        elif request.user.profile.role == 'mentor':
            mentor_profile = request.user.mentor_profile
            is_supervisor = (project.supervised_by == mentor_profile)
    
    # Only allow access if user is owner or supervisor
    if not (is_owner or is_supervisor):
        return redirect('general:index')
    
    module_instance = get_object_or_404(
        ProjectModuleInstance.objects.select_related('module'),
        id=module_id,
        project=project
    )
    
    context = {
        'project': project,
        'module_instance': module_instance,
        'is_owner': is_owner,
        'is_supervisor': is_supervisor,
    }
    
    return render(request, 'dashboard_user/projects/modules/module_detail.html', context)


@login_required
@require_POST
def submit_questionnaire(request, project_id):
    """Submit questionnaire answers for a project (accessible by owner or supervisor)"""
    project = get_object_or_404(Project, id=project_id)
    
    # Check if user is the owner or the supervisor (mentor)
    is_authorized = False
    if hasattr(request.user, 'profile'):
        if request.user.profile.role == 'user':
            is_authorized = (project.project_owner == request.user.user_profile)
        elif request.user.profile.role == 'mentor':
            is_authorized = (project.supervised_by == request.user.mentor_profile)
    
    if not is_authorized:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    # Get questionnaire for this project
    if not project.template or not hasattr(project.template, 'questionnaire'):
        return JsonResponse({'success': False, 'error': 'No questionnaire found for this template'}, status=400)
    
    questionnaire = project.template.questionnaire
    questions = questionnaire.questions.all().order_by('order')
    
    # Validate required questions
    errors = {}
    data = json.loads(request.body)
    answers_data = data.get('answers', {})
    
    for question in questions:
        if question.is_required:
            answer = answers_data.get(str(question.id), '').strip()
            if not answer:
                errors[str(question.id)] = f'This field is required.'
    
    if errors:
        return JsonResponse({'success': False, 'errors': errors}, status=400)
    
    # Save answers as JSON and extract special fields
    target_completion_date = None
    answers_dict = {}
    
    for question in questions:
        answer_text = answers_data.get(str(question.id), '').strip()
        if answer_text:
            answers_dict[str(question.id)] = answer_text
            
            # Extract target completion date if this is the target completion date question
            if question.is_target_date and question.question_type == 'date':
                try:
                    from datetime import datetime
                    target_completion_date = datetime.strptime(answer_text, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass
    
    # Create or update questionnaire response
    QuestionnaireResponse.objects.update_or_create(
        project=project,
        questionnaire=questionnaire,
        defaults={'answers': answers_dict}
    )
    
    # Mark questionnaire as completed and update target completion date
    from django.utils import timezone
    project.questionnaire_completed = True
    project.questionnaire_completed_at = timezone.now()
    if target_completion_date:
        project.target_completion_date = target_completion_date
    project.save()
    
    # Determine redirect URL based on user role
    if hasattr(request.user, 'profile') and request.user.profile.role == 'mentor':
        redirect_url = reverse('general:dashboard_mentor:project_detail', args=[project.id])
    else:
        redirect_url = reverse('general:dashboard_user:project_detail', args=[project.id])
    
    return JsonResponse({
        'success': True,
        'message': 'Questionnaire submitted successfully!',
        'redirect_url': redirect_url
    })


@login_required
def active_backlog(request):
    """Display user's active backlog"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return redirect('general:index')
    
    user_profile = request.user.user_profile
    
    # Get all tasks in user's active backlog
    tasks = Task.objects.filter(user_active_backlog=user_profile).order_by('order', 'created_at')
    
    # Calculate active and completed counts
    active_count = tasks.filter(completed=False).count()
    completed_count = tasks.filter(completed=True).count()
    total_tasks = tasks.count()
    
    # Also get tasks activated from stages (status='active', user_active_backlog=user_profile, still in stage)
    assigned_tasks = Task.objects.filter(status='active', user_active_backlog=user_profile, stage__isnull=False).order_by('-moved_to_active_backlog_at', 'order', 'created_at')
    
    # Get all mentors for filter
    relationships = MentorClientRelationship.objects.filter(
        client=user_profile,
        confirmed=True
    ).select_related('mentor', 'mentor__user').order_by('mentor__first_name', 'mentor__last_name')
    
    mentors = [rel.mentor for rel in relationships]
    
    # Get all projects owned by this user
    from dashboard_user.models import Project, ProjectStage
    projects = Project.objects.filter(project_owner=user_profile).select_related('supervised_by', 'template').order_by('-created_at')
    
    # Get stages for selected project (if any)
    selected_mentor_id = request.GET.get('mentor_id', '')
    selected_project_id = request.GET.get('project_id', '')
    stages = []
    
    if selected_project_id:
        try:
            project = projects.filter(id=int(selected_project_id)).first()
            if project:
                stages = ProjectStage.objects.filter(project=project).order_by('order', 'created_at')
        except (ValueError, TypeError):
            pass
    
    context = {
        'tasks': tasks,
        'assigned_tasks': assigned_tasks,
        'mentors': mentors,
        'projects': projects,
        'stages': stages,
        'selected_mentor_id': selected_mentor_id,
        'selected_project_id': selected_project_id,
        'active_count': active_count,
        'completed_count': completed_count,
        'total_tasks': total_tasks,
    }
    
    return render(request, 'dashboard_user/active_backlog.html', context)


@login_required
@require_POST
def create_active_backlog_task(request):
    """Create a new task in user's active backlog"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    user_profile = request.user.user_profile
    from dashboard_user.models import Task
    from decimal import Decimal
    
    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        if not title:
            return JsonResponse({'success': False, 'error': 'Task title is required'}, status=400)
        
        description = data.get('description', '').strip()
        deadline = data.get('deadline') or None
        priority = data.get('priority', 'medium')
        
        # Calculate order for the new task
        last_task = Task.objects.filter(user_active_backlog=user_profile).order_by('-order').first()
        if last_task:
            next_order = last_task.order + Decimal('10')
        else:
            next_order = Decimal('10')
        
        from django.utils import timezone
        task = Task.objects.create(
            user_active_backlog=user_profile,
            title=title,
            description=description,
            deadline=deadline,
            priority=priority,
            order=next_order,
            created_by=request.user,
            author_name=f"{request.user.profile.first_name} {request.user.profile.last_name}",
            author_email=request.user.email,
            author_role='client',
            moved_to_active_backlog_at=timezone.now()  # Set timestamp when created in active backlog
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Task created successfully',
            'task_id': task.id
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error creating active backlog task: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def edit_active_backlog_task(request, task_id):
    """Edit an existing task in user's active backlog"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    user_profile = request.user.user_profile
    from dashboard_user.models import Task
    
    task = get_object_or_404(Task, id=task_id, user_active_backlog=user_profile)
    
    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        if not title:
            return JsonResponse({'success': False, 'error': 'Task title is required'}, status=400)
        
        description = data.get('description', '').strip()
        deadline = data.get('deadline') or None
        priority = data.get('priority', 'medium')
        
        task.title = title
        task.description = description
        task.deadline = deadline
        task.priority = priority
        task.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Task updated successfully',
            'task': {
                'id': task.id,
                'title': task.title,
                'description': task.description or '',
                'deadline': task.deadline.strftime('%Y-%m-%d') if task.deadline else '',
                'priority': task.priority,
                'completed': task.completed,
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error editing active backlog task: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def toggle_active_backlog_task_complete(request, task_id):
    """Toggle completion status of a task in user's active backlog"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    user_profile = request.user.user_profile
    from dashboard_user.models import Task
    
    try:
        task = get_object_or_404(Task, id=task_id, user_active_backlog=user_profile)
        data = json.loads(request.body)
        completed = data.get('completed', False)
        
        if completed:
            # If task was activated from a stage, remove from active backlog but keep in stage
            if task.stage:
                task.complete_activated_task(user_profile)
            else:
                # Task was created directly in active backlog
                task.complete_active_backlog_task()
        else:
            # Uncomplete task
            task.completed = False
            task.status = 'active'
            task.completed_at = None
            task.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Task updated successfully',
            'completed': task.completed
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error toggling active backlog task: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def delete_active_backlog_task(request, task_id):
    """Delete a task from user's active backlog"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    user_profile = request.user.user_profile
    from dashboard_user.models import Task
    
    try:
        task = get_object_or_404(Task, id=task_id, user_active_backlog=user_profile)
        task.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Task deleted successfully'
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error deleting active backlog task: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def deactivate_active_backlog_task(request, task_id):
    """Deactivate a stage-linked task from user's active backlog"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    user_profile = request.user.user_profile
    from dashboard_user.models import Task
    
    try:
        task = get_object_or_404(Task, id=task_id, user_active_backlog=user_profile)
        
        # Only allow deactivation for stage-linked tasks
        if not task.stage:
            return JsonResponse({
                'success': False,
                'error': 'Cannot deactivate task created directly in active backlog'
            }, status=400)
        
        # Deactivate the task
        task.deactivate_task()
        
        return JsonResponse({
            'success': True,
            'message': 'Task deactivated successfully'
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error deactivating active backlog task: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def get_user_active_backlog_api(request):
    """API endpoint to get user's active backlog tasks"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        user_profile = request.user.user_profile
        from dashboard_user.models import Task, ProjectStage
        from django.utils import timezone
        from datetime import timedelta, date as date_type
        
        # Get filter parameter
        filter_status = request.GET.get('filter', 'todo')  # todo, completed, overdue
        
        # Get all tasks in user's active backlog (including stage-linked tasks)
        # Order by created_at descending (newest first), then by order
        tasks = Task.objects.filter(
            user_active_backlog=user_profile
        ).select_related('project', 'stage', 'stage__project').order_by('-created_at', 'order')
        
        # Calculate date thresholds
        today = timezone.now().date()
        
        # Apply filters
        if filter_status == 'todo':
            tasks = tasks.filter(completed=False)
        elif filter_status == 'completed':
            tasks = tasks.filter(completed=True)
        elif filter_status == 'overdue':
            tasks = tasks.filter(deadline__lt=today, completed=False)
        
        tasks_data = []
        for task in tasks:
            dl = task.deadline
            deadline_date = None
            if dl:
                if hasattr(dl, 'year'):
                    deadline_date = dl
                elif isinstance(dl, str) and len(dl) >= 10:
                    try:
                        deadline_date = date_type.fromisoformat(dl[:10])
                    except (ValueError, TypeError):
                        pass
            deadline_str = (deadline_date.strftime('%Y-%m-%d') if deadline_date else None) or (dl[:10] if isinstance(dl, str) and len(dl) >= 10 else None) if dl else None
            is_overdue = deadline_date and deadline_date < today and not task.completed if deadline_date else False
            
            # Get completed_at date for grouping
            completed_at_str = None
            if task.completed and task.completed_at:
                completed_at_str = task.completed_at.strftime('%Y-%m-%d')
            
            # Check if task is stage-linked
            has_stage = task.stage is not None
            stage_id = task.stage.id if task.stage else None
            stage_title = task.stage.title if task.stage else None
            project_id = None
            project_title = None
            
            if task.stage and task.stage.project:
                project_id = task.stage.project.id
                project_title = task.stage.project.title
            elif task.project:
                project_id = task.project.id
                project_title = task.project.title
            
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'description': task.description or '',
                'completed': task.completed,
                'deadline': deadline_str,
                'priority': task.priority,
                'status': task.status,
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'completed_at': completed_at_str,
                'order': float(task.order) if task.order is not None else 0.0,
                'is_overdue': is_overdue,
                'has_stage': has_stage,
                'stage_id': stage_id,
                'stage_title': stage_title,
                'project_id': project_id,
                'project_title': project_title,
            })
        
        # Calculate counts for all tasks (before filtering)
        all_tasks = Task.objects.filter(user_active_backlog=user_profile)
        todo_count = all_tasks.filter(completed=False).count()
        completed_count = all_tasks.filter(completed=True).count()
        overdue_count = all_tasks.filter(deadline__lt=today, completed=False).count()
        
        return JsonResponse({
            'success': True,
            'tasks': tasks_data,
            'todo_count': todo_count,
            'completed_count': completed_count,
            'overdue_count': overdue_count,
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error in get_user_active_backlog_api: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)


@login_required
def get_stages_api(request, project_id):
    """API endpoint to fetch stages for a project (for users)"""
    try:
        project = get_object_or_404(
            Project.objects.select_related('project_owner', 'supervised_by'),
            id=project_id
        )
        
        # Check if user is the owner or the supervisor (mentor)
        is_owner = False
        is_supervisor = False
        
        if hasattr(request.user, 'profile'):
            if request.user.profile.role == 'user':
                user_profile = request.user.user_profile
                is_owner = (project.project_owner == user_profile)
            elif request.user.profile.role == 'mentor':
                mentor_profile = request.user.mentor_profile
                is_supervisor = (project.supervised_by == mentor_profile)
        
        # Only allow access if user is owner or supervisor
        if not (is_owner or is_supervisor):
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        
        from dashboard_user.models import ProjectStage
        from datetime import datetime
        
        stages = project.stages.all().order_by('order')
        
        stages_data = []
        for stage in stages:
            # Format date for display (remove leading zero from day)
            target_date_display = None
            if stage.target_date:
                try:
                    target_date_display = stage.target_date.strftime('%b %d').replace(' 0', ' ')
                except Exception:
                    target_date_display = stage.target_date.strftime('%b %d')
            
            # Get task counts
            from dashboard_user.models import Task
            total_tasks = Task.objects.filter(stage=stage).count()
            completed_tasks = Task.objects.filter(stage=stage, completed=True).count()
            
            stages_data.append({
                'id': stage.id,
                'title': stage.title,
                'description': stage.description or '',
                'start_date': stage.start_date.strftime('%Y-%m-%d') if stage.start_date else None,
                'end_date': stage.end_date.strftime('%Y-%m-%d') if stage.end_date else None,
                'target_date': stage.target_date.strftime('%Y-%m-%d') if stage.target_date else None,
                'target_date_display': target_date_display,
                'is_completed': stage.is_completed,
                'is_pending_confirmation': stage.is_pending_confirmation,
                'progress_status': stage.progress_status,
                'is_disabled': stage.is_disabled,
                'tasks_total': total_tasks,
                'tasks_completed': completed_tasks,
            })
        
        return JsonResponse({
            'success': True,
            'stages': stages_data
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error in get_stages_api: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)


@login_required
def stage_detail(request, project_id, stage_id):
    """Display project stage detail for users"""
    project = get_object_or_404(
        Project.objects.select_related('project_owner', 'supervised_by'),
        id=project_id
    )
    
    # Check if user is the owner or the supervisor (mentor)
    is_owner = False
    is_supervisor = False
    
    if hasattr(request.user, 'profile'):
        if request.user.profile.role == 'user':
            user_profile = request.user.user_profile
            is_owner = (project.project_owner == user_profile)
        elif request.user.profile.role == 'mentor':
            mentor_profile = request.user.mentor_profile
            is_supervisor = (project.supervised_by == mentor_profile)
    
    # Only allow access if user is owner or supervisor
    if not (is_owner or is_supervisor):
        return redirect('general:index')
    
    from dashboard_user.models import ProjectStage, ProjectStageNote
    stage = get_object_or_404(ProjectStage, id=stage_id, project=project)
    
    # Update stage completion status based on tasks
    from dashboard_mentor.views import update_stage_completion_status
    update_stage_completion_status(stage)
    
    # Update progress status based on dates and tasks
    if not stage.is_disabled:
        stage.progress_status = stage.calculate_progress_status()
        stage.save()
    
    # Refresh stage from database to get updated status
    stage.refresh_from_db()
    
    # Handle POST actions (only for owner or supervisor)
    if request.method == "POST" and (is_owner or is_supervisor):
        if "note_text" in request.POST:
            note_text = request.POST.get("note_text", "").strip()
            if note_text:
                author_role = 'mentor' if is_supervisor else 'user'
                ProjectStageNote.objects.create(
                    stage=stage,
                    author=request.user,
                    text=note_text,
                    author_role=author_role
                )
                messages.success(request, "Note added.")
                return redirect('general:dashboard_user:stage_detail', project_id=project.id, stage_id=stage.id)
    
    # Get notes
    notes = stage.notes.all().select_related('author', 'author__mentor_profile', 'author__user_profile')
    
    # Get tasks for this stage
    from dashboard_user.models import Task
    tasks = stage.backlog_tasks.all().order_by('order', 'created_at')
    
    # Calculate active and completed task counts
    active_count = tasks.filter(completed=False).count()
    completed_count = tasks.filter(completed=True).count()
    
    context = {
        'project': project,
        'stage': stage,
        'notes': notes,
        'active_count': active_count,
        'completed_count': completed_count,
        'tasks': tasks,
        'is_owner': is_owner,
        'is_supervisor': is_supervisor,
    }
    
    return render(request, 'dashboard_user/projects/stage_detail.html', context)
