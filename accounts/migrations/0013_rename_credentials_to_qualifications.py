# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_mentorprofile_categories_and_more'),
        ('dashboard_mentor', '0006_rename_credential_to_qualification'),
    ]

    operations = [
        migrations.RenameField(
            model_name='mentorprofile',
            old_name='credentials',
            new_name='qualifications',
        ),
    ]

