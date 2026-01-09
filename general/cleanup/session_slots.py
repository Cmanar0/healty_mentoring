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
    import logging
    logger = logging.getLogger(__name__)
    
    now = timezone.now()
    
    # Ensure now is in UTC for comparison
    now_utc = now if now.tzinfo else timezone.now()
    if now_utc.tzinfo != dt_timezone.utc:
        now_utc = now_utc.astimezone(dt_timezone.utc)
    
    logger.info(f'[cleanup_draft_sessions] Starting cleanup at {now_utc}')
    
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
    if sessions_deleted > 0:
        logger.info(f'[cleanup_draft_sessions] Deleting {sessions_deleted} expired draft sessions')
        draft_sessions.delete()
    
    # Change invited sessions to expired
    invited_sessions = Session.objects.filter(
        status='invited',
        end_datetime__lt=now_utc
    )
    sessions_expired = invited_sessions.count()
    if sessions_expired > 0:
        logger.info(f'[cleanup_draft_sessions] Expiring {sessions_expired} invited sessions')
        invited_sessions.update(status='expired')
    
    # Change confirmed sessions to completed
    confirmed_sessions = Session.objects.filter(
        status='confirmed',
        end_datetime__lt=now_utc
    )
    sessions_completed = confirmed_sessions.count()
    if sessions_completed > 0:
        logger.info(f'[cleanup_draft_sessions] Completing {sessions_completed} confirmed sessions')
        # Log some example sessions for debugging
        example_ids = list(confirmed_sessions.values_list('id', 'end_datetime')[:5])
        logger.info(f'[cleanup_draft_sessions] Example sessions to complete: {example_ids}')
        confirmed_sessions.update(status='completed')
        logger.info(f'[cleanup_draft_sessions] Successfully updated {sessions_completed} sessions to completed')
    else:
        # Log if no sessions found - helps debug if query is working
        total_confirmed = Session.objects.filter(status='confirmed').count()
        logger.info(f'[cleanup_draft_sessions] No expired confirmed sessions found. Total confirmed sessions: {total_confirmed}')
        if total_confirmed > 0:
            # Show some example confirmed sessions and their end times
            examples = Session.objects.filter(status='confirmed').values_list('id', 'end_datetime')[:5]
            logger.info(f'[cleanup_draft_sessions] Example confirmed sessions: {examples}')
    
    return {
        'sessions_deleted': sessions_deleted,
        'sessions_expired': sessions_expired,
        'sessions_completed': sessions_completed
    }

