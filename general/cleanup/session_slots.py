"""
Session slots cleanup utility.

This module provides cleanup functions for managing expired sessions
in the database.

CLEANUP RULES:
1. Draft sessions: Delete if end_datetime < now (timezone-aware, UTC)
2. Invited sessions: Change status to "expired" if end_datetime < now
3. Confirmed sessions: Change status to "completed" if end_datetime < now
"""

from django.utils import timezone
from general.models import Session
from datetime import timezone as dt_timezone


# Configuration: intended execution frequency (in minutes)
CLEANUP_INTERVAL_MINUTES = 2


def cleanup_draft_sessions():
    """
    Clean up expired sessions based on their status.
    
    This function:
    - Deletes draft sessions with end_datetime < now
    - Changes invited sessions to "expired" if end_datetime < now
    - Changes confirmed sessions to "completed" if end_datetime < now
    - Is idempotent (safe to run multiple times)
    - Uses UTC timezone for comparison
    
    Returns:
        dict: {
            'sessions_deleted': int,
            'sessions_expired': int,
            'sessions_completed': int
        }
    """
    now = timezone.now()
    
    # Ensure now is in UTC for comparison
    now_utc = now if now.tzinfo else timezone.now()
    if now_utc.tzinfo != dt_timezone.utc:
        now_utc = now_utc.astimezone(dt_timezone.utc)
    
    # Delete expired draft sessions ONLY
    # IMPORTANT: Never delete terminal state sessions (completed, refunded, expired)
    # These are historical records that must be preserved
    draft_sessions = Session.objects.filter(
        status='draft',
        end_datetime__lt=now_utc
    ).exclude(
        status__in=['completed', 'refunded', 'expired']  # Extra protection (shouldn't be needed, but safety first)
    )
    sessions_deleted = draft_sessions.count()
    draft_sessions.delete()
    
    # Change invited sessions to expired
    invited_sessions = Session.objects.filter(
        status='invited',
        end_datetime__lt=now_utc
    )
    sessions_expired = invited_sessions.count()
    invited_sessions.update(status='expired')
    
    # Change confirmed sessions to completed
    confirmed_sessions = Session.objects.filter(
        status='confirmed',
        end_datetime__lt=now_utc
    )
    sessions_completed = confirmed_sessions.count()
    confirmed_sessions.update(status='completed')
    
    return {
        'sessions_deleted': sessions_deleted,
        'sessions_expired': sessions_expired,
        'sessions_completed': sessions_completed
    }

