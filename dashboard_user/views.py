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

    return render(request, 'dashboard_user/session_invitation.html', {
        'invitation': inv,
        'session': s,
        'mentor_name': mentor_name,
    })
