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
    QUALIFICATION_TYPES
)
from general.email_service import EmailService
from general.models import BlogPost
from general.forms import BlogPostForm
from django.core.paginator import Paginator
from django.db.models import Q
import json
import os
from datetime import datetime, timedelta, timezone as dt_timezone

@login_required
def dashboard(request):
    # Ensure only mentors can access
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing mentor dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'mentor':
        return redirect('general:index')
    
    # Fetch upcoming sessions (invited and confirmed only, future dates, max 4)
    upcoming_sessions = []
    has_more_sessions = False
    
    try:
        from general.models import Session
        mentor_profile = request.user.mentor_profile if hasattr(request.user, 'mentor_profile') else None
        
        if mentor_profile:
            now = timezone.now()
            # Get all upcoming sessions (invited and confirmed)
            all_upcoming = mentor_profile.sessions.filter(
                status__in=['invited', 'confirmed'],
                start_datetime__gte=now
            ).order_by('start_datetime').select_related('created_by').prefetch_related('attendees')
            
            # Get total count to check if there are more than 4
            total_count = all_upcoming.count()
            has_more_sessions = total_count > 4
            
            # Get first 4 sessions
            sessions_queryset = all_upcoming[:4]
            
            # Format sessions for template
            for session in sessions_queryset:
                # Get first attendee (client) if any
                client = session.attendees.first() if session.attendees.exists() else None
                client_name = None
                if client and hasattr(client, 'profile'):
                    client_name = f"{client.profile.first_name} {client.profile.last_name}".strip()
                    if not client_name:
                        client_name = client.email.split('@')[0]
                
                # Check if this is the first session with this client
                is_first_session = False
                if client:
                    try:
                        user_profile = client.user_profile if hasattr(client, 'user_profile') else None
                        if user_profile:
                            # Get all sessions with this client (excluding cancelled/expired)
                            all_client_sessions = mentor_profile.sessions.filter(
                                attendees=client
                            ).exclude(status__in=['cancelled', 'expired']).exclude(id=session.id)
                            
                            # If there are no other sessions with this client, this is the first
                            if not all_client_sessions.exists():
                                is_first_session = True
                            else:
                                # Check if this session is the earliest one
                                earliest_session = all_client_sessions.order_by('start_datetime').first()
                                if earliest_session and session.start_datetime and earliest_session.start_datetime:
                                    is_first_session = session.start_datetime <= earliest_session.start_datetime
                    except Exception:
                        is_first_session = False
                
                upcoming_sessions.append({
                    'id': session.id,
                    'start_datetime': session.start_datetime,
                    'end_datetime': session.end_datetime,
                    'status': session.status,
                    'client_name': client_name or 'Client',
                    'note': session.note,
                    'is_first_session': is_first_session,
                })
    except Exception as e:
        # Log error but don't fail the request
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching upcoming sessions: {str(e)}")
    
    return render(request, 'dashboard_mentor/dashboard_mentor.html', {
        'debug': settings.DEBUG,
        'upcoming_sessions': upcoming_sessions,
        'has_more_sessions': has_more_sessions,
    })

@login_required
def account(request):
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing mentor dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'mentor':
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
        },
    )

def check_time_overlap(start1, end1, start2, end2):
    """Check if two time ranges overlap"""
    return start1 < end2 and start2 < end1

def expand_recurring_slot_to_dates(recurring_slot, start_date, end_date):
    """
    Expand a recurring slot to actual date/time ranges within a date range.
    Returns a list of (date_str, start_time_str, end_time_str) tuples.
    """
    expanded = []
    
    try:
        slot_type = recurring_slot.get('type', 'weekly')
        weekdays = recurring_slot.get('weekdays', [])
        day_of_month = recurring_slot.get('day_of_month')
        start_time_str = recurring_slot.get('start_time', '09:00')
        end_time_str = recurring_slot.get('end_time', '17:00')
        skip_dates = set(recurring_slot.get('skip_dates', []))
        booked_dates = set(recurring_slot.get('booked_dates', []))
        created_at = recurring_slot.get('created_at')
        slot_start_date_str = recurring_slot.get('start_date')
        
        # Parse start and end times
        start_hour, start_minute = map(int, start_time_str.split(':'))
        end_hour, end_minute = map(int, end_time_str.split(':'))
        
        # Parse date range
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Parse slot start_date if provided (preferred over created_at for forward-only rendering)
        slot_start_date = None
        if slot_start_date_str:
            try:
                slot_start_date = datetime.strptime(slot_start_date_str, '%Y-%m-%d').date()
            except Exception:
                slot_start_date = None
        
        # Get creation date if available
        creation_date = None
        if created_at:
            try:
                creation_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
            except:
                pass
        
        # Generate dates based on recurrence type
        current_date = start_date
        if slot_start_date and current_date < slot_start_date:
            current_date = slot_start_date
        
        while current_date <= end_date:
            date_str = current_date.isoformat()
            
            # Skip if before slot start_date (or before creation_date for legacy data)
            if slot_start_date and current_date < slot_start_date:
                current_date += timedelta(days=1)
                continue
            if creation_date and current_date < creation_date:
                current_date += timedelta(days=1)
                continue
            
            # Skip if in skip_dates or booked_dates
            if date_str in skip_dates or date_str in booked_dates:
                current_date += timedelta(days=1)
                continue
            
            matches = False
            
            if slot_type == 'daily':
                matches = True
            elif slot_type == 'weekly':
                weekday_name = current_date.strftime('%A').lower()
                matches = weekday_name in weekdays
            elif slot_type == 'monthly':
                if day_of_month is not None:
                    # Check if current date's day matches
                    if current_date.day == day_of_month:
                        matches = True
                    # Handle edge case: if slot is for day 31 but month doesn't have 31 days
                    elif day_of_month > 28:
                        last_day = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                        if current_date.day == last_day.day and day_of_month > last_day.day:
                            matches = True
            
            if matches:
                expanded.append((date_str, start_time_str, end_time_str))
            
            current_date += timedelta(days=1)
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f'Error expanding recurring slot: {e}')
    
    return expanded

def check_slot_collisions(one_time_slots, recurring_slots, new_session_length, mentor_timezone_str: str = None, sessions=None):
    """
    Check if updating availability slot lengths to new_session_length would create collisions
    against other availability slots and existing sessions, and also detect session-session collisions.
    Returns True if collisions exist, False otherwise.
    """
    from datetime import datetime as dt
    from datetime import timezone as dt_timezone

    tzinfo = None
    if mentor_timezone_str:
        # Prefer stdlib zoneinfo, fallback to pytz if available.
        try:
            from zoneinfo import ZoneInfo
            tzinfo = ZoneInfo(str(mentor_timezone_str))
        except Exception:
            try:
                import pytz
                tzinfo = pytz.timezone(str(mentor_timezone_str))
            except Exception:
                tzinfo = None
    
    # Get all dates that have slots
    all_dates = set()
    for slot in one_time_slots:
        try:
            start_dt = datetime.fromisoformat(slot['start'].replace('Z', '+00:00'))
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=dt_timezone.utc)
            if tzinfo:
                start_dt = start_dt.astimezone(tzinfo)
            all_dates.add(start_dt.date().isoformat())
        except:
            pass
    
    # Expand recurring slots to get all dates
    if all_dates:
        min_date = min(all_dates)
        max_date = max(all_dates)
        # Expand a bit to catch edge cases
        min_date_obj = datetime.strptime(min_date, '%Y-%m-%d').date() - timedelta(days=30)
        max_date_obj = datetime.strptime(max_date, '%Y-%m-%d').date() + timedelta(days=30)
    else:
        # If no one-time slots, check next 90 days for recurring slots
        min_date_obj = datetime.now().date()
        max_date_obj = min_date_obj + timedelta(days=90)
    
    # Build a map of date -> list of time ranges for that date
    date_slots = {}
    
    # Add one-time availability slots (with updated length)
    for slot in one_time_slots:
        try:
            start_dt = datetime.fromisoformat(slot['start'].replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(slot['end'].replace('Z', '+00:00'))
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=dt_timezone.utc)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=dt_timezone.utc)
            if tzinfo:
                start_dt = start_dt.astimezone(tzinfo)
                end_dt = end_dt.astimezone(tzinfo)
            date_str = start_dt.date().isoformat()
            
            # Calculate new end time with new session length
            new_end_dt = start_dt + timedelta(minutes=new_session_length)
            
            if date_str not in date_slots:
                date_slots[date_str] = []
            
            date_slots[date_str].append({
                'start': start_dt.time(),
                'end': new_end_dt.time(),
                'type': 'one_time',
                'id': slot.get('id')
            })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f'Error processing one-time slot: {e}')
            continue
    
    # Expand and add recurring availability slots (with updated length)
    for recurring_slot in recurring_slots:
        expanded = expand_recurring_slot_to_dates(recurring_slot, min_date_obj, max_date_obj)
        for date_str, start_time_str, end_time_str in expanded:
            try:
                start_hour, start_minute = map(int, start_time_str.split(':'))
                end_hour, end_minute = map(int, end_time_str.split(':'))
                
                # Create datetime objects for this date
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                start_dt = datetime.combine(date_obj, dt.min.time().replace(hour=start_hour, minute=start_minute))
                original_end_dt = datetime.combine(date_obj, dt.min.time().replace(hour=end_hour, minute=end_minute))
                
                # Calculate new end time with new session length
                new_end_dt = start_dt + timedelta(minutes=new_session_length)
                
                if date_str not in date_slots:
                    date_slots[date_str] = []
                
                date_slots[date_str].append({
                    'start': start_dt.time(),
                    'end': new_end_dt.time(),
                    'type': 'recurring',
                    'id': recurring_slot.get('id')
                })
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f'Error processing expanded recurring slot: {e}')
                continue

    # Add sessions as fixed time ranges (do not change length)
    # IMPORTANT: Exclude cancelled sessions from collision detection
    try:
        if sessions:
            for s in sessions:
                try:
                    # Skip cancelled sessions - they shouldn't block availability
                    status = getattr(s, 'status', None) or s.get('status')
                    if status and str(status).lower() == 'cancelled':
                        continue
                    
                    start_dt = getattr(s, 'start_datetime', None) or s.get('start_datetime')
                    end_dt = getattr(s, 'end_datetime', None) or s.get('end_datetime')
                    if not start_dt or not end_dt:
                        continue
                    # Parse ISO strings if needed
                    if isinstance(start_dt, str):
                        start_dt = datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
                    if isinstance(end_dt, str):
                        end_dt = datetime.fromisoformat(end_dt.replace('Z', '+00:00'))
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=dt_timezone.utc)
                    if end_dt.tzinfo is None:
                        end_dt = end_dt.replace(tzinfo=dt_timezone.utc)
                    if tzinfo:
                        start_dt = start_dt.astimezone(tzinfo)
                        end_dt = end_dt.astimezone(tzinfo)
                    if end_dt <= start_dt:
                        continue
                    date_str = start_dt.date().isoformat()
                    # Only consider sessions in the same window as availability checks
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                        if date_obj < min_date_obj or date_obj > max_date_obj:
                            continue
                    except Exception:
                        pass
                    if date_str not in date_slots:
                        date_slots[date_str] = []
                    date_slots[date_str].append({
                        'start': start_dt.time(),
                        'end': end_dt.time(),
                        'type': 'session',
                        'id': getattr(s, 'id', None) or s.get('id')
                    })
                except Exception:
                    continue
    except Exception:
        pass
    
    # Check for collisions within each date
    for date_str, slots in date_slots.items():
        # Sort slots by start time
        slots.sort(key=lambda x: x['start'])
        
        # Check each slot against all others
        for i in range(len(slots)):
            for j in range(i + 1, len(slots)):
                slot1 = slots[i]
                slot2 = slots[j]
                
                # Check if they overlap
                if check_time_overlap(slot1['start'], slot1['end'], slot2['start'], slot2['end']):
                    return True  # Collision found
    
    return False  # No collisions

def update_slots_for_session_length(mentor_profile, old_length, new_length):
    """
    Update all availability slots when session length changes.
    Returns True if collisions exist (when lengthening), False otherwise.
    """
    # Get slots
    try:
        one_time_slots = list(mentor_profile.one_time_slots or [])
    except AttributeError:
        one_time_slots = list(mentor_profile.availability_slots or [])
    
    try:
        recurring_slots = list(mentor_profile.recurring_slots or [])
    except AttributeError:
        recurring_slots = list(mentor_profile.recurring_availability_slots or [])
    
    # If shortening, update directly
    if new_length < old_length:
        # Update one-time slots
        updated_one_time = []
        for slot in one_time_slots:
            try:
                start_dt = datetime.fromisoformat(slot['start'].replace('Z', '+00:00'))
                new_end_dt = start_dt + timedelta(minutes=new_length)
                slot['end'] = new_end_dt.isoformat()
                slot['length'] = new_length
                updated_one_time.append(slot)
            except:
                updated_one_time.append(slot)  # Keep invalid slots as-is
        
        # Update recurring slots end_time
        updated_recurring = []
        for slot in recurring_slots:
            try:
                start_hour, start_minute = map(int, slot.get('start_time', '09:00').split(':'))
                new_end_dt = datetime(2000, 1, 1, start_hour, start_minute) + timedelta(minutes=new_length)
                slot['end_time'] = new_end_dt.strftime('%H:%M')
                updated_recurring.append(slot)
            except:
                updated_recurring.append(slot)  # Keep invalid slots as-is
        
        # Save updated slots
        mentor_profile.one_time_slots = updated_one_time
        mentor_profile.recurring_slots = updated_recurring
        mentor_profile.save()
        return False  # No collisions when shortening
    
    # If lengthening, check for collisions first
    elif new_length > old_length:
        mentor_tz = mentor_profile.selected_timezone or mentor_profile.time_zone or 'UTC'
        has_collisions = check_slot_collisions(
            one_time_slots,
            recurring_slots,
            new_length,
            mentor_timezone_str=mentor_tz,
            sessions=list(mentor_profile.sessions.all())
        )
        
        if not has_collisions:
            # No collisions, update safely
            updated_one_time = []
            for slot in one_time_slots:
                try:
                    start_dt = datetime.fromisoformat(slot['start'].replace('Z', '+00:00'))
                    new_end_dt = start_dt + timedelta(minutes=new_length)
                    slot['end'] = new_end_dt.isoformat()
                    slot['length'] = new_length
                    updated_one_time.append(slot)
                except:
                    updated_one_time.append(slot)
            
            updated_recurring = []
            for slot in recurring_slots:
                try:
                    start_hour, start_minute = map(int, slot.get('start_time', '09:00').split(':'))
                    new_end_dt = datetime(2000, 1, 1, start_hour, start_minute) + timedelta(minutes=new_length)
                    slot['end_time'] = new_end_dt.strftime('%H:%M')
                    updated_recurring.append(slot)
                except:
                    updated_recurring.append(slot)
            
            mentor_profile.one_time_slots = updated_one_time
            mentor_profile.recurring_slots = updated_recurring
            mentor_profile.save()
            return False  # No collisions
        
        else:
            # Collisions exist - update slots anyway so user can see collisions in calendar
            # User will need to resolve them manually
            updated_one_time = []
            for slot in one_time_slots:
                try:
                    start_dt = datetime.fromisoformat(slot['start'].replace('Z', '+00:00'))
                    new_end_dt = start_dt + timedelta(minutes=new_length)
                    slot['end'] = new_end_dt.isoformat()
                    slot['length'] = new_length
                    updated_one_time.append(slot)
                except:
                    updated_one_time.append(slot)
            
            updated_recurring = []
            for slot in recurring_slots:
                try:
                    start_hour, start_minute = map(int, slot.get('start_time', '09:00').split(':'))
                    new_end_dt = datetime(2000, 1, 1, start_hour, start_minute) + timedelta(minutes=new_length)
                    slot['end_time'] = new_end_dt.strftime('%H:%M')
                    updated_recurring.append(slot)
                except:
                    updated_recurring.append(slot)
            
            mentor_profile.one_time_slots = updated_one_time
            mentor_profile.recurring_slots = updated_recurring
            mentor_profile.save()
            return True  # Has collisions
    
    return False  # No change in length

@login_required
def profile(request):
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing mentor dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'mentor':
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
            
            # Store old timezone before updating
            old_selected_timezone = profile.selected_timezone
            
            profile.time_zone = time_zone
            # Also update selected_timezone and clear confirmed mismatch when user updates via profile form
            if time_zone:
                profile.selected_timezone = time_zone
                profile.confirmed_timezone_mismatch = False
            
            profile.save()
            
            # Send email if timezone was changed (not first time setting)
            # Condition: old_selected_timezone was not empty AND it's different from new one
            if old_selected_timezone and old_selected_timezone.strip() and old_selected_timezone != time_zone and time_zone:
                try:
                    from general.email_service import EmailService
                    EmailService.send_timezone_change_email(
                        user=request.user,
                        new_timezone=time_zone,
                        old_timezone=old_selected_timezone
                    )
                except Exception as e:
                    # Log error but don't fail the request
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error sending timezone change email: {str(e)}")
            
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
            old_session_length = profile.session_length
            has_collisions = False
            
            if session_length:
                try:
                    new_session_length = int(session_length)
                    profile.session_length = new_session_length
                except ValueError:
                    profile.session_length = None
                    new_session_length = None
            else:
                profile.session_length = None
                new_session_length = None
            
            # If session length changed, update availability slots
            if old_session_length and new_session_length and old_session_length != new_session_length:
                has_collisions = update_slots_for_session_length(
                    profile, old_session_length, new_session_length
                )
                # Persist collision state for search/filtering and recovery UX
                profile.collisions = bool(has_collisions)
            elif new_session_length is None:
                # If session length is cleared, treat as no collision requirement
                profile.collisions = False
            
            # Handle first session free (boolean checkbox)
            profile.first_session_free = request.POST.get("first_session_free") == "on"
            
            # Handle first session length (only if first_session_free is True)
            first_session_length = request.POST.get("first_session_length", "")
            if profile.first_session_free and first_session_length:
                try:
                    first_session_length_int = int(first_session_length)
                    # Validate: first session length cannot exceed regular session length
                    if new_session_length and first_session_length_int > new_session_length:
                        from django.contrib import messages
                        messages.error(request, f'The first session length ({first_session_length_int} minutes) cannot be longer than the regular session length ({new_session_length} minutes). Please increase your regular session length first.')
                        return redirect("/dashboard/mentor/profile/")
                    profile.first_session_length = first_session_length_int
                except ValueError:
                    profile.first_session_length = None
            else:
                profile.first_session_length = None
            
            # Handle social media and links
            profile.instagram_name = instagram_name.strip() if instagram_name else None
            profile.linkedin_name = linkedin_name.strip() if linkedin_name else None
            profile.personal_website = personal_website.strip() if personal_website else None
            
            # Handle Video Introduction
            video_introduction_url = request.POST.get("video_introduction_url", "")
            profile.video_introduction_url = video_introduction_url.strip() if video_introduction_url else None
            
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
            if has_collisions:
                messages.warning(
                    request, 
                    'Session length updated, but collisions detected in availability slots. '
                    'Please review and resolve collisions in the calendar.'
                )
                # Redirect to my_sessions page with flag to open calendar
                return redirect("/dashboard/mentor/my-sessions/?open_calendar=true")
            else:
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
    
    # Check if collisions still exist (to filter out stale collision warnings)
    has_collisions_now = False
    if profile.session_length:
        try:
            one_time_slots = list(profile.one_time_slots or [])
        except AttributeError:
            one_time_slots = list(profile.availability_slots or [])
        
        try:
            recurring_slots = list(profile.recurring_slots or [])
        except AttributeError:
            recurring_slots = list(profile.recurring_availability_slots or [])
        
        mentor_tz = profile.selected_timezone or profile.time_zone or 'UTC'
        has_collisions_now = check_slot_collisions(
            one_time_slots,
            recurring_slots,
            profile.session_length,
            mentor_timezone_str=mentor_tz,
            sessions=list(profile.sessions.all())
        )
    
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
        'has_collisions_now': has_collisions_now,
        'debug': settings.DEBUG,
    })

@login_required
def settings_view(request):
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing mentor dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'mentor':
        return redirect('general:index')
    
    user = request.user
    profile = user.profile
    
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "update_timezone":
            time_zone = request.POST.get("time_zone", "")
            
            # Store old timezone before updating
            old_selected_timezone = profile.selected_timezone
            
            profile.time_zone = time_zone
            # Also update selected_timezone and clear confirmed mismatch when user updates via settings form
            if time_zone:
                profile.selected_timezone = time_zone
                profile.confirmed_timezone_mismatch = False
            
            profile.save()
            
            # Send email if timezone was changed (not first time setting)
            # Condition: old_selected_timezone was not empty AND it's different from new one
            if old_selected_timezone and old_selected_timezone.strip() and old_selected_timezone != time_zone and time_zone:
                try:
                    from general.email_service import EmailService
                    EmailService.send_timezone_change_email(
                        user=request.user,
                        new_timezone=time_zone,
                        old_timezone=old_selected_timezone
                    )
                except Exception as e:
                    # Log error but don't fail the request
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error sending timezone change email: {str(e)}")
            
            messages.success(request, "Timezone updated successfully.")
            return redirect("/dashboard/mentor/settings/")
    
    return render(
        request,
        'dashboard_mentor/settings.html',
        {
            'debug': settings.DEBUG,
        },
    )

@login_required
def support_view(request):
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing mentor dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'mentor':
        return redirect('general:index')
    
    from general.forms import TicketForm
    from general.models import Ticket
    
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.save()
            
            # Send email to admin
            from general.email_service import EmailService
            try:
                EmailService.send_ticket_created_email(ticket)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Error sending ticket created email: {str(e)}')
            
            messages.success(request, 'Your support ticket has been submitted successfully. We will get back to you soon!')
            return redirect('general:dashboard_mentor:support')
    else:
        form = TicketForm()
    
    # Get user's tickets
    user_tickets = Ticket.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    return render(
        request,
        'dashboard_mentor/support.html',
        {
            'debug': settings.DEBUG,
            'form': form,
            'user_tickets': user_tickets,
        },
    )


@login_required
def ticket_detail(request, ticket_id):
    """View ticket details and add comments"""
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing mentor dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'mentor':
        return redirect('general:index')
    
    from general.models import Ticket, TicketComment
    from general.forms import TicketCommentForm
    from general.email_service import EmailService
    from accounts.models import CustomUser
    
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_comment':
            form = TicketCommentForm(request.POST, request.FILES)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.ticket = ticket
                comment.user = request.user
                comment.save()
                
                # Send email to admin and create notification for all admins
                try:
                    EmailService.send_ticket_comment_email(ticket, comment, request.user)
                    
                    # Create notification for all admin users
                    admin_users = CustomUser.objects.filter(
                        is_active=True,
                        admin_profile__isnull=False
                    )
                    from general.models import Notification
                    from django.urls import reverse
                    import uuid
                    batch_id = uuid.uuid4()
                    
                    user_name = ticket.user.profile.first_name if hasattr(ticket.user, 'profile') and ticket.user.profile and ticket.user.profile.first_name else ticket.user.email.split('@')[0]
                    ticket_url = f"{EmailService.get_site_domain()}{reverse('general:dashboard_admin:ticket_detail', args=[ticket.id])}"
                    for admin_user in admin_users:
                        Notification.objects.create(
                            user=admin_user,
                            batch_id=batch_id,
                            target_type='single',
                            title=f"New comment on ticket #{ticket.id}",
                            description=f"{user_name} added a comment to ticket: {ticket.title}. <a href=\"{ticket_url}\" style=\"color: #10b981; text-decoration: underline;\">View ticket</a>"
                        )
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f'Error sending ticket comment email: {str(e)}')
                
                messages.success(request, 'Your comment has been added.')
                return redirect('general:dashboard_mentor:ticket_detail', ticket_id=ticket.id)
        elif action == 'update_status' and request.user.profile.role == 'admin':
            # Only admins can update status
            new_status = request.POST.get('status')
            if new_status in dict(Ticket.STATUS_CHOICES):
                old_status = ticket.status
                ticket.status = new_status
                ticket.save()
                
                # If marked as resolved, send email and notification
                if new_status == 'resolved' and old_status != 'resolved':
                    try:
                        EmailService.send_ticket_resolved_email(ticket)
                        
                        # Create notification for ticket creator
                        from general.models import Notification
                        from django.urls import reverse
                        import uuid
                        ticket_url = f"{EmailService.get_site_domain()}{reverse('general:dashboard_mentor:ticket_detail', args=[ticket.id])}"
                        Notification.objects.create(
                            user=ticket.user,
                            batch_id=uuid.uuid4(),
                            target_type='single',
                            title=f"Your ticket has been resolved",
                            description=f"Ticket #{ticket.id}: {ticket.title} has been marked as resolved. <a href=\"{ticket_url}\" style=\"color: #10b981; text-decoration: underline;\">View ticket</a>"
                        )
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f'Error sending ticket resolved email: {str(e)}')
                
                messages.success(request, f'Ticket status updated to {ticket.get_status_display()}.')
                return redirect('general:dashboard_mentor:ticket_detail', ticket_id=ticket.id)
    
    form = TicketCommentForm()
    comments = ticket.comments.all().order_by('created_at')
    
    return render(
        request,
        'dashboard_mentor/ticket_detail.html',
        {
            'ticket': ticket,
            'form': form,
            'comments': comments,
        },
    )

@login_required
def billing(request):
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing mentor dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'mentor':
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
        'debug': settings.DEBUG,
    })

@login_required
def my_sessions(request):
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing mentor dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'mentor':
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
    
    # Get mentor's timezone (use selected_timezone, fallback to time_zone)
    mentor_timezone = mentor_profile.selected_timezone or mentor_profile.time_zone or 'UTC'
    
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
    
    # Fetch initial sessions (first page)
    from general.models import Session
    from django.utils import timezone
    now = timezone.now()
    
    # Get all upcoming sessions (invited and confirmed) - first page
    initial_sessions = []
    try:
        all_upcoming = mentor_profile.sessions.filter(
            status__in=['invited', 'confirmed'],
            start_datetime__gte=now
        ).order_by('start_datetime').select_related('created_by').prefetch_related('attendees')
        
        # Get first 10 sessions for initial load
        sessions_queryset = all_upcoming[:10]
        
        # Format sessions for template
        for session in sessions_queryset:
            # Get first attendee (client) if any
            client = session.attendees.first() if session.attendees.exists() else None
            client_name = None
            if client and hasattr(client, 'profile'):
                client_name = f"{client.profile.first_name} {client.profile.last_name}".strip()
                if not client_name:
                    client_name = client.email.split('@')[0]
            
            # Check if this is the first session with this client
            is_first_session = False
            if client:
                try:
                    user_profile = client.user_profile if hasattr(client, 'user_profile') else None
                    if user_profile:
                        # Get all sessions with this client (excluding cancelled/expired)
                        all_client_sessions = mentor_profile.sessions.filter(
                            attendees=client
                        ).exclude(status__in=['cancelled', 'expired']).exclude(id=session.id)
                        
                        # If there are no other sessions with this client, this is the first
                        if not all_client_sessions.exists():
                            is_first_session = True
                        else:
                            # Check if this session is the earliest one
                            earliest_session = all_client_sessions.order_by('start_datetime').first()
                            if earliest_session and session.start_datetime and earliest_session.start_datetime:
                                is_first_session = session.start_datetime <= earliest_session.start_datetime
                except Exception:
                    is_first_session = False
            
            initial_sessions.append({
                'id': session.id,
                'start_datetime': session.start_datetime,
                'end_datetime': session.end_datetime,
                'status': session.status,
                'client_name': client_name or 'Client',
                'note': session.note,
                'is_first_session': is_first_session,
            })
    except Exception as e:
        # Log error but don't fail the request
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching initial sessions: {str(e)}")
    
    # Check if calendar should auto-open (e.g., after session length change with collisions)
    open_calendar = request.GET.get('open_calendar', 'false').lower() == 'true'
    
    return render(request, 'dashboard_mentor/my_sessions.html', {
        'debug': settings.DEBUG,
        'availability_data': availability_data,
        'recurring_slots': recurring_slots_data,
        'session_length': session_length,
        'mentor_timezone': mentor_timezone,
        'open_calendar': open_calendar,
        'initial_sessions': initial_sessions,
    })

@login_required
def get_sessions_paginated(request):
    """API endpoint for paginated sessions (infinite scroll)"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        from general.models import Session
        from django.utils import timezone
        from django.core.paginator import Paginator
        
        mentor_profile = request.user.mentor_profile if hasattr(request.user, 'mentor_profile') else None
        if not mentor_profile:
            return JsonResponse({'success': False, 'error': 'Mentor profile not found'}, status=404)
        
        # Get pagination parameters
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 10))
        
        now = timezone.now()
        
        # Get all upcoming sessions (invited and confirmed)
        all_upcoming = mentor_profile.sessions.filter(
            status__in=['invited', 'confirmed'],
            start_datetime__gte=now
        ).order_by('start_datetime').select_related('created_by').prefetch_related('attendees')
        
        # Paginate
        paginator = Paginator(all_upcoming, per_page)
        page_obj = paginator.get_page(page)
        
        # Format sessions for JSON response
        sessions_data = []
        for session in page_obj:
            # Get first attendee (client) if any
            client = session.attendees.first() if session.attendees.exists() else None
            client_name = None
            if client and hasattr(client, 'profile'):
                client_name = f"{client.profile.first_name} {client.profile.last_name}".strip()
                if not client_name:
                    client_name = client.email.split('@')[0]
            
            sessions_data.append({
                'id': session.id,
                'start_datetime': session.start_datetime.isoformat(),
                'end_datetime': session.end_datetime.isoformat(),
                'status': session.status,
                'client_name': client_name or 'Client',
                'note': session.note or '',
            })
        
        return JsonResponse({
            'success': True,
            'sessions': sessions_data,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'current_page': page,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching paginated sessions: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def get_dashboard_upcoming_sessions(request):
    """API endpoint for dashboard upcoming sessions (max 4)"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        from general.models import Session
        from django.utils import timezone
        
        mentor_profile = request.user.mentor_profile if hasattr(request.user, 'mentor_profile') else None
        if not mentor_profile:
            return JsonResponse({'success': False, 'error': 'Mentor profile not found'}, status=404)
        
        now = timezone.now()
        
        # Get all upcoming sessions (invited and confirmed)
        all_upcoming = mentor_profile.sessions.filter(
            status__in=['invited', 'confirmed'],
            start_datetime__gte=now
        ).order_by('start_datetime').select_related('created_by').prefetch_related('attendees')
        
        # Get total count to check if there are more than 4
        total_count = all_upcoming.count()
        has_more_sessions = total_count > 4
        
        # Get first 4 sessions
        sessions_queryset = all_upcoming[:4]
        
        # Format sessions for JSON response
        sessions_data = []
        for session in sessions_queryset:
            # Get first attendee (client) if any
            client = session.attendees.first() if session.attendees.exists() else None
            client_name = None
            if client and hasattr(client, 'profile'):
                client_name = f"{client.profile.first_name} {client.profile.last_name}".strip()
                if not client_name:
                    client_name = client.email.split('@')[0]
            
            # Check if this is the first session with this client
            is_first_session = False
            if client:
                try:
                    user_profile = client.user_profile if hasattr(client, 'user_profile') else None
                    if user_profile:
                        # Get all sessions with this client (excluding cancelled/expired)
                        all_client_sessions = mentor_profile.sessions.filter(
                            attendees=client
                        ).exclude(status__in=['cancelled', 'expired']).exclude(id=session.id)
                        
                        # If there are no other sessions with this client, this is the first
                        if not all_client_sessions.exists():
                            is_first_session = True
                        else:
                            # Check if this session is the earliest one
                            earliest_session = all_client_sessions.order_by('start_datetime').first()
                            if earliest_session and session.start_datetime and earliest_session.start_datetime:
                                is_first_session = session.start_datetime <= earliest_session.start_datetime
                except Exception:
                    is_first_session = False
            
            sessions_data.append({
                'id': session.id,
                'start_datetime': session.start_datetime.isoformat(),
                'end_datetime': session.end_datetime.isoformat(),
                'status': session.status,
                'client_name': client_name or 'Client',
                'note': session.note or '',
                'is_first_session': is_first_session,
            })
        
        return JsonResponse({
            'success': True,
            'sessions': sessions_data,
            'has_more_sessions': has_more_sessions,
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_dashboard_upcoming_sessions: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

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
        try:
            import pytz
        except ImportError:
            pytz = None
        
        mentor_profile = request.user.mentor_profile
        data = json.loads(request.body)
        availability_list = data.get('availability', [])
        selected_date_str = data.get('selected_date')
        explicit_edited_dates = data.get('edited_dates', [])  # Dates that originally had slots

        # Sessions (client-side slots) to be persisted on Save
        sessions_payload = data.get('sessions', []) or []
        deleted_sessions_payload = data.get('deleted_sessions', []) or data.get('deleted_session_ids', []) or []
        
        # Get existing slots - use new field names with fallback to old for backward compatibility
        try:
            existing_one_time_slots = list(mentor_profile.one_time_slots or [])
        except AttributeError:
            existing_one_time_slots = list(mentor_profile.availability_slots or [])
        
        try:
            existing_recurring_slots = list(mentor_profile.recurring_slots or [])
        except AttributeError:
            existing_recurring_slots = list(mentor_profile.recurring_availability_slots or [])
        
        # Collect all dates that have slots in the request
        edited_dates = set()
        for avail_item in availability_list:
            date_str = avail_item.get('date')
            if date_str:
                edited_dates.add(date_str)
        
        # Also include explicitly provided dates (for handling deletions)
        if explicit_edited_dates:
            for date_str in explicit_edited_dates:
                edited_dates.add(date_str)
        
        # If no dates found but we have a selected_date, use that
        if not edited_dates and selected_date_str:
            edited_dates.add(selected_date_str)
        elif not edited_dates and availability_list and len(availability_list) > 0:
            # Fallback to first item's date
            date_str = availability_list[0].get('date')
            if date_str:
                edited_dates.add(date_str)
        
        if not edited_dates:
            return JsonResponse({'success': False, 'error': 'No date specified'}, status=400)
        
        # Convert date strings to date objects for comparison
        edited_date_objs = set()
        for date_str in edited_dates:
            try:
                edited_date_objs.add(datetime.strptime(date_str, '%Y-%m-%d').date())
            except ValueError:
                continue
        
        # Remove all existing one-time slots for any of the edited dates (we'll replace them)
        # We need to compare dates in the mentor's local timezone, not UTC
        final_one_time_slots = []
        
        # Get mentor's timezone for date conversion
        mentor_timezone_str = mentor_profile.selected_timezone or mentor_profile.time_zone or 'UTC'
        if pytz:
            try:
                mentor_tz = pytz.timezone(mentor_timezone_str)
            except Exception:
                mentor_tz = None
        else:
            mentor_tz = None
        
        for slot in existing_one_time_slots:
            try:
                # Parse the slot's start datetime - handle various formats
                slot_start_str = slot.get('start', '')
                if not slot_start_str:
                    continue
                
                # Normalize timezone indicators
                slot_start_str = slot_start_str.replace('Z', '+00:00')
                
                # Parse datetime - handle both timezone-aware and naive formats
                try:
                    slot_start_dt_utc = datetime.fromisoformat(slot_start_str)
                except ValueError:
                    # Try parsing without timezone info
                    slot_start_dt_utc = datetime.fromisoformat(slot_start_str.replace('+00:00', '').replace('-00:00', ''))
                    slot_start_dt_utc = timezone.make_aware(slot_start_dt_utc)
                
                # Ensure timezone-aware (should be UTC)
                if slot_start_dt_utc.tzinfo is None:
                    slot_start_dt_utc = timezone.make_aware(slot_start_dt_utc)
                else:
                    # Ensure it's UTC - only if pytz is available
                    if pytz:
                        if slot_start_dt_utc.tzinfo != pytz.UTC:
                            slot_start_dt_utc = slot_start_dt_utc.astimezone(pytz.UTC)
                    else:
                        # If pytz not available, use stdlib UTC.
                        # (Django 5 removed django.utils.timezone.utc)
                        slot_start_dt_utc = slot_start_dt_utc.astimezone(dt_timezone.utc)
                
                # Convert UTC datetime to mentor's local timezone to get the correct date
                if mentor_tz:
                    slot_start_dt_local = slot_start_dt_utc.astimezone(mentor_tz)
                    slot_date_local = slot_start_dt_local.date()
                else:
                    # Fallback: use UTC date
                    slot_date_local = slot_start_dt_utc.date()
                
                # Only keep slots that are NOT on any of the edited dates (compare local dates)
                if slot_date_local not in edited_date_objs:
                    final_one_time_slots.append(slot)
            except (ValueError, KeyError, AttributeError) as e:
                # Skip invalid slots but log for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f'Error parsing slot date: {e}, slot: {slot}')
                continue
        
        # Track which recurring slot IDs are being edited/converted (to remove old ones)
        edited_recurring_slot_ids = set()
        
        # Process new slots - each session becomes a separate slot
        new_one_time_slots = []
        new_recurring_slots = []
        
        for avail_item in availability_list:
            date_str = avail_item.get('date')
            start_date_str = avail_item.get('start_date') or date_str
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
                    
                    try:
                        # Get mentor's timezone to properly convert local time to UTC
                        mentor_timezone_str = mentor_profile.selected_timezone or mentor_profile.time_zone or 'UTC'
                        
                        # Parse the date and time as being in the mentor's local timezone
                        local_datetime_str = f"{date_str} {start_time}:00"
                        local_end_datetime_str = f"{date_str} {end_time}:00"
                        
                        # Parse as naive datetime (no timezone info)
                        start_dt_naive = datetime.strptime(local_datetime_str, '%Y-%m-%d %H:%M:%S')
                        end_dt_naive = datetime.strptime(local_end_datetime_str, '%Y-%m-%d %H:%M:%S')
                        
                        # Convert from mentor's timezone to UTC for storage
                        try:
                            import pytz
                            mentor_tz = pytz.timezone(mentor_timezone_str)
                            # Localize the naive datetime to mentor's timezone
                            start_dt_local = mentor_tz.localize(start_dt_naive)
                            end_dt_local = mentor_tz.localize(end_dt_naive)
                            # Convert to UTC
                            start_dt = start_dt_local.astimezone(pytz.UTC)
                            end_dt = end_dt_local.astimezone(pytz.UTC)
                        except (ImportError, Exception):
                            # Fallback: if pytz not available or timezone invalid, treat as UTC
                            # Make timezone-aware as UTC
                            start_dt = timezone.make_aware(start_dt_naive)
                            end_dt = timezone.make_aware(end_dt_naive)
                        
                        # Validate end > start
                        if end_dt <= start_dt:
                            continue
                        
                        # Calculate length
                        length_minutes = avail_item.get('length')
                        if not length_minutes or length_minutes <= 0:
                            length_minutes = int((end_dt - start_dt).total_seconds() / 60)
                        
                        # Preserve booked status if provided, otherwise default to False
                        booked = avail_item.get('booked', False)
                        # Note: When converting from recurring to one-time, booked status starts fresh (False)
                        # since recurring slots use booked_dates instead
                        
                        # Get type from request or default to 'availability_slot'
                        slot_type = avail_item.get('type', 'availability_slot')
                        
                        # Create one-time slot with preserved id and created_at
                        one_time_slot = {
                            'id': slot_id,
                            'start': start_dt.isoformat(),
                            'end': end_dt.isoformat(),
                            'length': length_minutes,
                            'booked': booked,
                            'type': slot_type,
                            'created_at': created_at
                        }
                        new_one_time_slots.append(one_time_slot)
                    except ValueError as e:
                        continue
                continue  # Skip to next item
            
            if is_recurring and recurrence_rule:
                # Check if this is a delete_all request
                delete_all = avail_item.get('delete_all', False)
                if delete_all and recurring_slot_id:
                    # Mark for complete deletion
                    edited_recurring_slot_ids.add(recurring_slot_id)
                    continue  # Skip adding this slot, it will be removed
                
                # Handle recurring slots (including skip_dates-only updates)
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
                    # Use the date from the current slot item
                    slot_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
                    if slot_date_obj:
                        weekday_index = slot_date_obj.weekday()  # 0=Monday, 6=Sunday
                        weekdays = [weekday_names[weekday_index]]
                    else:
                        weekdays = []
                elif slot_type == 'monthly':
                    # Monthly: day_of_month = selected date's day, weekdays ignored
                    # Use the date from the current slot item
                    slot_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
                    day_of_month = slot_date_obj.day if slot_date_obj else None  # 1-31
                    weekdays = []  # Ignored for monthly
                else:
                    # Fallback
                    weekdays = avail_item.get('weekdays', [])
                    day_of_month = avail_item.get('day_of_month')
                
                # If editing an existing recurring slot, preserve its ID and remove the old one
                if recurring_slot_id:
                    edited_recurring_slot_ids.add(recurring_slot_id)
                    slot_id = recurring_slot_id
                    # Find and preserve created_at, skip_dates, and booked_dates from existing slot
                    existing_slot = next((s for s in existing_recurring_slots if s.get('id') == recurring_slot_id), None)
                    created_at = existing_slot.get('created_at', timezone.now().isoformat()) if existing_slot else timezone.now().isoformat()
                    existing_start_date = existing_slot.get('start_date') if existing_slot else None
                    
                    # Check if type, start_time, or end_time changed - if so, reset skip_dates
                    existing_type = existing_slot.get('type') if existing_slot else None
                    existing_start_time = existing_slot.get('start_time') if existing_slot else None
                    existing_end_time = existing_slot.get('end_time') if existing_slot else None
                    
                    type_changed = existing_type != slot_type
                    start_time_changed = existing_start_time != start_time
                    end_time_changed = existing_end_time != end_time
                    
                    if type_changed or start_time_changed or end_time_changed:
                        # Configuration changed - reset skip_dates (they were specific to old config)
                        skip_dates = avail_item.get('skip_dates', [])  # Only use new skip_dates from request
                        # Also reset booked_dates when configuration changes
                        booked_dates = avail_item.get('booked_dates', [])
                    else:
                        # Configuration unchanged - merge skip_dates: keep existing ones and add new ones from request
                        existing_skip_dates = existing_slot.get('skip_dates', []) if existing_slot else []
                        new_skip_dates = avail_item.get('skip_dates', [])
                        # Combine and deduplicate skip_dates
                        skip_dates = list(set(existing_skip_dates + new_skip_dates))
                        
                        # Merge booked_dates: keep existing ones and add new ones from request
                        existing_booked_dates = existing_slot.get('booked_dates', []) if existing_slot else []
                        new_booked_dates = avail_item.get('booked_dates', [])
                        # Combine and deduplicate booked_dates
                        booked_dates = list(set(existing_booked_dates + new_booked_dates))
                else:
                    slot_id = str(uuid.uuid4())
                    created_at = timezone.now().isoformat()
                    skip_dates = avail_item.get('skip_dates', [])
                    booked_dates = avail_item.get('booked_dates', [])
                    existing_start_date = None
                
                # Get slot_type from request or default to 'availability_slot'
                slot_type_value = avail_item.get('slot_type', 'availability_slot')
                
                # Build recurring slot with proper structure
                recurring_slot = {
                    'id': slot_id,
                    'type': slot_type,
                    'slot_type': slot_type_value,
                    # Forward-only rendering: start_date is the first date this rule is effective.
                    # Prefer the provided start_date (from client), otherwise keep existing.
                    'start_date': start_date_str or existing_start_date or (date_str or ''),
                    'start_time': start_time,
                    'end_time': end_time,
                    'created_at': created_at
                }
                
                # Add skip_dates if any
                if skip_dates:
                    recurring_slot['skip_dates'] = skip_dates
                
                # Add booked_dates if any
                if booked_dates:
                    recurring_slot['booked_dates'] = booked_dates
                
                # Add weekdays for daily/weekly, day_of_month for monthly
                if slot_type == 'monthly':
                    recurring_slot['day_of_month'] = day_of_month
                else:
                    recurring_slot['weekdays'] = weekdays
                
                new_recurring_slots.append(recurring_slot)
            else:
                # Handle regular one-time slots (not converted)
                # Check if we have ISO strings directly (preferred method)
                start_iso = avail_item.get('start_iso')
                end_iso = avail_item.get('end_iso')
                
                if start_iso and end_iso:
                    # Use UTC ISO strings directly - FullCalendar handles timezone conversion
                    try:
                        # Parse ISO string (handle both Z and +00:00 formats)
                        start_iso_clean = start_iso.replace('Z', '+00:00')
                        end_iso_clean = end_iso.replace('Z', '+00:00')
                        start_dt = datetime.fromisoformat(start_iso_clean)
                        end_dt = datetime.fromisoformat(end_iso_clean)
                        
                        # Ensure timezone-aware (should already be UTC)
                        if start_dt.tzinfo is None:
                            start_dt = timezone.make_aware(start_dt)
                        if end_dt.tzinfo is None:
                            end_dt = timezone.make_aware(end_dt)
                    except (ValueError, AttributeError):
                        # If ISO parsing fails, skip this slot
                        continue
                elif all([date_str, start_time, end_time]):
                    # Fallback: parse date/time as UTC (times are already UTC from frontend)
                    utc_datetime_str = f"{date_str} {start_time}:00"
                    utc_end_datetime_str = f"{date_str} {end_time}:00"
                    start_dt_naive = datetime.strptime(utc_datetime_str, '%Y-%m-%d %H:%M:%S')
                    end_dt_naive = datetime.strptime(utc_end_datetime_str, '%Y-%m-%d %H:%M:%S')
                    start_dt = timezone.make_aware(start_dt_naive)
                    end_dt = timezone.make_aware(end_dt_naive)
                else:
                    continue
                
                try:
                    
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
                    
                    # Preserve booked status if provided, otherwise default to False
                    # Check if this slot already exists to preserve its booked status
                    booked = False
                    if slot_id:
                        existing_slot = next((s for s in existing_one_time_slots if s.get('id') == slot_id), None)
                        if existing_slot:
                            booked = existing_slot.get('booked', False)
                    
                    # Allow override from request
                    if 'booked' in avail_item:
                        booked = avail_item.get('booked', False)
                    
                    # Get type from request or default to 'availability_slot'
                    slot_type = avail_item.get('type', 'availability_slot')
                    
                    # Create one-time slot
                    one_time_slot = {
                        'id': slot_id,
                        'start': start_dt.isoformat(),
                        'end': end_dt.isoformat(),
                        'length': length_minutes,
                        'booked': booked,
                        'type': slot_type,
                        'created_at': created_at
                    }
                    new_one_time_slots.append(one_time_slot)
                except ValueError as e:
                    # Log the error for debugging
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f'Error processing one-time slot: {e}, avail_item: {avail_item}')
                    continue
                except Exception as e:
                    # Log unexpected errors
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f'Unexpected error processing one-time slot: {e}, avail_item: {avail_item}')
                    continue
        
        # Remove recurring slots that are being edited/converted (we'll replace or remove them)
        final_recurring_slots = [
            slot for slot in existing_recurring_slots
            if slot.get('id') not in edited_recurring_slot_ids
        ]
        
        # Merge: keep existing one-time slots from other dates + add new slots for edited date
        # Merge: keep existing recurring slots (except edited ones) + add new/updated recurring slots
        final_one_time_slots = final_one_time_slots + new_one_time_slots
        
        # Deduplicate by ID to prevent duplicates (keep the LAST occurrence, which preserves new slots)
        # Since new_one_time_slots are added after final_one_time_slots, duplicates will be new slots
        # We iterate and keep track of seen IDs, but when we see a duplicate, we replace the old one
        seen_ids = {}
        deduplicated_one_time_slots = []
        for slot in final_one_time_slots:
            slot_id = slot.get('id')
            if slot_id:
                if slot_id in seen_ids:
                    # Replace the old slot with the new one (new slots come later)
                    old_index = seen_ids[slot_id]
                    deduplicated_one_time_slots[old_index] = slot
                else:
                    # First time seeing this ID, add it
                    seen_ids[slot_id] = len(deduplicated_one_time_slots)
                    deduplicated_one_time_slots.append(slot)
            else:
                # Slots without IDs should still be added (shouldn't happen, but be safe)
                deduplicated_one_time_slots.append(slot)
        
        final_recurring_slots = final_recurring_slots + new_recurring_slots
        
        # Save to MentorProfile - use new field names (migration has been applied)
        # Store slots in UTC (standard time) - they will be displayed adjusted to mentor's timezone
        mentor_profile.one_time_slots = deduplicated_one_time_slots
        mentor_profile.recurring_slots = final_recurring_slots
        mentor_profile.save()

        # --- Persist Session records (create/update/delete) ---
        sessions_created = 0
        sessions_updated = 0
        sessions_deleted = 0
        changed_sessions_info = []  # Track changed sessions for email sending
        try:
            from general.models import Session
            from decimal import Decimal, InvalidOperation

            # Delete sessions that were removed client-side (only those linked to this mentor)
            # Collect session info before deletion for email notifications
            deleted_sessions_info = []  # Track deleted sessions for email sending
            to_delete_ids = []
            for raw in deleted_sessions_payload:
                try:
                    to_delete_ids.append(int(raw))
                except Exception:
                    continue
            # Track which session IDs were actually deleted (for filtering later)
            actually_deleted_ids = set()
            if to_delete_ids:
                # Get sessions with related data before deletion
                # IMPORTANT: Never delete terminal state sessions (completed, refunded, expired)
                # These are historical records that should be preserved
                sessions_to_delete = mentor_profile.sessions.filter(
                    id__in=to_delete_ids
                ).exclude(
                    status__in=['completed', 'refunded', 'expired']
                ).prefetch_related('attendees')
                
                # Log if any terminal state sessions were requested for deletion (for debugging)
                terminal_sessions = mentor_profile.sessions.filter(
                    id__in=to_delete_ids,
                    status__in=['completed', 'refunded', 'expired']
                )
                if terminal_sessions.exists():
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f'Attempted to delete {terminal_sessions.count()} terminal state session(s) '
                        f'(completed/refunded/expired). These sessions are protected and were not deleted. '
                        f'Session IDs: {list(terminal_sessions.values_list("id", flat=True))}'
                    )
                
                # Collect session info grouped by client email (extract all data before deletion)
                for session in sessions_to_delete:
                    # Extract session data before deletion
                    session_data = {
                        'id': session.id,
                        'start_datetime': session.start_datetime,
                        'end_datetime': session.end_datetime,
                        'session_price': session.session_price,
                        'session_type': getattr(session, 'session_type', 'individual'),
                        'status': session.status,
                    }
                    
                    # Get all attendees (clients) for this session
                    attendees = session.attendees.all()
                    if attendees.exists():
                        for attendee in attendees:
                            client_email = attendee.email.lower().strip()
                            if client_email:
                                deleted_sessions_info.append({
                                    'session_data': session_data,
                                    'client_email': client_email
                                })
                    else:
                        # If no attendees, try to get client email from session data
                        # This handles cases where session was created but not yet assigned
                        # We'll skip email for sessions without client emails
                        pass
                
                sessions_deleted = sessions_to_delete.count()
                # Store IDs before deletion
                actually_deleted_ids = set(sessions_to_delete.values_list('id', flat=True))
                sessions_to_delete.delete()

            # Get changed sessions data from request
            changed_sessions_payload = data.get('changed_sessions', [])
            changed_sessions_map = {}
            for changed_item in changed_sessions_payload:
                session_id = changed_item.get('session_id')
                if session_id:
                    try:
                        changed_sessions_map[int(session_id)] = changed_item.get('original_data', {})
                    except Exception:
                        continue

            # Create or update sessions from payload
            allowed_statuses = {'draft', 'invited', 'confirmed', 'cancelled', 'completed', 'refunded', 'expired'}
            for item in sessions_payload:
                try:
                    start_iso = item.get('start_iso') or item.get('start')
                    end_iso = item.get('end_iso') or item.get('end')
                    if not start_iso or not end_iso:
                        continue
                    start_dt = datetime.fromisoformat(str(start_iso).replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(str(end_iso).replace('Z', '+00:00'))
                    if start_dt.tzinfo is None:
                        start_dt = timezone.make_aware(start_dt)
                    if end_dt.tzinfo is None:
                        end_dt = timezone.make_aware(end_dt)
                    if end_dt <= start_dt:
                        continue

                    status = str(item.get('status') or 'draft').lower().strip()
                    if status not in allowed_statuses:
                        status = 'draft'

                    session_type = str(item.get('session_type') or 'individual').lower().strip() or 'individual'

                    # Session price: default from mentor price_per_hour * (session_length/60)
                    raw_price = item.get('session_price')
                    price_val = None
                    if raw_price not in (None, ''):
                        try:
                            price_val = Decimal(str(raw_price))
                        except (InvalidOperation, ValueError):
                            price_val = None
                    if price_val is None:
                        try:
                            if mentor_profile.price_per_hour and mentor_profile.session_length:
                                price_val = (Decimal(str(mentor_profile.price_per_hour)) * Decimal(str(mentor_profile.session_length))) / Decimal('60')
                                # Whole USD for now (no decimals in UI)
                                price_val = price_val.quantize(Decimal('1'))
                        except Exception:
                            price_val = None

                    client_email = (item.get('client_email') or '').strip().lower()
                    client_first_name = item.get('client_first_name') or None
                    client_last_name = item.get('client_last_name') or None

                    db_id = item.get('session_id') or item.get('id')
                    if db_id:
                        try:
                            db_id_int = int(db_id)
                        except Exception:
                            db_id_int = None
                        if db_id_int:
                            # Skip if this session was just deleted
                            if db_id_int in actually_deleted_ids:
                                continue
                            existing = mentor_profile.sessions.filter(id=db_id_int).first()
                            if existing:
                                # IMPORTANT: Never update terminal state sessions (completed, refunded, expired)
                                # unless they're explicitly being changed (in changed_sessions_map)
                                # Terminal state sessions should be preserved as-is
                                terminal_statuses = {'completed', 'refunded', 'expired'}
                                is_terminal = existing.status in terminal_statuses
                                is_changed = db_id_int in changed_sessions_map
                                
                                # Skip updating terminal state sessions that aren't being explicitly changed
                                if is_terminal and not is_changed:
                                    # Terminal state session is being sent just to preserve it
                                    # Don't update it - just skip to next session
                                    continue
                                
                                # Prepare original_data for email (use existing if available, otherwise from changed_sessions_map)
                                email_original_data = None
                                if existing.original_data:
                                    # Use existing original_data (preserves first change snapshot)
                                    email_original_data = existing.original_data
                                elif is_changed:
                                    # Use new snapshot from changed_sessions_map
                                    email_original_data = changed_sessions_map[db_id_int]
                                
                                # If this is a changed session, save original_data and set changed_by
                                # BUT: If session is 'invited' (not confirmed), don't set change tracking fields
                                # Instead, just update the session data - it will appear as an updated invitation
                                if is_changed:
                                    # If session is 'invited' (not confirmed), don't track as a change
                                    # Just update the session - it will show as an updated invitation
                                    # Only clear change tracking fields if session is actually 'invited' status
                                    if existing.status == 'invited':
                                        # Clear any existing change tracking fields (but only if they exist)
                                        # This ensures invited sessions don't show as "changes" in session management
                                        if existing.original_data is not None or existing.changed_by is not None:
                                            existing.original_data = None
                                            existing.changed_by = None
                                        if existing.previous_data is not None or existing.changes_requested_by is not None:
                                            existing.previous_data = None
                                            existing.changes_requested_by = None
                                    else:
                                        # Session is 'confirmed' or other status - track as a change
                                        # Only set original_data if it's not already populated
                                        # This preserves the original data from the first change, so the client
                                        # always sees comparisons against what they originally saw
                                        if not existing.original_data:
                                            original_data = changed_sessions_map[db_id_int]
                                            # Convert datetime objects to ISO strings for JSON storage
                                            if isinstance(original_data, dict):
                                                # Ensure start_datetime and end_datetime are ISO strings
                                                if 'start_datetime' in original_data:
                                                    if hasattr(original_data['start_datetime'], 'isoformat'):
                                                        original_data['start_datetime'] = original_data['start_datetime'].isoformat()
                                                if 'end_datetime' in original_data:
                                                    if hasattr(original_data['end_datetime'], 'isoformat'):
                                                        original_data['end_datetime'] = original_data['end_datetime'].isoformat()
                                            existing.original_data = original_data
                                        # Set changed_by to indicate mentor made changes
                                        existing.changed_by = 'mentor'
                                        # If status was 'confirmed', change to 'invited' for re-confirmation
                                        if existing.status == 'confirmed':
                                            status = 'invited'
                                
                                # For terminal state sessions that are being changed, preserve their status
                                # (they shouldn't be changed, but if they are, at least preserve the terminal status)
                                if is_terminal and is_changed:
                                    # Don't change the status of terminal state sessions
                                    status = existing.status
                                
                                existing.start_datetime = start_dt
                                existing.end_datetime = end_dt
                                existing.status = status
                                existing.session_price = price_val
                                existing.client_first_name = client_first_name
                                existing.client_last_name = client_last_name
                                # expires_at left as-is for now
                                if hasattr(existing, 'session_type'):
                                    existing.session_type = session_type
                                existing.save()
                                
                                # Track changed session for email sending
                                # Send email whenever there are changes detected (session in changed_sessions_map)
                                # This ensures emails are sent for every save that includes changes, even if original_data already exists
                                # The email template will only show fields that actually changed
                                if is_changed and client_email:
                                    # Ensure we have original_data - use from changed_sessions_map if email_original_data is None
                                    final_original_data = email_original_data
                                    if not final_original_data and db_id_int in changed_sessions_map:
                                        final_original_data = changed_sessions_map[db_id_int]
                                    
                                    if final_original_data:
                                        changed_sessions_info.append({
                                            'session': existing,
                                            'client_email': client_email,
                                            'original_data': final_original_data
                                        })
                                
                                # Assign attendee if email provided and user exists
                                if client_email:
                                    try:
                                        client_user = CustomUser.objects.filter(email=client_email).first()
                                        if client_user:
                                            existing.attendees.set([client_user])
                                    except Exception:
                                        pass
                                sessions_updated += 1
                                continue

                    # Look up client name if client_email is provided
                    client_first_name = None
                    client_last_name = None
                    if client_email:
                        try:
                            client_user = CustomUser.objects.filter(email=client_email).first()
                            if client_user:
                                try:
                                    user_profile = client_user.user_profile
                                    if user_profile:
                                        client_first_name = user_profile.first_name or ''
                                        client_last_name = user_profile.last_name or ''
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    
                    # Create new
                    s = Session.objects.create(
                        start_datetime=start_dt,
                        end_datetime=end_dt,
                        created_by=request.user,
                        note='',
                        session_type=session_type,
                        tasks=[],
                        status=status,
                        session_price=price_val,
                        expires_at=None,
                        client_first_name=client_first_name,
                        client_last_name=client_last_name
                    )
                    mentor_profile.sessions.add(s)
                    if client_email:
                        try:
                            client_user = CustomUser.objects.filter(email=client_email).first()
                            if client_user:
                                s.attendees.add(client_user)
                        except Exception:
                            pass
                    sessions_created += 1
                except Exception:
                    continue
        except Exception:
            # Non-fatal: availability saving should still succeed if sessions can't be saved
            pass

        # Send emails for deleted sessions (grouped by client email)
        deleted_clients_notified_count = 0
        if deleted_sessions_info:
            try:
                from django.urls import reverse
                from general.email_service import EmailService
                
                # Group deleted sessions by client email
                deleted_sessions_by_client = {}
                for item in deleted_sessions_info:
                    client_email = item['client_email']
                    if client_email not in deleted_sessions_by_client:
                        deleted_sessions_by_client[client_email] = []
                    deleted_sessions_by_client[client_email].append(item['session_data'])
                
                # Send one email per client with all their deleted sessions
                for client_email, deleted_sessions_list in deleted_sessions_by_client.items():
                    try:
                        # Get mentor name
                        mentor_name = ''
                        try:
                            mentor_name = f"{mentor_profile.first_name} {mentor_profile.last_name}".strip()
                        except Exception:
                            mentor_name = 'your mentor'
                        
                        # Send email
                        EmailService.send_email(
                            subject=f'Session Cancelled',
                            recipient_email=client_email,
                            template_name='session_deleted_notification',
                            context={
                                'mentor_name': mentor_name,
                                'deleted_sessions': deleted_sessions_list,
                                'client_email': client_email
                            },
                            fail_silently=True
                        )
                        # Count successful email sends
                        deleted_clients_notified_count += 1
                    except Exception as e:
                        # Log error but don't fail the save
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f'Error sending session deleted email to {client_email}: {str(e)}')
                        continue
            except Exception as e:
                # Non-fatal: log but don't fail the save
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Error processing session deleted emails: {str(e)}')
        
        # Send emails for changed sessions (grouped by client email)
        clients_notified_count = 0
        if changed_sessions_info:
            try:
                from django.urls import reverse
                from general.email_service import EmailService
                
                # Group changed sessions by client email
                sessions_by_client = {}
                for item in changed_sessions_info:
                    client_email = item['client_email']
                    if client_email not in sessions_by_client:
                        sessions_by_client[client_email] = []
                    sessions_by_client[client_email].append(item)
                
                # Send one email per client with all their changes
                site_domain = EmailService.get_site_domain()
                for client_email, client_sessions in sessions_by_client.items():
                    try:
                        # Create a stable link for session management
                        from urllib.parse import quote
                        session_management_url = f"{site_domain}{reverse('accounts:session_changes_link')}?email={quote(client_email)}"
                        
                        # Prepare session changes data for email and determine change type
                        session_changes = []
                        has_datetime_change = False
                        has_price_change = False
                        
                        for item in client_sessions:
                            session = item['session']
                            original_data = item['original_data']
                            
                            # Parse ISO datetime strings in original_data to datetime objects for template
                            if isinstance(original_data, dict):
                                from datetime import datetime
                                from django.utils import timezone as dj_timezone
                                from decimal import Decimal, InvalidOperation
                                parsed_original_data = original_data.copy()
                                try:
                                    if 'start_datetime' in parsed_original_data and isinstance(parsed_original_data['start_datetime'], str):
                                        dt = datetime.fromisoformat(parsed_original_data['start_datetime'].replace('Z', '+00:00'))
                                        if dt.tzinfo is None:
                                            dt = dj_timezone.make_aware(dt)
                                        parsed_original_data['start_datetime'] = dt
                                    if 'end_datetime' in parsed_original_data and isinstance(parsed_original_data['end_datetime'], str):
                                        dt = datetime.fromisoformat(parsed_original_data['end_datetime'].replace('Z', '+00:00'))
                                        if dt.tzinfo is None:
                                            dt = dj_timezone.make_aware(dt)
                                        parsed_original_data['end_datetime'] = dt
                                except Exception:
                                    pass
                                
                                # Check if datetime changed for this session
                                session_datetime_changed = False
                                try:
                                    orig_start = parsed_original_data.get('start_datetime')
                                    orig_end = parsed_original_data.get('end_datetime')
                                    if orig_start and orig_end:
                                        if isinstance(orig_start, str):
                                            orig_start = datetime.fromisoformat(orig_start.replace('Z', '+00:00'))
                                            if orig_start.tzinfo is None:
                                                orig_start = dj_timezone.make_aware(orig_start)
                                        if isinstance(orig_end, str):
                                            orig_end = datetime.fromisoformat(orig_end.replace('Z', '+00:00'))
                                            if orig_end.tzinfo is None:
                                                orig_end = dj_timezone.make_aware(orig_end)
                                        if session.start_datetime != orig_start or session.end_datetime != orig_end:
                                            session_datetime_changed = True
                                            has_datetime_change = True
                                except Exception:
                                    pass
                                
                                # Check if price changed for this session (normalize for comparison)
                                session_price_changed = False
                                try:
                                    orig_price = parsed_original_data.get('session_price')
                                    current_price = session.session_price
                                    
                                    # Normalize both to Decimal for comparison
                                    def normalize_price(p):
                                        if p is None:
                                            return None
                                        try:
                                            return Decimal(str(p))
                                        except (InvalidOperation, ValueError, TypeError):
                                            return None
                                    
                                    orig_price_norm = normalize_price(orig_price)
                                    current_price_norm = normalize_price(current_price)
                                    
                                    if orig_price_norm != current_price_norm:
                                        session_price_changed = True
                                        has_price_change = True
                                except Exception:
                                    pass
                            else:
                                parsed_original_data = original_data
                            
                            session_changes.append({
                                'session': session,
                                'original_data': parsed_original_data
                            })
                        
                        # Determine which template to use based on what changed across all sessions
                        if has_datetime_change and has_price_change:
                            template_name = 'session_changes_both'
                        elif has_datetime_change:
                            template_name = 'session_changes_datetime_only'
                        elif has_price_change:
                            template_name = 'session_changes_price_only'
                        else:
                            # No actual changes detected - skip email (shouldn't happen, but safety check)
                            continue
                        
                        # Get mentor name
                        mentor_name = ''
                        try:
                            mentor_name = f"{mentor_profile.first_name} {mentor_profile.last_name}".strip()
                        except Exception:
                            mentor_name = 'your mentor'
                        
                        # Send email with appropriate template
                        EmailService.send_email(
                            subject=f'Session Changes - Action Required',
                            recipient_email=client_email,
                            template_name=template_name,
                            context={
                                'mentor_name': mentor_name,
                                'session_changes': session_changes,
                                'action_url': session_management_url,
                                'client_email': client_email
                            },
                            fail_silently=True
                        )
                        # Count successful email sends
                        clients_notified_count += 1
                    except Exception as e:
                        # Log error but don't fail the save
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f'Error sending session changes email to {client_email}: {str(e)}')
                        continue
            except Exception as e:
                # Non-fatal: log but don't fail the save
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Error processing session changes emails: {str(e)}')

        # If we're able to save, update collision flag based on current DB state.
        # Important: the UI is only allowed to save when collisions are resolved.
        # So we always clear the flag on successful save, then (optionally) recompute it.
        mentor_profile.collisions = False
        try:
            if mentor_profile.session_length:
                mentor_tz = mentor_profile.selected_timezone or mentor_profile.time_zone or 'UTC'
                has_collisions_now = check_slot_collisions(
                    list(mentor_profile.one_time_slots or []),
                    list(mentor_profile.recurring_slots or []),
                    mentor_profile.session_length,
                    mentor_timezone_str=mentor_tz,
                    sessions=list(mentor_profile.sessions.all())
                )
                mentor_profile.collisions = bool(has_collisions_now)
        except Exception:
            # Non-fatal: if collision recompute fails for any reason, keep collisions=False
            mentor_profile.collisions = False
        mentor_profile.save(update_fields=['collisions'])
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'Saved availability: {len(new_one_time_slots)} new one-time slots, {len(deduplicated_one_time_slots)} total one-time slots')
        
        # Create a summary message with all edited dates
        dates_summary = ', '.join(sorted(edited_dates)) if edited_dates else 'selected date(s)'
        return JsonResponse({
            'success': True,
            'message': f'Successfully saved {len(new_one_time_slots)} one-time slot(s) and {len(new_recurring_slots)} recurring slot(s) for {dates_summary}',
            'one_time_count': len(new_one_time_slots),
            'recurring_count': len(new_recurring_slots),
            'total_one_time_slots': len(deduplicated_one_time_slots),
            'sessions_created': sessions_created,
            'sessions_updated': sessions_updated,
            'sessions_deleted': sessions_deleted,
            'clients_notified': clients_notified_count,
            'deleted_clients_notified': deleted_clients_notified_count,
            'dates': sorted(list(edited_dates)) if edited_dates else []
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        # Log the full error with traceback for debugging
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f'Error saving availability: {str(e)}\n{traceback.format_exc()}')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def get_availability(request):
    """Get mentor availability slots from profile"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return JsonResponse({'success': False, 'error': 'Only mentors can fetch availability'}, status=403)
    
    try:
        # Run cleanup synchronously before fetching calendar data
        from general.cleanup.availability_slots import cleanup_expired_availability_slots
        from general.cleanup.session_slots import cleanup_draft_sessions
        cleanup_expired_availability_slots()
        cleanup_draft_sessions()
        
        mentor_profile = request.user.mentor_profile
        
        # Get one-time slots - use new field name with fallback to old
        try:
            one_time_slots = list(mentor_profile.one_time_slots or [])
        except AttributeError:
            one_time_slots = list(mentor_profile.availability_slots or [])
        
        # Get recurring slots - use new field name with fallback to old
        try:
            recurring_slots = list(mentor_profile.recurring_slots or [])
        except AttributeError:
            recurring_slots = list(mentor_profile.recurring_availability_slots or [])

        # Sessions linked to this mentor (stored as real Session records)
        sessions = []
        try:
            from django.utils import timezone as dj_timezone
            from general.models import Session
            from general.models import SessionInvitation

            # Prefetch latest invitation per session (best-effort; used for reminder gating + UI)
            invitation_by_session_id = {}
            try:
                inv_qs = SessionInvitation.objects.filter(
                    session__in=mentor_profile.sessions.all(),
                    cancelled_at__isnull=True
                ).order_by('-created_at')
                for inv in inv_qs:
                    if inv.session_id not in invitation_by_session_id:
                        invitation_by_session_id[inv.session_id] = inv
            except Exception:
                invitation_by_session_id = {}

            for s in mentor_profile.sessions.all():
                start_dt = s.start_datetime
                end_dt = s.end_datetime
                # Ensure ISO strings are timezone-aware
                if start_dt and start_dt.tzinfo is None:
                    start_dt = dj_timezone.make_aware(start_dt)
                if end_dt and end_dt.tzinfo is None:
                    end_dt = dj_timezone.make_aware(end_dt)
                exp_dt = s.expires_at
                if exp_dt and exp_dt.tzinfo is None:
                    exp_dt = dj_timezone.make_aware(exp_dt)
                client = s.attendees.first() if s.attendees.exists() else None
                client_email = client.email if client else None

                # Check if this is the first session with this client
                is_first_session = False
                if client:
                    try:
                        user_profile = client.user_profile if hasattr(client, 'user_profile') else None
                        if user_profile:
                            # Get all sessions with this client (excluding cancelled/expired)
                            all_client_sessions = mentor_profile.sessions.filter(
                                attendees=client
                            ).exclude(status__in=['cancelled', 'expired']).exclude(id=s.id)
                            
                            # If there are no other sessions with this client, this is the first
                            if not all_client_sessions.exists():
                                is_first_session = True
                            else:
                                # Check if this session is the earliest one
                                earliest_session = all_client_sessions.order_by('start_datetime').first()
                                if earliest_session and start_dt and earliest_session.start_datetime:
                                    # Compare with timezone awareness
                                    if start_dt.tzinfo is None:
                                        start_dt = dj_timezone.make_aware(start_dt)
                                    if earliest_session.start_datetime.tzinfo is None:
                                        earliest_dt = dj_timezone.make_aware(earliest_session.start_datetime)
                                    else:
                                        earliest_dt = earliest_session.start_datetime
                                    is_first_session = start_dt <= earliest_dt
                    except Exception:
                        is_first_session = False

                inv = invitation_by_session_id.get(s.id)
                invitation_sent = bool(inv) and bool(client_email)
                can_remind = False
                last_sent_at = None
                try:
                    if inv and inv.last_sent_at:
                        last_sent_at = inv.last_sent_at
                    elif inv and inv.created_at:
                        last_sent_at = inv.created_at
                    if last_sent_at:
                        can_remind = (dj_timezone.localdate(last_sent_at) != dj_timezone.localdate())
                except Exception:
                    can_remind = False

                sessions.append({
                    'id': s.id,
                    'start': start_dt.isoformat() if start_dt else None,
                    'end': end_dt.isoformat() if end_dt else None,
                    'status': getattr(s, 'status', 'draft') or 'draft',
                    'session_price': str(s.session_price) if getattr(s, 'session_price', None) is not None else None,
                    'expires_at': exp_dt.isoformat() if exp_dt else None,
                    'session_type': getattr(s, 'session_type', 'individual') or 'individual',
                    'client_email': client_email,
                    'client_first_name': getattr(s, 'client_first_name', None) or None,
                    'client_last_name': getattr(s, 'client_last_name', None) or None,
                    'invitation_sent': invitation_sent,
                    'can_remind': can_remind,
                    'last_invite_sent_at': last_sent_at.isoformat() if last_sent_at else None,
                    'is_first_session': is_first_session,
                })
        except Exception:
            sessions = []
        
        return JsonResponse({
            'success': True,
            'one_time_slots': one_time_slots,
            'recurring_slots': recurring_slots,
            'sessions': sessions
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def client_suggestions(request):
    """Return mentor client suggestions for session assignment (name/email)."""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return JsonResponse({'success': False, 'clients': []}, status=403)

    try:
        mentor_profile = request.user.mentor_profile
        relationships = MentorClientRelationship.objects.filter(
            mentor=mentor_profile,
            confirmed=True
        ).select_related('client', 'client__user').order_by('client__first_name', 'client__last_name')

        clients = []
        for rel in relationships:
            try:
                up = rel.client
                email = up.user.email if up and up.user else ''
                clients.append({
                    'first_name': up.first_name if up else '',
                    'last_name': up.last_name if up else '',
                    'email': email,
                })
            except Exception:
                continue

        return JsonResponse({'success': True, 'clients': clients})
    except Exception as e:
        return JsonResponse({'success': False, 'clients': [], 'error': str(e)}, status=500)


@login_required
def check_availability_collisions(request):
    """Check if mentor has any collisions in availability slots"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return JsonResponse({'success': False, 'has_collisions': False}, status=403)
    
    try:
        mentor_profile = request.user.mentor_profile

        # Primary source of truth is persisted collision state.
        has_collisions = bool(getattr(mentor_profile, 'collisions', False))

        # Self-heal: if the flag is true, recompute with mentor timezone and clear it if resolved.
        # This prevents the "calendar keeps auto-opening" issue after collisions are fixed.
        try:
            if has_collisions and mentor_profile.session_length:
                mentor_tz = mentor_profile.selected_timezone or mentor_profile.time_zone or 'UTC'
                # Filter out cancelled sessions from collision detection
                all_sessions = mentor_profile.sessions.exclude(status='cancelled')
                recomputed = check_slot_collisions(
                    list(mentor_profile.one_time_slots or []),
                    list(mentor_profile.recurring_slots or []),
                    mentor_profile.session_length,
                    mentor_timezone_str=mentor_tz,
                    sessions=list(all_sessions)
                )
                if bool(recomputed) != bool(has_collisions):
                    mentor_profile.collisions = bool(recomputed)
                    mentor_profile.save(update_fields=['collisions'])
                has_collisions = bool(recomputed)
            elif not mentor_profile.session_length and has_collisions:
                mentor_profile.collisions = False
                mentor_profile.save(update_fields=['collisions'])
                has_collisions = False
        except Exception:
            pass
        
        return JsonResponse({
            'success': True,
            'has_collisions': has_collisions
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'has_collisions': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def delete_availability_slot(request):
    """Delete a specific availability slot by ID"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return JsonResponse({'success': False, 'error': 'Only mentors can delete availability slots'}, status=403)
    
    try:
        import json
        mentor_profile = request.user.mentor_profile
        data = json.loads(request.body)
        slot_id = data.get('slot_id')
        
        if not slot_id:
            return JsonResponse({'success': False, 'error': 'Slot ID is required'}, status=400)
        
        # Get existing one-time slots - use new field name with fallback to old
        try:
            one_time_slots = list(mentor_profile.one_time_slots or [])
        except AttributeError:
            one_time_slots = list(mentor_profile.availability_slots or [])
        
        # Find and remove the slot with matching ID
        original_count = len(one_time_slots)
        one_time_slots = [slot for slot in one_time_slots if slot.get('id') != slot_id]
        
        if len(one_time_slots) == original_count:
            return JsonResponse({'success': False, 'error': 'Slot not found'}, status=404)
        
        # Save updated slots back to profile
        try:
            mentor_profile.one_time_slots = one_time_slots
        except AttributeError:
            mentor_profile.availability_slots = one_time_slots
        
        mentor_profile.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Availability slot deleted successfully'
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error deleting availability slot: {e}')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def invite_client(request):
    """Invite a client by email - creates unverified user and sends invitation"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return JsonResponse({'success': False, 'error': 'Only mentors can invite clients'}, status=403)
    
    mentor_profile = request.user.mentor_profile
    email = (request.POST.get('email', '') or '').strip().lower()
    if not email:
        # Support JSON payloads (used by some calendar popups)
        try:
            import json as _json
            data = _json.loads((request.body or b'{}').decode('utf-8') or '{}')
            email = (data.get('email', '') or '').strip().lower()
        except Exception:
            email = ''
    
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
@require_POST
def invite_session(request):
    """
    Send a session invitation email to a client (existing Session already saved in DB).
    If the user is unverified/new, the email links to complete-invitation then redirects back.
    """
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return JsonResponse({'success': False, 'error': 'Only mentors can invite clients'}, status=403)

    mentor_profile = request.user.mentor_profile
    try:
        import json as _json
        payload = _json.loads((request.body or b'{}').decode('utf-8') or '{}')
    except Exception:
        payload = {}

    email = (payload.get('email') or request.POST.get('email') or '').strip().lower()
    session_id = payload.get('session_id') or request.POST.get('session_id')
    start_iso = payload.get('start_iso')
    end_iso = payload.get('end_iso')

    if not email:
        return JsonResponse({'success': False, 'error': 'Email is required'}, status=400)
    try:
        session_id = int(session_id)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Session id is required'}, status=400)

    # Ensure session belongs to this mentor
    from general.models import Session, SessionInvitation
    s = mentor_profile.sessions.filter(id=session_id).first()
    if not s:
        return JsonResponse({'success': False, 'error': 'Session not found'}, status=404)
    
    # If current position (start_iso/end_iso) is provided, update the session to match
    # This handles the case where the session was moved in the calendar but not saved yet
    if start_iso and end_iso:
        try:
            from datetime import datetime
            from django.utils import timezone as dj_timezone
            new_start_dt = datetime.fromisoformat(str(start_iso).replace('Z', '+00:00'))
            new_end_dt = datetime.fromisoformat(str(end_iso).replace('Z', '+00:00'))
            if new_start_dt.tzinfo is None:
                new_start_dt = dj_timezone.make_aware(new_start_dt)
            if new_end_dt.tzinfo is None:
                new_end_dt = dj_timezone.make_aware(new_end_dt)
            
            # Only update if the position has actually changed
            if new_end_dt > new_start_dt:
                # Check if position changed (with small tolerance for timezone rounding)
                start_changed = abs((s.start_datetime - new_start_dt).total_seconds()) > 1
                end_changed = abs((s.end_datetime - new_end_dt).total_seconds()) > 1
                
                if start_changed or end_changed:
                    s.start_datetime = new_start_dt
                    s.end_datetime = new_end_dt
                    s.save(update_fields=['start_datetime', 'end_datetime'])
        except Exception as e:
            # Log error but don't fail the invitation - use existing session position
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f'Could not update session position before invitation: {str(e)}')

    # Resolve/create invited user + relationship token if needed
    try:
        existing_user = CustomUser.objects.filter(email=email).first()
    except Exception:
        existing_user = None

    relationship = None
    invited_user = None

    if existing_user:
        # Disallow inviting mentors via this flow
        try:
            if hasattr(existing_user, 'mentor_profile'):
                return JsonResponse({'success': False, 'error': 'This email belongs to a mentor account. Please use a different email.'}, status=400)
        except Exception:
            pass
        invited_user = existing_user
        try:
            user_profile = existing_user.user_profile
        except Exception:
            user_profile = None
        if user_profile:
            relationship = MentorClientRelationship.objects.filter(mentor=mentor_profile, client=user_profile).first()
            if not relationship:
                relationship = MentorClientRelationship.objects.create(
                    mentor=mentor_profile,
                    client=user_profile,
                    status='inactive',
                    confirmed=False,
                )
            # If user hasn't completed registration yet, ensure an invitation_token exists
            try:
                if not invited_user.is_email_verified and not relationship.invitation_token:
                    relationship.invitation_token = get_random_string(64)
                    relationship.save(update_fields=['invitation_token'])
            except Exception:
                pass
    else:
        # Create new unverified user (no separate client invite email; session email will take them through registration)
        temp_password = get_random_string(32)
        invited_user = CustomUser.objects.create_user(
            email=email,
            password=temp_password,
            is_email_verified=False,
            is_active=True
        )
        user_profile = UserProfile.objects.create(
            user=invited_user,
            first_name='',
            last_name='',
            role='user'
        )
        invitation_token = get_random_string(64)
        relationship = MentorClientRelationship.objects.create(
            mentor=mentor_profile,
            client=user_profile,
            status='inactive',
            confirmed=False,
            invitation_token=invitation_token
        )

    # Look up client name from user profile
    client_first_name = None
    client_last_name = None
    if invited_user:
        try:
            user_profile = invited_user.user_profile
            if user_profile:
                client_first_name = user_profile.first_name or ''
                client_last_name = user_profile.last_name or ''
        except Exception:
            pass
    
    # Attach attendee and set session status to invited
    try:
        if invited_user:
            s.attendees.set([invited_user])
        if getattr(s, 'status', None) != 'invited':
            s.status = 'invited'
        s.client_first_name = client_first_name
        s.client_last_name = client_last_name
        s.save(update_fields=['status', 'client_first_name', 'client_last_name'])
    except Exception:
        pass

    inv = SessionInvitation.objects.create(
        session=s,
        mentor=mentor_profile,
        invited_email=email,
        invited_user=invited_user if invited_user else None,
    )

    site_domain = EmailService.get_site_domain()
    from django.urls import reverse
    # Stable email link that always works (routes through login/registration as needed)
    action_url = f"{site_domain}{reverse('accounts:session_invitation_link', kwargs={'token': inv.token})}"

    # Format datetimes in invitee timezone for email display
    session_date_local = None
    session_start_time_local = None
    session_end_time_local = None
    invitee_timezone = None
    try:
        tz_name = None
        if invited_user and hasattr(invited_user, 'profile') and invited_user.profile:
            tz_name = (getattr(invited_user.profile, 'selected_timezone', None) or getattr(invited_user.profile, 'detected_timezone', None) or getattr(invited_user.profile, 'time_zone', None))
        tz_name = (tz_name or 'UTC')
        invitee_timezone = tz_name
        try:
            from zoneinfo import ZoneInfo
            tzinfo = ZoneInfo(str(tz_name))
        except Exception:
            tzinfo = dt_timezone.utc
        if s.start_datetime and s.end_datetime:
            start_local = s.start_datetime.astimezone(tzinfo)
            end_local = s.end_datetime.astimezone(tzinfo)
            session_date_local = start_local.strftime('%a, %b %d, %Y')
            session_start_time_local = start_local.strftime('%I:%M %p').lstrip('0')
            session_end_time_local = end_local.strftime('%I:%M %p').lstrip('0')
    except Exception:
        pass

    mentor_profile_url = None
    try:
        from django.urls import reverse
        mentor_profile_url = f"{site_domain}{reverse('web:mentor_profile_detail', kwargs={'user_id': mentor_profile.user_id})}"
    except Exception:
        mentor_profile_url = None

    # Email
    try:
        inv.last_sent_at = timezone.now()
        inv.save(update_fields=['last_sent_at'])
        EmailService.send_email(
            subject=f"Session invitation from {mentor_profile.first_name} {mentor_profile.last_name}",
            recipient_email=email,
            template_name='session_invitation',
            context={
                'mentor_name': f"{mentor_profile.first_name} {mentor_profile.last_name}",
                'mentor_profile_url': mentor_profile_url,
                'action_url': action_url,
                'session_start': s.start_datetime,
                'session_end': s.end_datetime,
                'session_date_local': session_date_local,
                'session_start_time_local': session_start_time_local,
                'session_end_time_local': session_end_time_local,
                'invitee_timezone': invitee_timezone,
                'session_price': getattr(s, 'session_price', None),
            }
        )
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Failed to send email: {e}'}, status=500)

    # Compute reminder gating
    can_remind = False
    try:
        can_remind = timezone.localdate(inv.last_sent_at) != timezone.localdate()
    except Exception:
        can_remind = False

    return JsonResponse({
        'success': True,
        'message': 'Session invitation sent.',
        'can_remind': can_remind,
        'last_sent_at': inv.last_sent_at.isoformat() if inv.last_sent_at else None,
    })


@login_required
@require_POST
def schedule_session(request):
    """
    Schedule a Session from an availability slot (one-time slot id or recurring rule+date),
    persist it immediately, remove/mark-booked the availability, and send a session invitation email.
    """
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return JsonResponse({'success': False, 'error': 'Only mentors can schedule sessions'}, status=403)

    mentor_profile = request.user.mentor_profile
    try:
        import json as _json
        payload = _json.loads((request.body or b'{}').decode('utf-8') or '{}')
    except Exception:
        payload = {}

    email = (payload.get('email') or '').strip().lower()
    start_iso = (payload.get('start_iso') or '').strip()
    end_iso = (payload.get('end_iso') or '').strip()
    availability_slot_id = (payload.get('availability_slot_id') or '').strip()
    recurring_id = (payload.get('recurring_id') or '').strip()
    instance_date = (payload.get('instance_date') or '').strip()

    if not email or not start_iso or not end_iso:
        return JsonResponse({'success': False, 'error': 'email, start_iso and end_iso are required'}, status=400)

    # Parse datetimes
    try:
        start_dt = datetime.fromisoformat(str(start_iso).replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(str(end_iso).replace('Z', '+00:00'))
        if start_dt.tzinfo is None:
            start_dt = timezone.make_aware(start_dt)
        if end_dt.tzinfo is None:
            end_dt = timezone.make_aware(end_dt)
        if end_dt <= start_dt:
            raise ValueError("end <= start")
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid start/end time'}, status=400)

    # Remove/mark-booked the availability source (so it doesn't collide with the new session)
    try:
        if recurring_id and instance_date:
            updated = False
            rules = list(getattr(mentor_profile, 'recurring_slots', []) or [])
            for r in rules:
                if str(r.get('id', '')) == recurring_id:
                    booked = r.get('booked_dates') or []
                    if not isinstance(booked, list):
                        booked = []
                    if instance_date not in booked:
                        booked.append(instance_date)
                    r['booked_dates'] = booked
                    updated = True
                    break
            if not updated:
                return JsonResponse({'success': False, 'error': 'This availability series was not found. Please refresh and try again.'}, status=400)
            mentor_profile.recurring_slots = rules
            mentor_profile.save(update_fields=['recurring_slots'])
        elif availability_slot_id:
            slots = list(getattr(mentor_profile, 'one_time_slots', []) or [])
            before_len = len(slots)
            slots = [s for s in slots if str(s.get('id', '')) != availability_slot_id]
            if len(slots) == before_len:
                return JsonResponse({'success': False, 'error': 'This availability slot is not saved yet. Please click Save, then try again.'}, status=400)
            mentor_profile.one_time_slots = slots
            mentor_profile.save(update_fields=['one_time_slots'])
        else:
            return JsonResponse({'success': False, 'error': 'availability_slot_id or (recurring_id + instance_date) is required'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Could not update availability: {e}'}, status=500)

    # Create the session
    from general.models import Session, SessionInvitation
    from decimal import Decimal
    duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
    price_val = None
    try:
        if mentor_profile.price_per_hour:
            price_val = (Decimal(str(mentor_profile.price_per_hour)) * Decimal(str(duration_minutes))) / Decimal('60')
            price_val = price_val.quantize(Decimal('1'))
    except Exception:
        price_val = None

    # Reuse invite_session logic for creating/locating user + relationship + sending email.
    # We'll inline the minimal parts so we can return session_id.
    try:
        existing_user = CustomUser.objects.filter(email=email).first()
    except Exception:
        existing_user = None

    relationship = None
    invited_user = None
    client_first_name = None
    client_last_name = None

    if existing_user:
        try:
            if hasattr(existing_user, 'mentor_profile'):
                return JsonResponse({'success': False, 'error': 'This email belongs to a mentor account. Please use a different email.'}, status=400)
        except Exception:
            pass
        invited_user = existing_user
        try:
            user_profile = existing_user.user_profile
            if user_profile:
                client_first_name = user_profile.first_name or ''
                client_last_name = user_profile.last_name or ''
        except Exception:
            user_profile = None
        if user_profile:
            relationship = MentorClientRelationship.objects.filter(mentor=mentor_profile, client=user_profile).first()
            if not relationship:
                relationship = MentorClientRelationship.objects.create(
                    mentor=mentor_profile,
                    client=user_profile,
                    status='inactive',
                    confirmed=False,
                )
            # If user hasn't completed registration yet, ensure an invitation_token exists
            try:
                if not invited_user.is_email_verified and not relationship.invitation_token:
                    relationship.invitation_token = get_random_string(64)
                    relationship.save(update_fields=['invitation_token'])
            except Exception:
                pass
    else:
        temp_password = get_random_string(32)
        invited_user = CustomUser.objects.create_user(
            email=email,
            password=temp_password,
            is_email_verified=False,
            is_active=True
        )
        user_profile = UserProfile.objects.create(
            user=invited_user,
            first_name='',
            last_name='',
            role='user'
        )
        invitation_token = get_random_string(64)
        relationship = MentorClientRelationship.objects.create(
            mentor=mentor_profile,
            client=user_profile,
            status='inactive',
            confirmed=False,
            invitation_token=invitation_token
        )

    s = Session.objects.create(
        start_datetime=start_dt,
        end_datetime=end_dt,
        created_by=request.user,
        note='',
        session_type='individual',
        status='invited',
        expires_at=None,
        session_price=price_val,
        client_first_name=client_first_name,
        client_last_name=client_last_name,
        tasks=[],
    )
    mentor_profile.sessions.add(s)

    try:
        if invited_user:
            s.attendees.set([invited_user])
    except Exception:
        pass

    inv = SessionInvitation.objects.create(
        session=s,
        mentor=mentor_profile,
        invited_email=email,
        invited_user=invited_user if invited_user else None,
    )

    site_domain = EmailService.get_site_domain()
    from django.urls import reverse
    # Stable email link that always works (routes through login/registration as needed)
    action_url = f"{site_domain}{reverse('accounts:session_invitation_link', kwargs={'token': inv.token})}"

    # Format datetimes in invitee timezone for email display
    session_date_local = None
    session_start_time_local = None
    session_end_time_local = None
    invitee_timezone = None
    try:
        tz_name = None
        if invited_user and hasattr(invited_user, 'profile') and invited_user.profile:
            tz_name = (getattr(invited_user.profile, 'selected_timezone', None) or getattr(invited_user.profile, 'detected_timezone', None) or getattr(invited_user.profile, 'time_zone', None))
        tz_name = (tz_name or 'UTC')
        invitee_timezone = tz_name
        try:
            from zoneinfo import ZoneInfo
            tzinfo = ZoneInfo(str(tz_name))
        except Exception:
            tzinfo = dt_timezone.utc
        if s.start_datetime and s.end_datetime:
            start_local = s.start_datetime.astimezone(tzinfo)
            end_local = s.end_datetime.astimezone(tzinfo)
            session_date_local = start_local.strftime('%a, %b %d, %Y')
            session_start_time_local = start_local.strftime('%I:%M %p').lstrip('0')
            session_end_time_local = end_local.strftime('%I:%M %p').lstrip('0')
    except Exception:
        pass

    mentor_profile_url = None
    try:
        from django.urls import reverse
        mentor_profile_url = f"{site_domain}{reverse('web:mentor_profile_detail', kwargs={'user_id': mentor_profile.user_id})}"
    except Exception:
        mentor_profile_url = None

    try:
        inv.last_sent_at = timezone.now()
        inv.save(update_fields=['last_sent_at'])
        EmailService.send_email(
            subject=f"Session invitation from {mentor_profile.first_name} {mentor_profile.last_name}",
            recipient_email=email,
            template_name='session_invitation',
            context={
                'mentor_name': f"{mentor_profile.first_name} {mentor_profile.last_name}",
                'mentor_profile_url': mentor_profile_url,
                'action_url': action_url,
                'session_start': s.start_datetime,
                'session_end': s.end_datetime,
                'session_date_local': session_date_local,
                'session_start_time_local': session_start_time_local,
                'session_end_time_local': session_end_time_local,
                'invitee_timezone': invitee_timezone,
                'session_price': getattr(s, 'session_price', None),
            }
        )
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Failed to send email: {e}'}, status=500)

    can_remind = False
    try:
        can_remind = timezone.localdate(inv.last_sent_at) != timezone.localdate()
    except Exception:
        can_remind = False

    return JsonResponse({
        'success': True,
        'message': 'Session scheduled and invitation sent.',
        'session_id': s.id,
        'can_remind': can_remind,
        'last_sent_at': inv.last_sent_at.isoformat() if inv.last_sent_at else None,
    })


@login_required
@require_POST
def refund_session(request):
    """Refund a completed session by changing its status to 'refunded'."""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return JsonResponse({'success': False, 'error': 'Only mentors can refund sessions'}, status=403)

    mentor_profile = request.user.mentor_profile
    try:
        import json as _json
        payload = _json.loads((request.body or b'{}').decode('utf-8') or '{}')
    except Exception:
        payload = {}

    session_id = payload.get('session_id') or request.POST.get('session_id')
    try:
        session_id = int(session_id)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Session id is required'}, status=400)

    from general.models import Session
    s = mentor_profile.sessions.filter(id=session_id).first()
    if not s:
        return JsonResponse({'success': False, 'error': 'Session not found'}, status=404)

    # Only allow refunding completed sessions
    if s.status != 'completed':
        return JsonResponse({'success': False, 'error': 'Only completed sessions can be refunded'}, status=400)

    # Change status to refunded
    s.status = 'refunded'
    s.save()

    return JsonResponse({'success': True, 'message': 'Session refunded successfully'})


@login_required
@require_POST
def remind_session(request):
    """Resend session invitation email. Limited to once per day per session invitation."""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return JsonResponse({'success': False, 'error': 'Only mentors can send reminders'}, status=403)

    mentor_profile = request.user.mentor_profile
    try:
        import json as _json
        payload = _json.loads((request.body or b'{}').decode('utf-8') or '{}')
    except Exception:
        payload = {}

    session_id = payload.get('session_id') or request.POST.get('session_id')
    try:
        session_id = int(session_id)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Session id is required'}, status=400)

    from general.models import SessionInvitation
    s = mentor_profile.sessions.filter(id=session_id).first()
    if not s:
        return JsonResponse({'success': False, 'error': 'Session not found'}, status=404)

    invited_email = ''
    try:
        invited_email = (s.attendees.first().email if s.attendees.exists() else '').strip().lower()
    except Exception:
        invited_email = ''
    if not invited_email:
        return JsonResponse({'success': False, 'error': 'No invited client on this session'}, status=400)

    inv = SessionInvitation.objects.filter(
        session=s,
        mentor=mentor_profile,
        invited_email=invited_email,
        cancelled_at__isnull=True
    ).order_by('-created_at').first()
    if not inv:
        return JsonResponse({'success': False, 'error': 'No invitation found for this session'}, status=404)

    if inv.is_expired():
        return JsonResponse({'success': False, 'error': 'Invitation expired. Please send a new invitation.'}, status=400)

    # Once per day (including the day it was sent)
    try:
        if timezone.localdate(inv.last_sent_at) == timezone.localdate():
            return JsonResponse({'success': False, 'error': 'You can only send one reminder per day.'}, status=400)
    except Exception:
        return JsonResponse({'success': False, 'error': 'You can only send one reminder per day.'}, status=400)

    # Ensure invitation_token exists for unverified users (so landing can route correctly)
    try:
        invited_user = CustomUser.objects.filter(email=invited_email).first()
        if invited_user and not invited_user.is_email_verified:
            try:
                user_profile = invited_user.user_profile
                rel = MentorClientRelationship.objects.filter(mentor=mentor_profile, client=user_profile).first()
                if rel and not rel.invitation_token:
                    rel.invitation_token = get_random_string(64)
                    rel.save(update_fields=['invitation_token'])
            except Exception:
                pass
    except Exception:
        pass

    site_domain = EmailService.get_site_domain()
    from django.urls import reverse
    action_url = f"{site_domain}{reverse('accounts:session_invitation_link', kwargs={'token': inv.token})}"

    # Format datetimes in invitee timezone for email display
    session_date_local = None
    session_start_time_local = None
    session_end_time_local = None
    invitee_timezone = None
    try:
        tz_name = None
        invited_user_obj = None
        try:
            invited_user_obj = CustomUser.objects.filter(email=invited_email).first()
        except Exception:
            invited_user_obj = None
        if invited_user_obj and hasattr(invited_user_obj, 'profile') and invited_user_obj.profile:
            tz_name = (getattr(invited_user_obj.profile, 'selected_timezone', None) or getattr(invited_user_obj.profile, 'detected_timezone', None) or getattr(invited_user_obj.profile, 'time_zone', None))
        tz_name = (tz_name or 'UTC')
        invitee_timezone = tz_name
        try:
            from zoneinfo import ZoneInfo
            tzinfo = ZoneInfo(str(tz_name))
        except Exception:
            tzinfo = dt_timezone.utc
        if s.start_datetime and s.end_datetime:
            start_local = s.start_datetime.astimezone(tzinfo)
            end_local = s.end_datetime.astimezone(tzinfo)
            session_date_local = start_local.strftime('%a, %b %d, %Y')
            session_start_time_local = start_local.strftime('%I:%M %p').lstrip('0')
            session_end_time_local = end_local.strftime('%I:%M %p').lstrip('0')
    except Exception:
        pass

    mentor_profile_url = None
    try:
        from django.urls import reverse
        mentor_profile_url = f"{site_domain}{reverse('web:mentor_profile_detail', kwargs={'user_id': mentor_profile.user_id})}"
    except Exception:
        mentor_profile_url = None

    try:
        inv.last_sent_at = timezone.now()
        inv.save(update_fields=['last_sent_at'])
        EmailService.send_email(
            subject=f"Session reminder from {mentor_profile.first_name} {mentor_profile.last_name}",
            recipient_email=invited_email,
            template_name='session_invitation',
            context={
                'mentor_name': f"{mentor_profile.first_name} {mentor_profile.last_name}",
                'mentor_profile_url': mentor_profile_url,
                'action_url': action_url,
                'session_start': s.start_datetime,
                'session_end': s.end_datetime,
                'session_date_local': session_date_local,
                'session_start_time_local': session_start_time_local,
                'session_end_time_local': session_end_time_local,
                'invitee_timezone': invitee_timezone,
                'session_price': getattr(s, 'session_price', None),
            }
        )
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Failed to send reminder: {e}'}, status=500)

    return JsonResponse({
        'success': True,
        'message': 'Reminder sent.',
        'last_sent_at': inv.last_sent_at.isoformat() if inv.last_sent_at else None,
        'can_remind': False,
    })


@login_required
def session_detail(request, session_id: int):
    """Mentor-only dedicated session detail page."""
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing mentor dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'mentor':
        return redirect('general:index')

    mentor_profile = request.user.mentor_profile
    from general.models import Session

    s = mentor_profile.sessions.filter(id=session_id).first()
    if not s:
        messages.error(request, 'Session not found.')
        return redirect('general:dashboard_mentor:my_sessions')

    client_email = None
    try:
        client_email = s.attendees.first().email if s.attendees.exists() else None
    except Exception:
        client_email = None

    # Render times in mentor timezone (best effort)
    tz_name = mentor_profile.selected_timezone or mentor_profile.detected_timezone or mentor_profile.time_zone or 'UTC'
    start_local = None
    end_local = None
    try:
        from zoneinfo import ZoneInfo
        tzinfo = ZoneInfo(str(tz_name))
        start_local = s.start_datetime.astimezone(tzinfo) if s.start_datetime else None
        end_local = s.end_datetime.astimezone(tzinfo) if s.end_datetime else None
    except Exception:
        start_local = s.start_datetime
        end_local = s.end_datetime

    return render(request, 'dashboard_mentor/session_detail.html', {
        'debug': settings.DEBUG,
        'session': s,
        'client_email': client_email,
        'mentor_timezone': tz_name,
        'start_local': start_local,
        'end_local': end_local,
    })


@login_required
def clients_list(request):
    """Display list of all clients for the logged-in mentor"""
    if not hasattr(request.user, 'profile'):
        return redirect('general:index')
    
    # Prevent admin users from accessing mentor dashboard
    if request.user.profile.role == 'admin':
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('accounts:login')
    
    if request.user.profile.role != 'mentor':
        return redirect('general:index')
    
    mentor_profile = request.user.mentor_profile
    relationships = MentorClientRelationship.objects.filter(mentor=mentor_profile).select_related('client', 'client__user').order_by('-created_at')
    
    return render(request, 'dashboard_mentor/clients.html', {
        'relationships': relationships,
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


# ============================================================================
# BLOG POST VIEWS FOR MENTORS
# ============================================================================

@login_required
def blog_list(request):
    """List all blog posts for the current mentor"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        messages.error(request, "Only mentors can access this page.")
        return redirect('general:index')
    
    # Get only posts by this mentor
    posts = BlogPost.objects.filter(author=request.user).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) |
            Q(excerpt__icontains=search_query) |
            Q(content__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter in ['draft', 'published']:
        posts = posts.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(posts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'dashboard_mentor/blog_list.html', {
        'page_obj': page_obj,
        'posts': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'predefined_categories': PREDEFINED_CATEGORIES,
    })


@login_required
def blog_create(request):
    """Create a new blog post"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        messages.error(request, "Only mentors can create blog posts.")
        return redirect('general:index')
    
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, 'Blog post created successfully!')
            return redirect('general:dashboard_mentor:blog_list')
    else:
        form = BlogPostForm()
    
    return render(request, 'dashboard_mentor/blog_form.html', {
        'form': form,
        'action': 'Create',
        'predefined_categories': PREDEFINED_CATEGORIES,
    })


@login_required
def blog_edit(request, post_id):
    """Edit an existing blog post"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        messages.error(request, "Only mentors can edit blog posts.")
        return redirect('general:index')
    
    post = get_object_or_404(BlogPost, id=post_id, author=request.user)
    
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Blog post updated successfully!')
            return redirect('general:dashboard_mentor:blog_list')
    else:
        form = BlogPostForm(instance=post)
    
    return render(request, 'dashboard_mentor/blog_form.html', {
        'form': form,
        'post': post,
        'action': 'Edit',
        'predefined_categories': PREDEFINED_CATEGORIES,
    })


@login_required
@require_POST
def blog_delete(request, post_id):
    """Delete a blog post"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        return JsonResponse({'success': False, 'error': 'Only mentors can delete blog posts'}, status=403)
    
    post = get_object_or_404(BlogPost, id=post_id, author=request.user)
    
    # Delete cover image if it exists
    if post.cover_image:
        post.cover_image.delete(save=False)
    
    post.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Blog post deleted successfully.'})
    
    messages.success(request, 'Blog post deleted successfully.')
    return redirect('general:dashboard_mentor:blog_list')
