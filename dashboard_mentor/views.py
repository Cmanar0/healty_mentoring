from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from dashboard_mentor.models import Tag, Credential

@login_required
def dashboard(request):
    # Ensure only mentors can access
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return redirect('general:index')
    return render(request, 'dashboard_mentor/dashboard_mentor.html')

@login_required
def account(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return redirect('general:index')

    user = request.user
    profile = user.profile

    if request.method == "POST":
        # Update basic name fields
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        if first_name is not None:
            profile.first_name = first_name
        if last_name is not None:
            profile.last_name = last_name
        profile.save()

        # Update email if provided
        email = request.POST.get("email")
        if email:
            user.email = email
            user.save()

        # Handle password change
        new_password = request.POST.get("new_password")
        new_password_again = request.POST.get("new_password_again")
        if new_password and new_password_again and new_password == new_password_again:
            from django.contrib.auth import update_session_auth_hash

            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)

        return redirect("/dashboard/mentor/account/")

    # Compute simple profile completion percentage based on key fields
    filled = 0
    total = 0

    def consider(value):
        nonlocal filled, total
        total += 1
        if value:
            filled += 1

    consider(profile.first_name)
    consider(profile.last_name)
    consider(profile.time_zone)
    consider(profile.bio)
    consider(profile.quote)
    consider(profile.mentor_type)
    consider(profile.profile_picture)
    consider(profile.credentials.exists())
    consider(profile.tags.exists())
    consider(bool(profile.billing))
    consider(bool(profile.subscription))

    profile_completion = int(round((filled / total) * 100)) if total else 0

    return render(
        request,
        'dashboard_mentor/account.html',
        {"profile_completion": profile_completion},
    )

@login_required
def profile(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return redirect('general:index')
    
    user = request.user
    profile = user.profile
    
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "update_picture":
            if 'profile_picture' in request.FILES:
                profile.profile_picture = request.FILES['profile_picture']
                profile.save()
            return redirect("/dashboard/mentor/profile/")
        
        elif action == "update_profile":
            # Update basic fields
            first_name = request.POST.get("first_name")
            last_name = request.POST.get("last_name")
            time_zone = request.POST.get("time_zone", "")
            mentor_type = request.POST.get("mentor_type", "")
            bio = request.POST.get("bio", "")
            quote = request.POST.get("quote", "")
            
            if first_name is not None:
                profile.first_name = first_name
            if last_name is not None:
                profile.last_name = last_name
            profile.time_zone = time_zone
            profile.mentor_type = mentor_type if mentor_type else None
            profile.bio = bio
            profile.quote = quote
            profile.save()
            
            # Handle tags (ManyToMany)
            tags_input = request.POST.get("tags", "").strip()
            if tags_input:
                tag_names = [t.strip() for t in tags_input.split(",") if t.strip()]
                profile.tags.clear()
                for tag_name in tag_names:
                    tag, created = Tag.objects.get_or_create(name=tag_name)
                    profile.tags.add(tag)
            else:
                profile.tags.clear()
            
            # Handle credentials (ManyToMany)
            credentials_input = request.POST.get("credentials", "").strip()
            if credentials_input:
                cred_titles = [c.strip() for c in credentials_input.split(",") if c.strip()]
                profile.credentials.clear()
                for cred_title in cred_titles:
                    cred, created = Credential.objects.get_or_create(title=cred_title)
                    profile.credentials.add(cred)
            else:
                profile.credentials.clear()
            
            return redirect("/dashboard/mentor/profile/")
    
    return render(request, 'dashboard_mentor/profile.html')

@login_required
def my_sessions(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return redirect('general:index')
    return render(request, 'dashboard_mentor/my_sessions.html')
