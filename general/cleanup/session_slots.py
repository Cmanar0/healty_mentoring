"""
Session slots cleanup utility.

This module provides cleanup functions for removing draft sessions
from the database.

CLEANUP RULE:
Delete a session ONLY if ALL conditions are met:
- status == "draft"
- end_datetime < now (timezone-aware, UTC)
"""

from django.utils import timezone
from general.models import Session
from datetime import timezone as dt_timezone


# Configuration: intended execution frequency (in minutes)
CLEANUP_INTERVAL_MINUTES = 2


def cleanup_draft_sessions():
    """
    Remove expired draft sessions from the database.
    
    This function:
    - Finds all sessions with status == "draft" and end_datetime < now
    - Deletes them from the database
    - Is idempotent (safe to run multiple times)
    - Uses UTC timezone for comparison
    
    Returns:
        dict: {
            'sessions_deleted': int
        }
    """
    now = timezone.now()
    
    # Ensure now is in UTC for comparison
    now_utc = now if now.tzinfo else timezone.now()
    if now_utc.tzinfo != dt_timezone.utc:
        now_utc = now_utc.astimezone(dt_timezone.utc)
    
    # Find all draft sessions that have ended (end_datetime < now)
    draft_sessions = Session.objects.filter(
        status='draft',
        end_datetime__lt=now_utc
    )
    sessions_deleted = draft_sessions.count()
    
    # Delete expired draft sessions
    draft_sessions.delete()
    
    return {
        'sessions_deleted': sessions_deleted
    }

