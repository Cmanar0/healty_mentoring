from django.db import models
from django.utils import timezone


class ProjectTemplate(models.Model):
    """Template model for project types (e.g., Mindset, Trading, Weight Loss, Business Plan)"""
    CATEGORY_CHOICES = [
        ('health', 'Health & Wellness'),
        ('business', 'Business & Career'),
        ('personal', 'Personal Development'),
        ('finance', 'Finance & Trading'),
        ('academic', 'Academic'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100, unique=True, help_text="Template name (e.g., 'Mindset', 'Trading', 'Weight Loss')")
    description = models.TextField(blank=True, help_text="Description of what this template is for")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other', help_text="Category for grouping templates")
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class (e.g., 'fa-brain', 'fa-chart-line')")
    color = models.CharField(max_length=7, default='#10b981', help_text="Hex color for template (e.g., #10b981)")
    image = models.ImageField(upload_to='project_templates/', blank=True, null=True, help_text="Template image/icon")
    is_active = models.BooleanField(default=True, help_text="Whether this template is available for selection")
    order = models.IntegerField(default=0, help_text="Display order (lower numbers appear first)")
    
    # Template structure/metadata (for future extensibility)
    template_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="Optional: Custom fields structure for this template type"
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Project Template"
        verbose_name_plural = "Project Templates"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Project(models.Model):
    """Project model for users"""
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, help_text="Project description")
    template = models.ForeignKey(
        ProjectTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        help_text="Project template (e.g., Mindset, Trading, Weight Loss)"
    )
    project_owner = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE, related_name="owned_projects", null=True, blank=True)
    supervised_by = models.ForeignKey("accounts.MentorProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="supervised_projects")
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        ordering = ['-created_at', 'title']

    def __str__(self):
        return self.title
