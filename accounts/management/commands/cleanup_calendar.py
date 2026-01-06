"""
Django management command to clean up expired availability slots.

Usage:
    python manage.py cleanup_calendar
"""

from django.core.management.base import BaseCommand
from general.cleanup.availability_slots import cleanup_expired_availability_slots


class Command(BaseCommand):
    help = 'Remove expired one-time availability slots from MentorProfile records'

    def handle(self, *args, **options):
        """Execute the cleanup function."""
        self.stdout.write('Starting calendar cleanup...')
        
        result = cleanup_expired_availability_slots()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Cleanup completed: '
                f'{result["profiles_checked"]} profiles checked, '
                f'{result["profiles_updated"]} profiles updated, '
                f'{result["slots_removed"]} slots removed'
            )
        )

