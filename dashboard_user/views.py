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
    Auth-required page for a client to confirm a session invitation.
    For now, "Confirm and pay" only sets Session.status='confirmed' and redirects to user dashboard.
    """
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return redirect('general:index')

    from general.models import SessionInvitation
    inv = SessionInvitation.objects.select_related('session', 'mentor', 'mentor__user').filter(token=token).first()
    if not inv:
        messages.error(request, 'Invalid or expired session invitation link.')
        return redirect('/dashboard/user/')

    # Expired/cancelled
    if inv.cancelled_at:
        messages.error(request, 'This session invitation is no longer valid.')
        return redirect('/dashboard/user/')
    if inv.is_expired():
        messages.error(request, 'This session invitation has expired. Please ask your mentor to resend it.')
        return redirect('/dashboard/user/')

    # Ensure correct user is logged in
    user_email = (request.user.email or '').strip().lower()
    invited_email = (inv.invited_email or '').strip().lower()
    if (inv.invited_user and inv.invited_user_id != request.user.id) or (invited_email and invited_email != user_email):
        logout(request)
        messages.warning(request, f'This invitation is for {inv.invited_email}. Please log in with that account.')
        return redirect(f"/accounts/login/?next=/dashboard/user/session-invitation/{token}/")

    s = inv.session
    mentor_name = ''
    try:
        mentor_name = f"{inv.mentor.first_name} {inv.mentor.last_name}".strip()
    except Exception:
        mentor_name = 'your mentor'

    if request.method == 'POST':
        # Confirm session
        try:
            # Ensure attendee includes the user
            try:
                s.attendees.add(request.user)
            except Exception:
                pass
            if getattr(s, 'status', None) != 'confirmed':
                s.status = 'confirmed'
                s.save(update_fields=['status'])
            inv.accepted_at = timezone.now()
            inv.save(update_fields=['accepted_at'])
            messages.success(request, 'Session confirmed. Payment will be added next.')
        except Exception:
            messages.error(request, 'Could not confirm this session. Please try again.')
        return redirect('/dashboard/user/')

    return render(request, 'dashboard_user/session_management.html', {
        'invitation': inv,
        'session': s,
        'mentor_name': mentor_name,
    })


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
    
    # Get all sessions with pending changes (original_data is not null and changed_by is 'mentor')
    # Note: original_data is a JSONField, so we need to check it properly
    changed_sessions = []
    all_user_sessions = Session.objects.filter(attendees=request.user).select_related('created_by')
    for session in all_user_sessions:
        if session.original_data and session.changed_by == 'mentor':
            # Parse ISO datetime strings from original_data to timezone-aware datetime objects for template
            if isinstance(session.original_data, dict):
                from datetime import datetime
                from django.utils import timezone as dj_timezone
                try:
                    if 'start_datetime' in session.original_data and isinstance(session.original_data['start_datetime'], str):
                        dt = datetime.fromisoformat(session.original_data['start_datetime'].replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            dt = dj_timezone.make_aware(dt)
                        session.original_data['start_datetime'] = dt
                    if 'end_datetime' in session.original_data and isinstance(session.original_data['end_datetime'], str):
                        dt = datetime.fromisoformat(session.original_data['end_datetime'].replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            dt = dj_timezone.make_aware(dt)
                        session.original_data['end_datetime'] = dt
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
                session = changed_sessions.filter(id=session_id).first()
                if session:
                    # Clear original_data and changed_by, set status to confirmed
                    session.original_data = None
                    session.changed_by = None
                    session.status = 'confirmed'
                    session.save()
                    messages.success(request, f'Session #{session_id} changes confirmed.')
            
            elif action == 'decline_change' and session_id:
                session = changed_sessions.filter(id=session_id).first()
                if session:
                    # Clear original_data and changed_by, set status to cancelled
                    session.original_data = None
                    session.changed_by = None
                    session.status = 'cancelled'
                    session.save()
                    messages.success(request, f'Session #{session_id} changes declined.')
            
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
    
    return render(request, 'dashboard_user/session_management.html', {
        'invitations': invitations,
        'changed_sessions': changed_sessions,
    })
