from django.db import models

class Credential(models.Model):
    """Credentials model for mentors"""
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)
    description = models.TextField(max_length=450, blank=True)

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
