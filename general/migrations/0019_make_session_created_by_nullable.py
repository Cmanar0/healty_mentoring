# Session: created_by is deprecated; use session.mentors + session.attendees only.
# Making created_by nullable so we can stop setting it and eventually remove it.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('general', '0018_session_meeting_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='session',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='created_sessions',
                to='accounts.CustomUser',
            ),
        ),
    ]
