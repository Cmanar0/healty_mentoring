from django.db import models

class MentorType(models.Model):
    """Model for mentor types that can be selected or created by mentors"""
    name = models.CharField(max_length=100, unique=True)
    is_custom = models.BooleanField(default=False, help_text="True if created by a mentor, False if predefined")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Mentor Type"
        verbose_name_plural = "Mentor Types"
        ordering = ['-is_custom', 'name']
    
    def __str__(self):
        return self.name

class Credential(models.Model):
    """Credentials model for mentors"""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Credential"
        verbose_name_plural = "Credentials"
        ordering = ['title']

    def __str__(self):
        return self.title

class Tag(models.Model):
    """Tags for filtering mentors"""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ['name']

    def __str__(self):
        return self.name
