from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def index(request):
    user = request.user
    # Ensure user has a profile
    if not hasattr(user, 'profile'):
        return redirect('web:landing')
        
    role = user.profile.role
    
    if role == 'mentor':
        return redirect('dashboard:mentor_dashboard')
    elif role == 'user':
        return redirect('dashboard:user_dashboard')
    elif role == 'admin':
        # Admin role users are redirected to admin panel or landing
        # Since they shouldn't use the regular dashboard
        if user.is_staff:
            return redirect('/admin/')
        return redirect('web:landing')
    
    return redirect('web:landing')

@login_required
def mentor_dashboard(request):
    # Access control: only mentors
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return redirect('dashboard:index')
    return render(request, "dashboard/mentor/dashboard_mentor.html")

@login_required
def user_dashboard(request):
    # Access control: only users
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return redirect('dashboard:index')
    return render(request, "dashboard/user/dashboard_user.html")

@login_required
def account(request):
    if request.method == "POST":
        profile = request.user.profile
        profile.first_name = request.POST.get("first_name", profile.first_name)
        profile.last_name = request.POST.get("last_name", profile.last_name)
        profile.time_zone = request.POST.get("time_zone", profile.time_zone)
        if request.FILES.get("profile_picture"):
            profile.profile_picture = request.FILES.get("profile_picture")
        # credentials: expect JSON or CSV string for simplicity
        creds = request.POST.get("credentials", "[]")
        try:
            import json
            profile.credentials = json.loads(creds)
        except Exception:
            # try comma separated titles
            profile.credentials = [{"title": s.strip()} for s in creds.split(",") if s.strip()]
        profile.save()
        return redirect("dashboard:account")
    
    # Determine which template to use based on user role
    if hasattr(request.user, 'profile') and request.user.profile.role == 'user':
        return render(request, "dashboard/user/account.html")
    else:
        return render(request, "dashboard/mentor/account.html")
