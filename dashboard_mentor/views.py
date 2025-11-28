from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    # Ensure only mentors can access
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return redirect('dashboard:index')
    return render(request, 'dashboard_mentor/dashboard_mentor.html')

@login_required
def account(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return redirect('dashboard:index')

    if request.method == "POST":
        profile = request.user.profile
        profile.first_name = request.POST.get("first_name", profile.first_name)
        profile.last_name = request.POST.get("last_name", profile.last_name)
        profile.time_zone = request.POST.get("time_zone", profile.time_zone)
        if request.FILES.get("profile_picture"):
            profile.profile_picture = request.FILES.get("profile_picture")
        # Handle credentials
        creds = request.POST.get("credentials", "[]")
        try:
            import json
            profile.credentials = json.loads(creds)
        except Exception:
            # try comma separated titles
            profile.credentials = [{"title": s.strip()} for s in creds.split(",") if s.strip()]
        profile.save()
        return redirect("/dashboard/mentor/account/")
    
    return render(request, 'dashboard_mentor/account.html')

@login_required
def my_sessions(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return redirect('dashboard:index')
    return render(request, 'dashboard_mentor/my_sessions.html')
