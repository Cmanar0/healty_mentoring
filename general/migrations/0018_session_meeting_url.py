# Generated migration for Session.meeting_url

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('general', '0017_review_reviewreply'),
    ]

    operations = [
        migrations.AddField(
            model_name='session',
            name='meeting_url',
            field=models.URLField(
                blank=True,
                help_text='Online meeting link created when the session is confirmed (client confirms or books).',
                max_length=512,
                null=True
            ),
        ),
    ]
