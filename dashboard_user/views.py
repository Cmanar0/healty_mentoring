from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from accounts.models import MentorClientRelationship
from django.utils import timezone
from datetime import timedelta

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
def account(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return redirect('general:index')

    if request.method == "POST":
        profile = request.user.profile
        profile.first_name = request.POST.get("first_name", profile.first_name)
        profile.last_name = request.POST.get("last_name", profile.last_name)
        profile.time_zone = request.POST.get("time_zone", profile.time_zone)
        if request.FILES.get("profile_picture"):
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
            profile.profile_picture = request.FILES.get("profile_picture")
        profile.save()
        return redirect("/dashboard/user/account/")

    return render(request, 'dashboard_user/account.html')

@login_required
def my_sessions(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return redirect('general:index')
    return render(request, 'dashboard_user/my_sessions.html')


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
    from django.contrib.auth import logout
    
    user_email = (request.user.email or '').strip().lower()
    
    # Get all pending invitations for this user
    invitations = SessionInvitation.objects.filter(
        invited_email=user_email,
        cancelled_at__isnull=True,
        accepted_at__isnull=True
    ).select_related('session', 'mentor', 'mentor__user').order_by('-created_at')
    
    # Calculate duration in minutes for each invitation
    for inv in invitations:
        if inv.session.start_datetime and inv.session.end_datetime:
            duration = inv.session.end_datetime - inv.session.start_datetime
            inv.session.duration_minutes = int(duration.total_seconds() / 60)
        else:
            inv.session.duration_minutes = 0
    
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
    changed_sessions = []
    if all_user_session_ids:
        all_user_sessions = Session.objects.filter(id__in=all_user_session_ids).select_related('created_by').prefetch_related('mentors')
        
        for session in all_user_sessions:
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
                    # Check if date/time changed
                    if 'start_datetime' in change_data and change_data['start_datetime']:
                        old_start = change_data['start_datetime']
                        if isinstance(old_start, str):
                            try:
                                old_start = datetime.fromisoformat(old_start.replace('Z', '+00:00'))
                                if old_start.tzinfo is None:
                                    old_start = dj_timezone.make_aware(old_start)
                            except:
                                pass
                        if old_start != session.start_datetime:
                            date_changed = True
                    if 'end_datetime' in change_data and change_data['end_datetime']:
                        old_end = change_data['end_datetime']
                        if isinstance(old_end, str):
                            try:
                                old_end = datetime.fromisoformat(old_end.replace('Z', '+00:00'))
                                if old_end.tzinfo is None:
                                    old_end = dj_timezone.make_aware(old_end)
                            except:
                                pass
                        if old_end != session.end_datetime:
                            date_changed = True
                    
                    # Check if price changed
                    old_price = change_data.get('session_price')
                    new_price = session.session_price
                    if old_price != new_price:
                        price_changed = True
                
                # Add flags to session object for template (no underscore for Django template access)
                session.date_changed = date_changed
                session.price_changed = price_changed
                
                # Calculate duration in minutes
                if session.start_datetime and session.end_datetime:
                    duration = session.end_datetime - session.start_datetime
                    session.duration_minutes = int(duration.total_seconds() / 60)
                else:
                    session.duration_minutes = 0
                
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
