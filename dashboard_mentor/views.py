from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.crypto import get_random_string
from django.utils import timezone
from accounts.models import CustomUser, UserProfile, MentorClientRelationship
from dashboard_mentor.constants import (
    PREDEFINED_MENTOR_TYPES, PREDEFINED_TAGS, 
    PREDEFINED_LANGUAGES, PREDEFINED_CATEGORIES,
    COMMON_TIMEZONES, QUALIFICATION_TYPES
)
from general.email_service import EmailService
import json
import os

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
    has_qualifications = len(profile.qualifications) > 0 if profile.qualifications else False
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
            
            # Handle qualifications (from JSON array)
            qualifications_data = request.POST.get("qualifications_data", "")
            if qualifications_data:
                try:
                    qualifications_list = json.loads(qualifications_data)
                    # Clean and validate qualifications data
                    cleaned_qualifications = []
                    for qual_data in qualifications_list:
                        title = qual_data.get('title', '').strip()
                        if title:  # Only add if title exists
                            cleaned_qualifications.append({
                                'title': title,
                                'subtitle': qual_data.get('subtitle', '').strip(),
                                'description': qual_data.get('description', '').strip(),
                                'type': qual_data.get('type', 'certificate').strip()
                            })
                    profile.qualifications = cleaned_qualifications
                except json.JSONDecodeError:
                    profile.qualifications = []
            else:
                profile.qualifications = []
            
            profile.save()
            
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
    has_qualifications = len(profile.qualifications) > 0 if profile.qualifications else False
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
    
    # Get existing availability for the mentor from JSON fields
    mentor_profile = request.user.mentor_profile if hasattr(request.user, 'mentor_profile') else None
    if not mentor_profile:
        return redirect('general:index')
    
    # Format availability data for frontend from one_time_slots JSON field
    # Use new field name, fallback to old for backward compatibility
    try:
        one_time_slots = mentor_profile.one_time_slots or []
    except AttributeError:
        one_time_slots = mentor_profile.availability_slots or []
    availability_data = {}
    
    # Load one-time slots and convert times to mentor's timezone
    try:
        import pytz
        # Get mentor's timezone object
        try:
            mentor_tz = pytz.timezone(mentor_timezone) if mentor_timezone else pytz.UTC
        except:
            mentor_tz = pytz.UTC
    except ImportError:
        # Fallback if pytz is not available - use UTC
        mentor_tz = None
    
    for slot in one_time_slots:
        try:
            from datetime import datetime
            # Parse UTC datetime
            start_dt_utc = datetime.fromisoformat(slot['start'].replace('Z', '+00:00'))
            end_dt_utc = datetime.fromisoformat(slot['end'].replace('Z', '+00:00'))
            
            # Convert to mentor's timezone if pytz is available
            if mentor_tz:
                # Make timezone-aware (UTC)
                if start_dt_utc.tzinfo is None:
                    start_dt_utc = pytz.UTC.localize(start_dt_utc)
                if end_dt_utc.tzinfo is None:
                    end_dt_utc = pytz.UTC.localize(end_dt_utc)
                
                # Convert to mentor's timezone
                start_dt_local = start_dt_utc.astimezone(mentor_tz)
                end_dt_local = end_dt_utc.astimezone(mentor_tz)
            else:
                # Fallback: use UTC times directly
                start_dt_local = start_dt_utc
                end_dt_local = end_dt_utc
            
            # Use local date for grouping (date might change after timezone conversion)
            date_str = start_dt_local.date().isoformat()
            if date_str not in availability_data:
                availability_data[date_str] = []
            
            length_minutes = int((end_dt_utc - start_dt_utc).total_seconds() / 60)
            
            availability_data[date_str].append({
                'start': start_dt_local.time().strftime('%H:%M'),
                'end': end_dt_local.time().strftime('%H:%M'),
                'length': length_minutes,
                'id': slot.get('id'),
                'type': 'one_time',
                'created_at': slot.get('created_at', '')
            })
        except (KeyError, ValueError) as e:
            continue
    
    # Load recurring slots - pass raw JSON without expansion
    # Use new field name, fallback to old for backward compatibility
    try:
        recurring_slots_data = mentor_profile.recurring_slots or []
    except AttributeError:
        recurring_slots_data = mentor_profile.recurring_availability_slots or []
    
    # Get session_length from mentor profile
    session_length = mentor_profile.session_length if mentor_profile and mentor_profile.session_length else 60
    
    # Get mentor's timezone (use selected_timezone, fallback to time_zone)
    mentor_timezone = mentor_profile.selected_timezone or mentor_profile.time_zone or 'UTC'
    
    return render(request, 'dashboard_mentor/my_sessions.html', {
        'common_timezones': COMMON_TIMEZONES,
        'debug': settings.DEBUG,
        'availability_data': availability_data,
        'recurring_slots': recurring_slots_data,
        'session_length': session_length,
        'mentor_timezone': mentor_timezone,
    })

@login_required
@require_POST
def save_availability(request):
    """Save mentor availability from frontend"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return JsonResponse({'success': False, 'error': 'Only mentors can save availability'}, status=403)
    
    try:
        from datetime import datetime
        from django.utils import timezone
        import uuid
        
        mentor_profile = request.user.mentor_profile
        data = json.loads(request.body)
        availability_list = data.get('availability', [])
        selected_date_str = data.get('selected_date')
        
        if not availability_list:
            return JsonResponse({'success': False, 'error': 'No availability data provided'}, status=400)
        
        # Get the date being edited - prefer selected_date from request, fallback to first item's date
        edited_date_str = selected_date_str or availability_list[0].get('date')
        if not edited_date_str:
            return JsonResponse({'success': False, 'error': 'No date specified'}, status=400)
        
        # Get existing slots - use new field names with fallback to old for backward compatibility
        try:
            existing_one_time_slots = list(mentor_profile.one_time_slots or [])
        except AttributeError:
            existing_one_time_slots = list(mentor_profile.availability_slots or [])
        
        try:
            existing_recurring_slots = list(mentor_profile.recurring_slots or [])
        except AttributeError:
            existing_recurring_slots = list(mentor_profile.recurring_availability_slots or [])
        
        # Remove all existing one-time slots for the edited date (we'll replace them)
        edited_date_obj = datetime.strptime(edited_date_str, '%Y-%m-%d').date()
        final_one_time_slots = [
            slot for slot in existing_one_time_slots
            if datetime.fromisoformat(slot['start'].replace('Z', '+00:00')).date() != edited_date_obj
        ]
        
        # Track which recurring slot IDs are being edited/converted (to remove old ones)
        edited_recurring_slot_ids = set()
        
        # Process new slots - each session becomes a separate slot
        new_one_time_slots = []
        new_recurring_slots = []
        
        for avail_item in availability_list:
            date_str = avail_item.get('date')
            start_time = avail_item.get('start')
            end_time = avail_item.get('end')
            is_recurring = avail_item.get('is_recurring', False)
            recurrence_rule = avail_item.get('recurrence_rule', '')
            recurring_slot_id = avail_item.get('recurring_slot_id')  # ID of recurring slot being edited
            
            # Handle recurring → one-time conversion
            if recurring_slot_id and not (is_recurring and recurrence_rule):
                # This is a conversion: recurring slot → one-time slot
                edited_recurring_slot_ids.add(recurring_slot_id)
                
                # Find the recurring slot to convert
                existing_recurring_slot = next(
                    (s for s in existing_recurring_slots if s.get('id') == recurring_slot_id),
                    None
                )
                
                if existing_recurring_slot and all([date_str, start_time, end_time]):
                    # Use the recurring slot's id and created_at
                    slot_id = existing_recurring_slot.get('id')
                    created_at = existing_recurring_slot.get('created_at', timezone.now().isoformat())
                    
                    # Build datetime strings with timezone
                    start_datetime_str = f"{date_str}T{start_time}:00+00:00"
                    end_datetime_str = f"{date_str}T{end_time}:00+00:00"
                    
                    try:
                        # Parse datetime
                        start_dt = datetime.fromisoformat(start_datetime_str.replace('+00:00', ''))
                        end_dt = datetime.fromisoformat(end_datetime_str.replace('+00:00', ''))
                        
                        # Make timezone-aware
                        start_dt = timezone.make_aware(start_dt)
                        end_dt = timezone.make_aware(end_dt)
                        
                        # Validate end > start
                        if end_dt <= start_dt:
                            continue
                        
                        # Calculate length
                        length_minutes = avail_item.get('length')
                        if not length_minutes or length_minutes <= 0:
                            length_minutes = int((end_dt - start_dt).total_seconds() / 60)
                        
                        # Create one-time slot with preserved id and created_at
                        one_time_slot = {
                            'id': slot_id,
                            'start': start_dt.isoformat(),
                            'end': end_dt.isoformat(),
                            'length': length_minutes,
                            'created_at': created_at
                        }
                        new_one_time_slots.append(one_time_slot)
                    except ValueError as e:
                        continue
                continue  # Skip to next item
            
            if is_recurring and recurrence_rule:
                # Handle recurring slots
                slot_type = recurrence_rule
                
                # Determine weekdays and day_of_month based on recurrence type
                weekdays = []
                day_of_month = None
                
                if slot_type == 'daily':
                    # Daily: all 7 weekdays, no day_of_month
                    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                elif slot_type == 'weekly':
                    # Weekly: single weekday of selected date, no day_of_month
                    weekday_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                    weekday_index = edited_date_obj.weekday()  # 0=Monday, 6=Sunday
                    weekdays = [weekday_names[weekday_index]]
                elif slot_type == 'monthly':
                    # Monthly: day_of_month = selected date's day, weekdays ignored
                    day_of_month = edited_date_obj.day  # 1-31
                    weekdays = []  # Ignored for monthly
                else:
                    # Fallback
                    weekdays = avail_item.get('weekdays', [])
                    day_of_month = avail_item.get('day_of_month')
                
                # If editing an existing recurring slot, preserve its ID and remove the old one
                if recurring_slot_id:
                    edited_recurring_slot_ids.add(recurring_slot_id)
                    slot_id = recurring_slot_id
                    # Find and preserve created_at from existing slot
                    existing_slot = next((s for s in existing_recurring_slots if s.get('id') == recurring_slot_id), None)
                    created_at = existing_slot.get('created_at', timezone.now().isoformat()) if existing_slot else timezone.now().isoformat()
                else:
                    slot_id = str(uuid.uuid4())
                    created_at = timezone.now().isoformat()
                
                # Build recurring slot with proper structure
                recurring_slot = {
                    'id': slot_id,
                    'type': slot_type,
                    'start_time': start_time,
                    'end_time': end_time,
                    'created_at': created_at
                }
                
                # Add weekdays for daily/weekly, day_of_month for monthly
                if slot_type == 'monthly':
                    recurring_slot['day_of_month'] = day_of_month
                else:
                    recurring_slot['weekdays'] = weekdays
                
                new_recurring_slots.append(recurring_slot)
            else:
                # Handle regular one-time slots (not converted)
                if not all([date_str, start_time, end_time]):
                    continue
                
                # Build datetime strings with timezone
                start_datetime_str = f"{date_str}T{start_time}:00+00:00"
                end_datetime_str = f"{date_str}T{end_time}:00+00:00"
                
                try:
                    # Parse datetime
                    start_dt = datetime.fromisoformat(start_datetime_str.replace('+00:00', ''))
                    end_dt = datetime.fromisoformat(end_datetime_str.replace('+00:00', ''))
                    
                    # Make timezone-aware
                    start_dt = timezone.make_aware(start_dt)
                    end_dt = timezone.make_aware(end_dt)
                    
                    # Validate end > start
                    if end_dt <= start_dt:
                        continue
                    
                    # Calculate length
                    length_minutes = avail_item.get('length')
                    if not length_minutes or length_minutes <= 0:
                        length_minutes = int((end_dt - start_dt).total_seconds() / 60)
                    
                    # Preserve existing ID if provided (for existing one-time sessions being updated)
                    slot_id = avail_item.get('id')
                    if not slot_id:
                        slot_id = str(uuid.uuid4())
                    
                    # Preserve created_at if provided, otherwise use current time
                    created_at = avail_item.get('created_at')
                    if not created_at:
                        created_at = timezone.now().isoformat()
                    
                    # Create one-time slot
                    one_time_slot = {
                        'id': slot_id,
                        'start': start_dt.isoformat(),
                        'end': end_dt.isoformat(),
                        'length': length_minutes,
                        'created_at': created_at
                    }
                    new_one_time_slots.append(one_time_slot)
                except ValueError as e:
                    continue
        
        # Remove recurring slots that are being edited/converted (we'll replace or remove them)
        final_recurring_slots = [
            slot for slot in existing_recurring_slots
            if slot.get('id') not in edited_recurring_slot_ids
        ]
        
        # Merge: keep existing one-time slots from other dates + add new slots for edited date
        # Merge: keep existing recurring slots (except edited ones) + add new/updated recurring slots
        final_one_time_slots = final_one_time_slots + new_one_time_slots
        final_recurring_slots = final_recurring_slots + new_recurring_slots
        
        # Save to MentorProfile - use new field names (migration has been applied)
        mentor_profile.one_time_slots = final_one_time_slots
        mentor_profile.recurring_slots = final_recurring_slots
        mentor_profile.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully saved {len(new_one_time_slots)} one-time slot(s) and {len(new_recurring_slots)} recurring slot(s) for {edited_date_str}',
            'one_time_count': len(new_one_time_slots),
            'recurring_count': len(new_recurring_slots),
            'date': edited_date_str
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def invite_client(request):
    """Invite a client by email - creates unverified user and sends invitation"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return JsonResponse({'success': False, 'error': 'Only mentors can invite clients'}, status=403)
    
    mentor_profile = request.user.mentor_profile
    email = request.POST.get('email', '').strip().lower()
    
    if not email:
        return JsonResponse({'success': False, 'error': 'Email is required'}, status=400)
    
    # Check if user already exists
    try:
        existing_user = CustomUser.objects.get(email=email)
        # Check if user has a user_profile (not mentor_profile)
        try:
            user_profile = existing_user.user_profile
            # Check if relationship already exists
            existing_relationship = MentorClientRelationship.objects.filter(mentor=mentor_profile, client=user_profile).first()
            if existing_relationship:
                if existing_relationship.status == 'confirmed' and existing_relationship.confirmed:
                    return JsonResponse({'success': False, 'error': 'This user is already in your client list'}, status=400)
                # If relationship exists but not active/confirmed, resend confirmation
                confirmation_token = get_random_string(64)
                existing_relationship.confirmation_token = confirmation_token
                existing_relationship.status = 'inactive'  # Reset to inactive
                existing_relationship.confirmed = False  # Reset confirmation
                existing_relationship.invited_at = timezone.now()
                existing_relationship.save()
            else:
                # Create new relationship for existing user - needs confirmation
                confirmation_token = get_random_string(64)
                existing_relationship = MentorClientRelationship.objects.create(
                    mentor=mentor_profile,
                    client=user_profile,
                    status='inactive',
                    confirmed=False,
                    confirmation_token=confirmation_token
                )
            
            # Send confirmation email to existing user
            site_domain = EmailService.get_site_domain()
            confirmation_url = f"{site_domain}/accounts/confirm-mentor-invitation/{confirmation_token}/"
            
            EmailService.send_email(
                subject=f"{mentor_profile.first_name} {mentor_profile.last_name} wants to add you as a client",
                recipient_email=email,
                template_name='client_confirmation',
                context={
                    'mentor_name': f"{mentor_profile.first_name} {mentor_profile.last_name}",
                    'confirmation_url': confirmation_url,
                }
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Confirmation email sent. The user will appear as pending until they accept.'
            })
        except UserProfile.DoesNotExist:
            # User exists but doesn't have a user_profile - they might be a mentor
            return JsonResponse({'success': False, 'error': 'This email belongs to a mentor account. Please use a different email.'}, status=400)
    except CustomUser.DoesNotExist:
        pass
    
    # Create new unverified user
    try:
        # Generate a random password (user will set their own during registration)
        temp_password = get_random_string(32)
        user = CustomUser.objects.create_user(
            email=email,
            password=temp_password,
            is_email_verified=False,
            is_active=True  # Allow them to complete registration
        )
        
        # Create UserProfile with placeholder names (will be updated during registration)
        user_profile = UserProfile.objects.create(
            user=user,
            first_name='',
            last_name='',
            role='user'
        )
        
        # Generate invitation token
        invitation_token = get_random_string(64)
        
        # Create mentor-client relationship
        relationship = MentorClientRelationship.objects.create(
            mentor=mentor_profile,
            client=user_profile,
            status='inactive',
            confirmed=False,
            invitation_token=invitation_token
        )
        
        # Send invitation email
        site_domain = EmailService.get_site_domain()
        registration_url = f"{site_domain}/accounts/complete-invitation/{invitation_token}/"
        
        EmailService.send_email(
            subject=f"You've been invited by {mentor_profile.first_name} {mentor_profile.last_name}",
            recipient_email=email,
            template_name='client_invitation',
            context={
                'mentor_name': f"{mentor_profile.first_name} {mentor_profile.last_name}",
                'registration_url': registration_url,
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Invitation sent. The user will appear in your clients list once they complete registration.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def clients_list(request):
    """Display list of all clients for the logged-in mentor"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return redirect('general:index')
    
    mentor_profile = request.user.mentor_profile
    relationships = MentorClientRelationship.objects.filter(mentor=mentor_profile).select_related('client', 'client__user').order_by('-created_at')
    
    return render(request, 'dashboard_mentor/clients.html', {
        'relationships': relationships,
        'common_timezones': COMMON_TIMEZONES,
        'debug': settings.DEBUG,
    })


@login_required
@require_POST
def resend_client_invitation(request, relationship_id):
    """Resend invitation or confirmation email to a client"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return JsonResponse({'success': False, 'error': 'Only mentors can resend invitations'}, status=403)
    
    mentor_profile = request.user.mentor_profile
    try:
        relationship = MentorClientRelationship.objects.get(id=relationship_id, mentor=mentor_profile)
    except MentorClientRelationship.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Relationship not found'}, status=404)
    
    site_domain = EmailService.get_site_domain()
    client_user = relationship.client.user
    
    # Check if user is verified to determine which email to send
    if not client_user.is_email_verified:
        # Resend invitation email for new users (not verified yet)
        if not relationship.invitation_token:
            relationship.invitation_token = get_random_string(64)
            relationship.save()
        
        registration_url = f"{site_domain}/accounts/complete-invitation/{relationship.invitation_token}/"
        
        EmailService.send_email(
            subject=f"You've been invited by {mentor_profile.first_name} {mentor_profile.last_name}",
            recipient_email=client_user.email,
            template_name='client_invitation',
            context={
                'mentor_name': f"{mentor_profile.first_name} {mentor_profile.last_name}",
                'registration_url': registration_url,
            }
        )
        
        relationship.invited_at = timezone.now()
        relationship.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Invitation email resent successfully.'
        })
    
    elif not relationship.confirmed and relationship.status == 'inactive':
        # Resend confirmation email for existing verified users
        if not relationship.confirmation_token:
            relationship.confirmation_token = get_random_string(64)
            relationship.save()
        
        confirmation_url = f"{site_domain}/accounts/confirm-mentor-invitation/{relationship.confirmation_token}/"
        
        EmailService.send_email(
            subject=f"{mentor_profile.first_name} {mentor_profile.last_name} wants to add you as a client",
            recipient_email=client_user.email,
            template_name='client_confirmation',
            context={
                'mentor_name': f"{mentor_profile.first_name} {mentor_profile.last_name}",
                'confirmation_url': confirmation_url,
            }
        )
        
        relationship.invited_at = timezone.now()
        relationship.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Confirmation email resent successfully.'
        })
    
    else:
        return JsonResponse({'success': False, 'error': 'Cannot resend email for confirmed or denied relationships'}, status=400)


@login_required
@require_POST
def delete_client_relationship(request, relationship_id):
    """Delete a client relationship and expire tokens"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return JsonResponse({'success': False, 'error': 'Only mentors can delete relationships'}, status=403)
    
    mentor_profile = request.user.mentor_profile
    try:
        relationship = MentorClientRelationship.objects.get(id=relationship_id, mentor=mentor_profile)
    except MentorClientRelationship.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Relationship not found'}, status=404)
    
    # Expire tokens by clearing them
    relationship.invitation_token = None
    relationship.confirmation_token = None
    relationship.save()
    
    # Delete the relationship
    relationship.delete()
    
    return JsonResponse({
        'success': True,
        'message': 'Client removed from your list successfully.'
    })
