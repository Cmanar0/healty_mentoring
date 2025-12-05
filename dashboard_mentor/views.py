from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from dashboard_mentor.models import Qualification
from dashboard_mentor.constants import (
    PREDEFINED_MENTOR_TYPES, PREDEFINED_TAGS, 
    PREDEFINED_LANGUAGES, PREDEFINED_CATEGORIES,
    COMMON_TIMEZONES, QUALIFICATION_TYPES
)
import json

@login_required
def dashboard(request):
    # Ensure only mentors can access
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return redirect('general:index')
    return render(request, 'dashboard_mentor/dashboard_mentor.html', {
        'common_timezones': COMMON_TIMEZONES,
        'debug': settings.DEBUG,
    })

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
            from general.email_service import EmailService

            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
            
            # Send password changed confirmation email
            try:
                EmailService.send_password_changed_email(user)
            except Exception as e:
                # Log error but don't fail the request
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error sending password changed email: {str(e)}")

        return redirect("/dashboard/mentor/account/")

    # Compute simple profile completion percentage based on key fields
    # Each field contributes equally: 100% / 15 fields = ~6.67% per field
    # Total fields tracked: 15
    filled = 0
    total = 0
    missing_fields = []

    def consider(value, field_name, display_name):
        """
        Track a field for profile completion.
        Each call increments total by 1, and if value is truthy, increments filled by 1.
        This ensures each field contributes equally to the completion percentage.
        """
        nonlocal filled, total
        total += 1
        if value:
            filled += 1
        else:
            missing_fields.append(display_name)

    # Field 1-2: Basic Info
    consider(profile.first_name, 'first_name', 'First Name')
    consider(profile.last_name, 'last_name', 'Last Name')
    
    # Field 3: Time Zone (use selected_timezone, fallback to time_zone for backward compatibility)
    timezone_value = profile.selected_timezone or profile.time_zone
    consider(timezone_value, 'time_zone', 'Time Zone')
    
    # Field 4-5: Content
    consider(profile.bio, 'bio', 'Bio')
    consider(profile.quote, 'quote', 'Quote')
    
    # Field 6: Mentor Type
    consider(profile.mentor_type, 'mentor_type', 'Mentor Type')
    
    # Field 7: Profile Picture
    consider(profile.profile_picture, 'profile_picture', 'Profile Picture')
    
    # Field 8: Qualifications (at least one required)
    # Check through the through model since we use a custom through model
    from dashboard_mentor.models import MentorProfileQualification
    has_qualifications = MentorProfileQualification.objects.filter(mentor_profile=profile).exists()
    consider(has_qualifications, 'qualifications', 'Qualifications')
    
    # Field 9-11: Tags, Languages, Categories (at least one of each required)
    consider(len(profile.tags) > 0 if profile.tags else False, 'tags', 'Tags')
    consider(len(profile.languages) > 0 if profile.languages else False, 'languages', 'Languages')
    consider(len(profile.categories) > 0 if profile.categories else False, 'categories', 'Categories')
    
    
    # Field 13-14: Pricing
    consider(profile.price_per_hour, 'price_per_hour', 'Price per Hour')
    # Session Configuration: Track standard session length (not First Session Free)
    has_session_length = profile.session_length and profile.session_length > 0
    consider(has_session_length, 'session_length', 'Session Length')
    
    # Field 15: Social Media (at least one of: Instagram, LinkedIn, or Website)
    has_social = bool(profile.instagram_name or profile.linkedin_name or profile.personal_website)
    consider(has_social, 'social_media', 'Social Media (Instagram, LinkedIn, or Website)')
    
    # Note: Billing and Subscription are NOT included in profile completion
    # Note: First Session Free is NOT tracked (only standard session length is tracked)
    # Total: 15 fields, each contributing 100/15 = ~6.67% to completion

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
            'debug': settings.DEBUG,
            "profile_completion": profile_completion,
            "missing_fields": missing_fields,
            "content_percentage": contentPercentage,
            "content_missing": content_missing,
            "billing_filled": billing_filled,
            "common_timezones": COMMON_TIMEZONES,
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
                    # Delete the file from storage using storage API
                    if old_picture.name:
                        old_picture.storage.delete(old_picture.name)
                    # Clear the field reference
                    profile.profile_picture = None
                    profile.save(update_fields=['profile_picture'])
                
                # Save new profile picture
                profile.profile_picture = request.FILES['profile_picture']
                profile.save()
            return redirect("/dashboard/mentor/profile/")
        
        elif action == "update_cover_image":
            if 'cover_image' in request.FILES:
                # Delete old cover image if it exists
                if profile.cover_image:
                    old_cover = profile.cover_image
                    # Delete the file from storage using storage API
                    if old_cover.name:
                        old_cover.storage.delete(old_cover.name)
                    # Clear the field reference
                    profile.cover_image = None
                    profile.save(update_fields=['cover_image'])
                
                # Save new cover image
                profile.cover_image = request.FILES['cover_image']
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
            price_per_hour = request.POST.get("price_per_hour", "")
            instagram_name = request.POST.get("instagram_name", "")
            linkedin_name = request.POST.get("linkedin_name", "")
            personal_website = request.POST.get("personal_website", "")
            nationality = request.POST.get("nationality", "")
            
            if first_name is not None:
                profile.first_name = first_name
            if last_name is not None:
                profile.last_name = last_name
            profile.time_zone = time_zone
            # Also update selected_timezone and clear confirmed mismatch when user updates via profile form
            if time_zone:
                profile.selected_timezone = time_zone
                profile.confirmed_timezone_mismatch = False
            
            # Handle mentor type - just store as string
            if mentor_type:
                profile.mentor_type = mentor_type.strip()
            else:
                profile.mentor_type = None
            
            profile.bio = bio
            profile.quote = quote
            
            # Handle tags (from JSON array) - save all tags (predefined and custom)
            tags_data = request.POST.get("tags_data", "")
            if tags_data:
                try:
                    tags_list = json.loads(tags_data)
                    # Save all tags as-is (no filtering)
                    profile.tags = [tag.strip() for tag in tags_list if tag.strip()]
                except json.JSONDecodeError:
                    profile.tags = []
            else:
                profile.tags = []
            
            # Handle languages (from JSON array) - only allow predefined language IDs
            languages_data = request.POST.get("languages_data", "")
            if languages_data:
                try:
                    languages_list = json.loads(languages_data)
                    valid_language_ids = [lang_id for lang_id in languages_list if lang_id in [lang['id'] for lang in PREDEFINED_LANGUAGES]]
                    profile.languages = valid_language_ids
                except json.JSONDecodeError:
                    profile.languages = []
            else:
                profile.languages = []
            
            # Handle categories (from JSON array) - only allow predefined category IDs
            categories_data = request.POST.get("categories_data", "")
            if categories_data:
                try:
                    categories_list = json.loads(categories_data)
                    valid_category_ids = [cat_id for cat_id in categories_list if cat_id in [cat['id'] for cat in PREDEFINED_CATEGORIES]]
                    profile.categories = valid_category_ids
                except json.JSONDecodeError:
                    profile.categories = []
            else:
                profile.categories = []
            
            # Handle price per hour
            if price_per_hour:
                try:
                    profile.price_per_hour = float(price_per_hour)
                except ValueError:
                    profile.price_per_hour = None
            else:
                profile.price_per_hour = None
            
            # Handle session length
            session_length = request.POST.get("session_length", "")
            if session_length:
                try:
                    profile.session_length = int(session_length)
                except ValueError:
                    profile.session_length = None
            else:
                profile.session_length = None
            
            # Handle first session free (boolean checkbox)
            profile.first_session_free = request.POST.get("first_session_free") == "on"
            
            # Handle first session length (only if first_session_free is True)
            first_session_length = request.POST.get("first_session_length", "")
            if profile.first_session_free and first_session_length:
                try:
                    profile.first_session_length = int(first_session_length)
                except ValueError:
                    profile.first_session_length = None
            else:
                profile.first_session_length = None
            
            # Handle social media and links
            profile.instagram_name = instagram_name.strip() if instagram_name else None
            profile.linkedin_name = linkedin_name.strip() if linkedin_name else None
            profile.personal_website = personal_website.strip() if personal_website else None
            
            profile.save()
            
            # Handle qualifications (from JSON array)
            qualifications_data = request.POST.get("qualifications_data", "")
            if qualifications_data:
                try:
                    qualifications_list = json.loads(qualifications_data)
                    # Import the through model
                    from dashboard_mentor.models import MentorProfileQualification
                    # Clear existing qualifications
                    MentorProfileQualification.objects.filter(mentor_profile=profile).delete()
                    # Add qualifications in order using through model
                    for order, qual_data in enumerate(qualifications_list):
                        title = qual_data.get('title', '').strip()
                        subtitle = qual_data.get('subtitle', '').strip()
                        description = qual_data.get('description', '').strip()
                        qual_type = qual_data.get('type', 'certificate').strip()
                        if title:
                            qual, created = Qualification.objects.get_or_create(
                                title=title,
                                defaults={'subtitle': subtitle, 'description': description, 'type': qual_type}
                            )
                            if not created:
                                if subtitle:
                                    qual.subtitle = subtitle
                                if description:
                                    qual.description = description
                                if qual_type:
                                    qual.type = qual_type
                                qual.save()
                            # Create through model instance with order
                            MentorProfileQualification.objects.create(
                                mentor_profile=profile,
                                qualification=qual,
                                order=order
                            )
                except json.JSONDecodeError:
                    pass
            else:
                from dashboard_mentor.models import MentorProfileQualification
                MentorProfileQualification.objects.filter(mentor_profile=profile).delete()
            
            from django.contrib import messages
            messages.success(request, 'Profile updated successfully!')
            return redirect("/dashboard/mentor/profile/")
    
    # Compute profile completion percentage (same as account view)
    # Each field contributes equally: 100% / 15 fields = ~6.67% per field
    # Total fields tracked: 15
    filled = 0
    total = 0
    missing_fields = []

    def consider(value, field_name, display_name):
        """
        Track a field for profile completion.
        Each call increments total by 1, and if value is truthy, increments filled by 1.
        This ensures each field contributes equally to the completion percentage.
        """
        nonlocal filled, total
        total += 1
        if value:
            filled += 1
        else:
            missing_fields.append(display_name)

    # Field 1-2: Basic Info
    consider(profile.first_name, 'first_name', 'First Name')
    consider(profile.last_name, 'last_name', 'Last Name')
    
    # Field 3: Time Zone (use selected_timezone, fallback to time_zone for backward compatibility)
    timezone_value = profile.selected_timezone or profile.time_zone
    consider(timezone_value, 'time_zone', 'Time Zone')
    
    # Field 4-5: Content
    consider(profile.bio, 'bio', 'Bio')
    consider(profile.quote, 'quote', 'Quote')
    
    # Field 6: Mentor Type
    consider(profile.mentor_type, 'mentor_type', 'Mentor Type')
    
    # Field 7: Profile Picture
    consider(profile.profile_picture, 'profile_picture', 'Profile Picture')
    
    # Field 8: Qualifications (at least one required)
    # Check through the through model since we use a custom through model
    from dashboard_mentor.models import MentorProfileQualification
    has_qualifications = MentorProfileQualification.objects.filter(mentor_profile=profile).exists()
    consider(has_qualifications, 'qualifications', 'Qualifications')
    
    # Field 9-11: Tags, Languages, Categories (at least one of each required)
    consider(len(profile.tags) > 0 if profile.tags else False, 'tags', 'Tags')
    consider(len(profile.languages) > 0 if profile.languages else False, 'languages', 'Languages')
    consider(len(profile.categories) > 0 if profile.categories else False, 'categories', 'Categories')
    
    
    # Field 13-14: Pricing
    consider(profile.price_per_hour, 'price_per_hour', 'Price per Hour')
    # Session Configuration: Track standard session length (not First Session Free)
    has_session_length = profile.session_length and profile.session_length > 0
    consider(has_session_length, 'session_length', 'Session Length')
    
    # Field 15: Social Media (at least one of: Instagram, LinkedIn, or Website)
    has_social = bool(profile.instagram_name or profile.linkedin_name or profile.personal_website)
    consider(has_social, 'social_media', 'Social Media (Instagram, LinkedIn, or Website)')
    
    # Note: Billing and Subscription are NOT included in profile completion
    # Note: First Session Free is NOT tracked (only standard session length is tracked)
    # Total: 15 fields, each contributing 100/15 = ~6.67% to completion

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
    
    return render(request, 'dashboard_mentor/profile.html', {
        'user': user,
        'profile': profile,
        'profile_completion': profile_completion,
        'missing_fields': missing_fields,
        'content_percentage': contentPercentage,
        'content_missing': content_missing,
        'mentor_types': PREDEFINED_MENTOR_TYPES,
        'predefined_tags': PREDEFINED_TAGS,
        'predefined_languages': PREDEFINED_LANGUAGES,
        'predefined_categories': PREDEFINED_CATEGORIES,
        'qualification_types': QUALIFICATION_TYPES,
        'common_timezones': COMMON_TIMEZONES,
        'debug': settings.DEBUG,
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
        'billing': profile.billing or {},
        'common_timezones': COMMON_TIMEZONES,
        'debug': settings.DEBUG,
    })

@login_required
def my_sessions(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return redirect('general:index')
    return render(request, 'dashboard_mentor/my_sessions.html', {
        'common_timezones': COMMON_TIMEZONES,
        'debug': settings.DEBUG,
    })
