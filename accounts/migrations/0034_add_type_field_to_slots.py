# Generated manually

from django.db import migrations


def add_type_field_to_existing_slots(apps, schema_editor):
    """Add type field to existing slots (default to availability_slot)"""
    MentorProfile = apps.get_model('accounts', 'MentorProfile')
    
    for profile in MentorProfile.objects.all():
        updated_one_time = False
        updated_recurring = False
        
        # Update one_time_slots: add type: "availability_slot" if not present
        if profile.one_time_slots:
            updated_slots = []
            for slot in profile.one_time_slots:
                if isinstance(slot, dict):
                    if 'type' not in slot:
                        slot['type'] = 'availability_slot'
                    updated_slots.append(slot)
                else:
                    updated_slots.append(slot)
            if updated_slots != profile.one_time_slots:
                profile.one_time_slots = updated_slots
                updated_one_time = True
        
        # Update recurring_slots: add slot_type: "availability_slot" if not present
        if profile.recurring_slots:
            updated_slots = []
            for slot in profile.recurring_slots:
                if isinstance(slot, dict):
                    if 'slot_type' not in slot:
                        slot['slot_type'] = 'availability_slot'
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
    """Reverse: remove type and slot_type fields (optional - can be left as is)"""
    # We don't need to remove these fields as they're optional JSON fields
    # Leaving them won't break anything
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0033_add_booked_fields_to_slots'),
    ]

    operations = [
        migrations.RunPython(add_type_field_to_existing_slots, reverse_migration),
    ]

