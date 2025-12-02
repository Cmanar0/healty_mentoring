from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from dashboard_mentor.models import Tag, Credential, MentorType

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
    missing_fields = []

    def consider(value, field_name, display_name):
        nonlocal filled, total
        total += 1
        if value:
            filled += 1
        else:
            missing_fields.append(display_name)

    consider(profile.first_name, 'first_name', 'First Name')
    consider(profile.last_name, 'last_name', 'Last Name')
    consider(profile.time_zone, 'time_zone', 'Time Zone')
    consider(profile.bio, 'bio', 'Bio')
    consider(profile.quote, 'quote', 'Quote')
    consider(profile.mentor_type, 'mentor_type', 'Mentor Type')
    consider(profile.profile_picture, 'profile_picture', 'Profile Picture')
    consider(profile.credentials.exists(), 'credentials', 'Credentials')
    consider(profile.tags.exists(), 'tags', 'Tags')
    # Note: Billing and Subscription are NOT included in profile completion

    profile_completion = int(round((filled / total) * 100)) if total else 0
    
    # Calculate profile content percentage
    blogPosts = 2
    blogPostsTotal = 5
    marketingContent = 2  # quiz + manual checked
    marketingContentTotal = 7
    reviews = 0  # Mockup data - will be replaced with actual reviews count
    reviewsTotal = 3
    
    blogPercentage = (blogPosts / blogPostsTotal) * 100
    marketingPercentage = (marketingContent / marketingContentTotal) * 100
    reviewsPercentage = (reviews / reviewsTotal) * 100 if reviewsTotal > 0 else 0
    contentPercentage = round((blogPercentage + marketingPercentage + reviewsPercentage) / 3)
    
    content_missing = []
    if (blogPosts / blogPostsTotal) < 1:
        content_missing.append(f'Blog Posts ({blogPosts}/{blogPostsTotal})')
    if (marketingContent / marketingContentTotal) < 1:
        content_missing.append(f'Marketing Content ({marketingContent}/{marketingContentTotal})')
    if (reviews / reviewsTotal) < 1:
        content_missing.append(f'Client Reviews ({reviews}/{reviewsTotal})')
    
    # Check billing status for account page
    billing_filled = bool(profile.billing and profile.billing.get('residential_address') and profile.billing.get('payment_method'))

    return render(
        request,
        'dashboard_mentor/account.html',
        {
            "profile_completion": profile_completion,
            "missing_fields": missing_fields,
            "content_percentage": contentPercentage,
            "content_missing": content_missing,
            "billing_filled": billing_filled,
        },
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
                # Delete old profile picture if it exists
                if profile.profile_picture:
                    old_picture = profile.profile_picture
                    # Delete the file from storage
                    old_picture.delete(save=False)
                
                # Save new profile picture
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
            
            # Handle mentor type - create if it doesn't exist
            if mentor_type:
                mentor_type = mentor_type.strip()
                mentor_type_obj, created = MentorType.objects.get_or_create(
                    name=mentor_type,
                    defaults={'is_custom': True}
                )
                profile.mentor_type = mentor_type
            else:
                profile.mentor_type = None
            
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
            
            # Handle credentials (from JSON array)
            import json
            credentials_data = request.POST.get("credentials_data", "")
            if credentials_data:
                try:
                    credentials_list = json.loads(credentials_data)
                    profile.credentials.clear()
                    for cred_data in credentials_list:
                        title = cred_data.get('title', '').strip()
                        subtitle = cred_data.get('subtitle', '').strip()
                        if title:
                            cred, created = Credential.objects.get_or_create(
                                title=title,
                                defaults={'description': subtitle}
                            )
                            if not created and subtitle:
                                cred.description = subtitle
                                cred.save()
                            profile.credentials.add(cred)
                except json.JSONDecodeError:
                    pass
            else:
                profile.credentials.clear()
            
            return redirect("/dashboard/mentor/profile/")
    
    # Compute profile completion percentage (same as account view)
    filled = 0
    total = 0
    missing_fields = []

    def consider(value, field_name, display_name):
        nonlocal filled, total
        total += 1
        if value:
            filled += 1
        else:
            missing_fields.append(display_name)

    consider(profile.first_name, 'first_name', 'First Name')
    consider(profile.last_name, 'last_name', 'Last Name')
    consider(profile.time_zone, 'time_zone', 'Time Zone')
    consider(profile.bio, 'bio', 'Bio')
    consider(profile.quote, 'quote', 'Quote')
    consider(profile.mentor_type, 'mentor_type', 'Mentor Type')
    consider(profile.profile_picture, 'profile_picture', 'Profile Picture')
    consider(profile.credentials.exists(), 'credentials', 'Credentials')
    consider(profile.tags.exists(), 'tags', 'Tags')
    # Note: Billing and Subscription are NOT included in profile completion

    profile_completion = int(round((filled / total) * 100)) if total else 0
    
    # Calculate profile content percentage
    blogPosts = 2
    blogPostsTotal = 5
    marketingContent = 2  # quiz + manual checked
    marketingContentTotal = 7
    reviews = 0  # Mockup data - will be replaced with actual reviews count
    reviewsTotal = 3
    
    blogPercentage = (blogPosts / blogPostsTotal) * 100
    marketingPercentage = (marketingContent / marketingContentTotal) * 100
    reviewsPercentage = (reviews / reviewsTotal) * 100 if reviewsTotal > 0 else 0
    contentPercentage = round((blogPercentage + marketingPercentage + reviewsPercentage) / 3)
    
    content_missing = []
    if (blogPosts / blogPostsTotal) < 1:
        content_missing.append(f'Blog Posts ({blogPosts}/{blogPostsTotal})')
    if (marketingContent / marketingContentTotal) < 1:
        content_missing.append(f'Marketing Content ({marketingContent}/{marketingContentTotal})')
    if (reviews / reviewsTotal) < 1:
        content_missing.append(f'Client Reviews ({reviews}/{reviewsTotal})')
    
    # Fetch all mentor types for autocomplete
    mentor_types = MentorType.objects.all().values_list('name', flat=True)
    
    return render(request, 'dashboard_mentor/profile.html', {
        'user': user,
        'profile': profile,
        'profile_completion': profile_completion,
        'missing_fields': missing_fields,
        'content_percentage': contentPercentage,
        'content_missing': content_missing,
        'mentor_types': list(mentor_types),
    })

@login_required
def billing(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return redirect('general:index')
    
    profile = request.user.profile
    
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "update_billing":
            # Update billing information
            billing_data = {
                'residential_address': request.POST.get('residential_address', ''),
                'tax_id': request.POST.get('tax_id', ''),
                'bank_account': request.POST.get('bank_account', ''),
                'payment_method': request.POST.get('payment_method', ''),
                'bank_name': request.POST.get('bank_name', ''),
                'swift_code': request.POST.get('swift_code', ''),
            }
            profile.billing = billing_data
            profile.save()
            return redirect("/dashboard/mentor/billing/")
    
    return render(request, 'dashboard_mentor/billing.html', {
        'billing': profile.billing or {}
    })

@login_required
def my_sessions(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return redirect('general:index')
    return render(request, 'dashboard_mentor/my_sessions.html')
