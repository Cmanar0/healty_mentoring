from django.db import models
from django.utils import timezone
from django.conf import settings
from django.utils.crypto import get_random_string
import uuid
from datetime import timedelta

class Session(models.Model):
    """Session model for mentor sessions"""
    SESSION_TYPES = [
        ('individual', 'Individual'),
        ('group', 'Group'),
        ('workshop', 'Workshop'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('invited', 'Invited'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    created_by = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="created_sessions")
    attendees = models.ManyToManyField("accounts.CustomUser", related_name="attended_sessions", blank=True)
    note = models.TextField(blank=True)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES, default='individual')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    expires_at = models.DateTimeField(blank=True, null=True)
    session_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    tasks = models.JSONField(default=list, blank=True)  # Array of tasks

    class Meta:
        verbose_name = "Session"
        verbose_name_plural = "Sessions"
        ordering = ['-start_datetime']

    def __str__(self):
        return f"Session on {self.start_datetime.strftime('%Y-%m-%d %H:%M')}"


class SessionInvitation(models.Model):
    """
    Tokenized invitation for a user to confirm a Session.

    - For existing verified users: email links directly to the confirm page (auth required).
    - For new/unverified users: email links to complete-invitation, then redirects to confirm page.
    """
    token = models.CharField(max_length=64, unique=True, db_index=True, editable=False)
    session = models.ForeignKey("general.Session", on_delete=models.CASCADE, related_name="invitations")
    mentor = models.ForeignKey("accounts.MentorProfile", on_delete=models.CASCADE, related_name="session_invitations")
    invited_email = models.EmailField()
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="session_invitations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(blank=True, null=True)
    accepted_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["invited_email"]),
            models.Index(fields=["expires_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = get_random_string(64)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        if not self.last_sent_at:
            self.last_sent_at = timezone.now()
        super().save(*args, **kwargs)

    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"SessionInvitation({self.invited_email} -> session {self.session_id})"


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
