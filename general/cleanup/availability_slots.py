"""
Availability slots cleanup utility.

This module provides cleanup functions for removing expired one-time availability slots
from MentorProfile records.

CLEANUP RULE:
Delete a slot ONLY if ALL conditions are met:
- type == "availability_slot"
- end < now (timezone-aware, UTC)
"""

from django.utils import timezone
from accounts.models import MentorProfile
from datetime import datetime, timezone as dt_timezone


def cleanup_expired_availability_slots():
    """
    Remove expired one-time availability slots from all MentorProfile records.
    
    This function:
    - Iterates over all MentorProfile records
    - Removes only expired one-time availability slots that meet ALL criteria:
      * type == "availability_slot"
      * end < now (timezone-aware, UTC)
    - Saves MentorProfile only if changes occurred
    - Is idempotent (safe to run multiple times)
    
    Returns:
        dict: {
            'profiles_checked': int,
            'profiles_updated': int,
            'slots_removed': int
        }
    """
    now = timezone.now()
    profiles_checked = 0
    profiles_updated = 0
    slots_removed = 0
    
    # Iterate over all mentor profiles
    for mentor_profile in MentorProfile.objects.all():
        profiles_checked += 1
        updated = False
        
        # Get one-time slots (use new field name with fallback to old)
        try:
            one_time_slots = list(mentor_profile.one_time_slots or [])
        except AttributeError:
            one_time_slots = list(mentor_profile.availability_slots or [])
        
        if not one_time_slots:
            continue
        
        # Filter out expired availability slots
        filtered_slots = []
        for slot in one_time_slots:
            # Skip if not a dict
            if not isinstance(slot, dict):
                filtered_slots.append(slot)
                continue
            
            # Apply strict cleanup rule: ALL conditions must be met
            slot_type = slot.get('type', '')
            end_str = slot.get('end', '')
            
            # Check if this slot should be deleted
            should_delete = (
                slot_type == 'availability_slot' and
                bool(end_str)
            )
            
            if should_delete:
                try:
                    # Parse end datetime (handle various formats)
                    end_str_normalized = end_str.replace('Z', '+00:00')
                    end_dt = datetime.fromisoformat(end_str_normalized)
                    
                    # Ensure timezone-aware (should be UTC)
                    if end_dt.tzinfo is None:
                        end_dt = timezone.make_aware(end_dt, timezone=dt_timezone.utc)
                    else:
                        # Convert to UTC for comparison
                        end_dt = end_dt.astimezone(dt_timezone.utc)
                    
                    # timezone.now() returns UTC-aware datetime by default in Django
                    # Ensure both are in UTC for comparison
                    now_utc = now if now.tzinfo else timezone.now()
                    if now_utc.tzinfo != dt_timezone.utc:
                        now_utc = now_utc.astimezone(dt_timezone.utc)
                    
                    # Only delete if end < now (both in UTC)
                    if end_dt < now_utc:
                        slots_removed += 1
                        updated = True
                        continue  # Skip adding this slot to filtered list
                except (ValueError, TypeError, AttributeError):
                    # If parsing fails, keep the slot (safer)
                    pass
            
            # Keep this slot
            filtered_slots.append(slot)
        
        # Save only if changes occurred
        if updated:
            try:
                mentor_profile.one_time_slots = filtered_slots
                mentor_profile.save(update_fields=['one_time_slots'])
                profiles_updated += 1
            except AttributeError:
                # Fallback to old field name if new one doesn't exist
                try:
                    mentor_profile.availability_slots = filtered_slots
                    mentor_profile.save(update_fields=['availability_slots'])
                    profiles_updated += 1
                except Exception:
                    # Log error but continue processing other profiles
                    pass
    
    return {
        'profiles_checked': profiles_checked,
        'profiles_updated': profiles_updated,
        'slots_removed': slots_removed
    }

