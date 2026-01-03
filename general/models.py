from django.db import models
from django.utils import timezone
from django.conf import settings
from django.utils.crypto import get_random_string
import uuid
from datetime import timedelta

class Session(models.Model):
    """
    Session model for mentor sessions.
    
    ============================================================================
    SESSION STATE MACHINE AND LIFECYCLE DOCUMENTATION
    ============================================================================
    
    SESSION STATUS DEFINITIONS
    ---------------------------
    
    • draft
      - Session exists only in mentor calendar
      - No client is notified
      - Changes are ignored completely by the change-tracking system
      - Mentor can freely modify without triggering confirmation workflow
    
    • invited
      - Session has been sent to client
      - Client has not yet confirmed
      - May represent:
        * A new invitation (first time sent to client)
        * A changed session awaiting confirmation (mentor modified after initial invitation)
      - Client must take action: confirm or decline
    
    • confirmed
      - Client has accepted the session
      - Session is finalized unless changed again
      - If mentor changes a confirmed session, it transitions back to 'invited'
        and requires client re-confirmation
    
    • cancelled
      - Session was explicitly declined by client
      - Terminal state (no transitions out)
      - Once cancelled, session cannot be reactivated
    
    
    ALLOWED STATUS TRANSITIONS
    ---------------------------
    
    The following transitions are the ONLY valid state changes:
    
    1. draft → invited
       - Trigger: Mentor sends invitation
       - Action: Client receives notification and must respond
    
    2. invited → confirmed
       - Trigger: Client confirms invitation
       - Action: Session is finalized and scheduled
    
    3. confirmed → invited
       - Trigger: Mentor changes a confirmed session
       - Action: Client must re-confirm the changes
       - Note: This creates a pending change (previous_data is populated)
    
    4. invited → cancelled
       - Trigger: Client declines invitation or change
       - Action: Session is permanently cancelled
    
    5. confirmed → cancelled
       - Trigger: Client declines after a change to a confirmed session
       - Action: Session is permanently cancelled
    
    Invalid transitions (not allowed):
    - draft → confirmed (must go through invited first)
    - confirmed → draft (cannot revert to draft)
    - cancelled → any state (cancelled is terminal)
    - draft → cancelled (draft sessions are not sent to clients)
    
    
    PENDING CHANGE DEFINITION (CRITICAL)
    ------------------------------------
    
    A session is considered "pending change" if and only if:
    
    • previous_data IS NOT NULL
    
    When a session has a pending change:
    
    • Client must confirm or decline the change
    • Session must appear on the client confirmation page
    • The current session data represents the proposed changes
    • The previous_data field contains the complete original snapshot
    
    previous_data must be cleared (set to NULL) only when:
    
    • Client confirms the change
      - Session status may change (e.g., confirmed → invited → confirmed)
      - previous_data is cleared
      - changes_requested_by is cleared
    
    • Session is cancelled
      - Session status becomes 'cancelled'
      - previous_data is cleared
      - changes_requested_by is cleared
    
    While pending:
    
    • previous_data must remain populated
    • changes_requested_by must remain populated
    • Session cannot be modified further until pending change is resolved
    
    
    CHANGE ORIGIN TRACKING
    ----------------------
    
    The changes_requested_by field indicates who initiated the pending change.
    
    Allowed values:
    
    • "mentor"
      - Mentor modified the session
      - Currently the only value in use
      - Client must confirm or decline mentor's changes
    
    • "client"
      - Client proposed a change (future functionality)
      - Reserved for future client-initiated change requests
      - Mentor would need to confirm client's proposed changes
    
    • NULL
      - No pending change exists
      - Session is in normal state (no confirmation required)
    
    For now:
    
    • Only "mentor" is used in practice
    • "client" exists to support future functionality
    • This field works in conjunction with previous_data to track pending
      changes through the confirmation workflow
    
    
    EXPLICIT NON-GOALS
    ------------------
    
    The following behaviors are explicitly NOT implemented:
    
    • No automatic timeouts
      - Sessions do not expire or cancel automatically
      - No background jobs check for stale pending changes
    
    • No background cancellation
      - Sessions are not cancelled by system processes
      - Only explicit user action (client decline) cancels sessions
    
    • No auto-confirmation
      - Sessions are not automatically confirmed
      - Client must explicitly confirm each invitation or change
    
    • Sessions remain pending until user action
      - A session with previous_data populated will remain in that state
        indefinitely until the client takes action
      - No automatic cleanup or expiration
    
    ============================================================================
    """
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

    # ============================================================================
    # PENDING SESSION CHANGES SUPPORT
    # ============================================================================
    # These fields support the session-change confirmation workflow where
    # mentors can modify sessions that are already invited or confirmed.
    #
    # previous_data:
    #   - Stores the FULL original session snapshot before a change is made
    #   - The snapshot is a complete representation of the session at the moment
    #     before the change, with JSON structure mirroring session model fields
    #     exactly (same keys as current fields)
    #   - This field is only populated while waiting for client confirmation
    #   - Once the client confirms the change, this field will be cleared (NULL)
    #   - If the client declines, the session will be canceled
    #   - NULL means no pending change exists
    #
    # changes_requested_by:
    #   - Indicates who initiated the pending change: "mentor" or "client"
    #   - For now, only "mentor" will be used (mentor-initiated changes)
    #   - "client" is reserved for future functionality (client-initiated changes)
    #   - NULL means no pending change exists
    #   - This field works in conjunction with previous_data to track pending
    #     changes through the confirmation workflow
    # ============================================================================
    previous_data = models.JSONField(
        blank=True,
        null=True,
        help_text="Full original snapshot of session data before changes. JSON structure mirrors current session fields exactly. Populated while waiting for client confirmation, cleared on confirmation or cancellation."
    )
    changes_requested_by = models.CharField(
        max_length=20,
        choices=[
            ('mentor', 'Mentor'),
            ('client', 'Client'),
        ],
        blank=True,
        null=True,
        help_text="Indicates who requested the pending changes: mentor or client. NULL means no pending change exists."
    )
    # New fields for session change tracking
    original_data = models.JSONField(
        blank=True,
        null=True,
        help_text="Original session data snapshot when mentor saves changes. Stores full session state before changes. Cleared when client confirms or declines."
    )
    changed_by = models.CharField(
        max_length=20,
        choices=[
            ('mentor', 'Mentor'),
            ('client', 'Client'),
        ],
        blank=True,
        null=True,
        help_text="Indicates who initiated the changes: mentor or client. Set to 'mentor' when mentor saves changes, cleared when client confirms or declines."
    )

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
