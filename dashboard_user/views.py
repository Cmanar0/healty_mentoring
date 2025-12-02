from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    # Ensure only users can access
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return redirect('general:index')
    return render(request, 'dashboard_user/dashboard_user.html')

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
                # Delete the file from storage
                old_picture.delete(save=False)
            
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
