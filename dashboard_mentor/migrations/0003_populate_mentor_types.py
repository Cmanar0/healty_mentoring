from django.db import migrations

def populate_mentor_types(apps, schema_editor):
    MentorType = apps.get_model('dashboard_mentor', 'MentorType')
    
    # Predefined mentor types
    predefined_types = [
        'Life Coach',
        'Career Coach',
        'Business Coach',
        'Health Coach',
        'Wellness Coach',
        'Fitness Coach',
        'Nutrition Coach',
        'Relationship Coach',
        'Executive Coach',
        'Performance Coach',
    ]
    
    for type_name in predefined_types:
        MentorType.objects.get_or_create(
            name=type_name,
            defaults={'is_custom': False}
        )

def reverse_populate_mentor_types(apps, schema_editor):
    MentorType = apps.get_model('dashboard_mentor', 'MentorType')
    MentorType.objects.filter(is_custom=False).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('dashboard_mentor', '0002_mentortype'),
    ]

    operations = [
        migrations.RunPython(populate_mentor_types, reverse_populate_mentor_types),
    ]

