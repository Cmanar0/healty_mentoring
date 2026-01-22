from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ProjectTemplate, Questionnaire


@receiver(post_save, sender=ProjectTemplate)
def create_template_questionnaire(sender, instance, created, **kwargs):
    """Automatically create a questionnaire when a template is created"""
    if created:
        Questionnaire.objects.get_or_create(template=instance)
