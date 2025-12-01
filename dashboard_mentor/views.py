from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

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
def my_sessions(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return redirect('general:index')
    return render(request, 'dashboard_mentor/my_sessions.html')
