"""
Django management command to clean up expired availability slots and draft sessions.

Usage:
    python manage.py cleanup_calendar
"""

from django.core.management.base import BaseCommand
from general.cleanup.availability_slots import cleanup_expired_availability_slots
from general.cleanup.session_slots import cleanup_draft_sessions


class Command(BaseCommand):
    help = 'Remove expired one-time availability slots and draft sessions'

    def handle(self, *args, **options):
        """Execute the cleanup functions."""
        import sys
        import traceback
        from django.utils import timezone
        
        try:
            self.stdout.write(f'[{timezone.now()}] Starting calendar cleanup...')
            
            # Cleanup expired availability slots
            availability_result = cleanup_expired_availability_slots()
            
            # Cleanup draft sessions
            sessions_result = cleanup_draft_sessions()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'[{timezone.now()}] Cleanup completed: '
                    f'{availability_result["profiles_checked"]} profiles checked, '
                    f'{availability_result["profiles_updated"]} profiles updated, '
                    f'{availability_result["slots_removed"]} availability slots removed, '
                    f'{sessions_result["sessions_deleted"]} draft sessions deleted, '
                    f'{sessions_result["sessions_expired"]} sessions expired, '
                    f'{sessions_result["sessions_completed"]} sessions completed, '
                    f'{sessions_result.get("sessions_payout_available", 0)} sessions payout_available'
                )
            )
        except Exception as e:
            error_msg = f'[{timezone.now()}] ERROR in cleanup_calendar: {str(e)}'
            self.stderr.write(error_msg)
            self.stderr.write(traceback.format_exc())
            sys.exit(1)

