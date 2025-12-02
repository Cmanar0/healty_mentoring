# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard_mentor', '0005_credential_subtitle_alter_credential_description'),
        ('accounts', '0012_mentorprofile_categories_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Credential',
            new_name='Qualification',
        ),
    ]

