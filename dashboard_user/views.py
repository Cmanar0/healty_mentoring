from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from django.conf import settings
from accounts.models import MentorClientRelationship, MentorProfile, UserProfile, CustomUser
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from decimal import Decimal

@login_required
def dashboard(request):
    # Ensure only users can access
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return redirect('general:index')
    
    # Get pending invitations for verified users (not confirmed yet, status is inactive)
    pending_invitations = []
    if request.user.is_email_verified and hasattr(request.user, 'user_profile'):
        user_profile = request.user.user_profile
        expiration_time = timezone.now() - timedelta(days=7)
        
        pending_invitations = MentorClientRelationship.objects.filter(
            client=user_profile,
            confirmed=False,
            status='inactive',
            invited_at__gte=expiration_time
        ).select_related('mentor', 'mentor__user').order_by('-invited_at')
    
    return render(request, 'dashboard_user/dashboard_user.html', {
        'pending_invitations': pending_invitations,
    })

@login_required
def profile(request):
    """User profile page - for editing profile information (first name, last name, profile picture)"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
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
            
            if first_name is not None:
                profile.first_name = first_name
            if last_name is not None:
                profile.last_name = last_name
            
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
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
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
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
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
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return redirect('general:index')
    
    return render(
        request,
        'dashboard_user/support.html',
        {
            'debug': settings.DEBUG,
        },
    )

@login_required
def my_sessions(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return redirect('general:index')
    
    from general.models import Session
    from django.utils import timezone
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
    
    now = timezone.now()
    
    # Get all upcoming sessions where user is an attendee (invited and confirmed)
    initial_sessions = []
    try:
        all_upcoming = Session.objects.filter(
            attendees=request.user,
            status__in=['invited', 'confirmed'],
            start_datetime__gte=now
        ).order_by('start_datetime').select_related('created_by', 'created_by__mentor_profile').prefetch_related('attendees')
        
        # Get first 10 sessions for initial load
        sessions_queryset = all_upcoming[:10]
        
        # Format sessions for template
        for session in sessions_queryset:
            # Get mentor name (created_by is the mentor)
            mentor_name = None
            if session.created_by and hasattr(session.created_by, 'mentor_profile'):
                mentor_profile = session.created_by.mentor_profile
                mentor_name = f"{mentor_profile.first_name} {mentor_profile.last_name}".strip()
                if not mentor_name:
                    mentor_name = session.created_by.email.split('@')[0]
            else:
                mentor_name = session.created_by.email.split('@')[0] if session.created_by else 'Mentor'
            
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
    
    return render(request, 'dashboard_user/my_sessions.html', {
        'initial_sessions': initial_sessions,
        'user_timezone': user_timezone,
    })


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
        ).order_by('start_datetime').select_related('created_by', 'created_by__mentor_profile').prefetch_related('attendees')
        
        # Paginate
        paginator = Paginator(all_upcoming, per_page)
        page_obj = paginator.get_page(page)
        
        # Format sessions for JSON response
        sessions_data = []
        for session in page_obj:
            # Get mentor name (created_by is the mentor)
            mentor_name = None
            if session.created_by and hasattr(session.created_by, 'mentor_profile'):
                mentor_profile = session.created_by.mentor_profile
                mentor_name = f"{mentor_profile.first_name} {mentor_profile.last_name}".strip()
                if not mentor_name:
                    mentor_name = session.created_by.email.split('@')[0]
            else:
                mentor_name = session.created_by.email.split('@')[0] if session.created_by else 'Mentor'
            
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
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return redirect('general:index')
    
    from accounts.models import MentorClientRelationship
    
    user_profile = request.user.profile
    relationships = MentorClientRelationship.objects.filter(
        client=user_profile
    ).select_related('mentor', 'mentor__user').order_by('-created_at')
    
    return render(request, 'dashboard_user/mentors.html', {
        'relationships': relationships,
    })


@login_required
def session_invitation(request, token: str):
    """
    Validates session invitation token and redirects to session management page
    which shows all pending invitations and changes.
    """
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
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
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
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
    attendee_sessions = Session.objects.filter(attendees=request.user).select_related('created_by')
    attendee_session_ids = set(attendee_sessions.values_list('id', flat=True))
    
    # Combine all session IDs (needed for both GET and POST)
    all_user_session_ids = invitation_session_ids | attendee_session_ids
    
    # Get all sessions with pending changes
    # Check both previous_data/changes_requested_by AND original_data/changed_by
    # IMPORTANT: Exclude sessions that are 'invited' and have an active invitation
    # (those should only appear in the invitations list, not as changes)
    changed_sessions = []
    if all_user_session_ids:
        all_user_sessions = Session.objects.filter(id__in=all_user_session_ids).select_related('created_by').prefetch_related('mentors', 'mentors__user')
        
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
def book_session(request):
    """
    Book a session from the booking modal.
    Handles both logged-in users and non-logged-in users (new and existing).
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
                # Calculate regular price
                price_per_hour = mentor_profile.price_per_hour or Decimal('0')
                hours = Decimal(str(duration_minutes)) / Decimal('60')
                price = price_per_hour * hours
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
                    price_per_hour = mentor_profile.price_per_hour or Decimal('0')
                    hours = Decimal(str(duration_minutes)) / Decimal('60')
                    price = price_per_hour * hours
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
        
        # NOW handle availability slot - only after we've confirmed the booking can proceed
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
            created_by=mentor_profile.user,
            note=session_note,
            first_lesson_user_note=first_lesson_note,
            session_type='individual',
            status='confirmed',
            session_price=price,
            tasks=[],
        )
        mentor_profile.sessions.add(session)
        
        if user:
            session.attendees.add(user)
        
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
        
        return JsonResponse({
            'success': True,
            'message': 'Session booked successfully',
            'session_id': session.id,
            'email': user_email,
            'is_new_user': is_new_user_account
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error booking session: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'}, status=500)
