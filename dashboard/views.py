from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def index(request):
    return render(request, "dashboard/index.html")

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
    return render(request, "dashboard/account.html")
