# Generated manually

from django.db import migrations


def add_booked_fields_to_existing_slots(apps, schema_editor):
    """Add booked field to one_time_slots and booked_dates to recurring_slots"""
    MentorProfile = apps.get_model('accounts', 'MentorProfile')
    
    for profile in MentorProfile.objects.all():
        updated_one_time = False
        updated_recurring = False
        
        # Update one_time_slots: add booked: false if not present
        if profile.one_time_slots:
            updated_slots = []
            for slot in profile.one_time_slots:
                if isinstance(slot, dict):
                    if 'booked' not in slot:
                        slot['booked'] = False
                    updated_slots.append(slot)
                else:
                    updated_slots.append(slot)
            if updated_slots != profile.one_time_slots:
                profile.one_time_slots = updated_slots
                updated_one_time = True
        
        # Update recurring_slots: add booked_dates: [] if not present
        if profile.recurring_slots:
            updated_slots = []
            for slot in profile.recurring_slots:
                if isinstance(slot, dict):
                    if 'booked_dates' not in slot:
                        slot['booked_dates'] = []
                    updated_slots.append(slot)
                else:
                    updated_slots.append(slot)
            if updated_slots != profile.recurring_slots:
                profile.recurring_slots = updated_slots
                updated_recurring = True
        
        # Save only if changes were made
        if updated_one_time or updated_recurring:
            profile.save()


def reverse_migration(apps, schema_editor):
    """Reverse: remove booked and booked_dates fields (optional - can be left as is)"""
    # We don't need to remove these fields as they're optional JSON fields
    # Leaving them won't break anything
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0032_rename_availability_fields'),
    ]

    operations = [
        migrations.RunPython(add_booked_fields_to_existing_slots, reverse_migration),
    ]

