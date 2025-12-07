from django.db import models
from django.utils import timezone
import uuid

class Session(models.Model):
    """Session model for mentor sessions"""
    SESSION_TYPES = [
        ('individual', 'Individual'),
        ('group', 'Group'),
        ('workshop', 'Workshop'),
    ]
    
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    created_by = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="created_sessions")
    attendees = models.ManyToManyField("accounts.CustomUser", related_name="attended_sessions", blank=True)
    note = models.TextField(blank=True)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES, default='individual')
    tasks = models.JSONField(default=list, blank=True)  # Array of tasks

    class Meta:
        verbose_name = "Session"
        verbose_name_plural = "Sessions"
        ordering = ['-start_datetime']

    def __str__(self):
        return f"Session on {self.start_datetime.strftime('%Y-%m-%d %H:%M')}"


class Notification(models.Model):
    """Notification model for user notifications"""
    user = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="notifications")
    batch_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True, help_text="Groups notifications created in the same admin action")
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    is_opened = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_opened']),
        ]

    def __str__(self):
        return f"{self.title} - {self.user.email}"
