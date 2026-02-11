# Ensure every session that has created_by has that mentor in session.mentors (M2M).

from django.db import migrations


def backfill_mentors(apps, schema_editor):
    Session = apps.get_model('general', 'Session')
    MentorProfile = apps.get_model('accounts', 'MentorProfile')
    for session in Session.objects.select_related('created_by').all():
        if session.created_by_id is None:
            continue
        mentor_profile = MentorProfile.objects.filter(user_id=session.created_by_id).first()
        if mentor_profile is None:
            continue
        if session.mentors.filter(pk=mentor_profile.pk).exists():
            continue
        session.mentors.add(mentor_profile)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('general', '0019_make_session_created_by_nullable'),
    ]

    operations = [
        migrations.RunPython(backfill_mentors, noop),
    ]
