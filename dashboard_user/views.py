from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
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
