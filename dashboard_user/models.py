from django.db import models

class Project(models.Model):
    """Project model for users"""
    PROJECT_TYPES = [
        ('personal', 'Personal'),
        ('professional', 'Professional'),
        ('academic', 'Academic'),
    ]
    
    title = models.CharField(max_length=200)
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPES, default='personal')
    project_owner = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE, related_name="owned_projects", null=True, blank=True)
    supervised_by = models.ForeignKey("accounts.MentorProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="supervised_projects")

    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        ordering = ['title']

    def __str__(self):
        return self.title
