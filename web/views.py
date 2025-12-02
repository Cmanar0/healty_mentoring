from django.shortcuts import render, get_object_or_404
from accounts.models import CustomUser

def landing(request):
    return render(request, "web/landing.html")

def mentors(request):
    return render(request, "web/mentors.html")

def terms(request):
    return render(request, "web/terms.html")

def mentor_profile_detail(request, user_id):
    mentor_user = get_object_or_404(CustomUser, id=user_id)
    try:
        mentor_profile = mentor_user.mentor_profile
    except:
        return render(request, "web/mentor_profile_detail.html", {"error": "Mentor profile not found"})
    
    return render(request, "web/mentor_profile_detail.html", {
        "mentor_user": mentor_user,
        "mentor_profile": mentor_profile,
    })
