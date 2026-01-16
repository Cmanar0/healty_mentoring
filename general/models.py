from django.db import models
from django.utils import timezone
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from django.core.validators import FileExtensionValidator
import uuid
import os
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
    
    • expired
      - Session was in 'invited' status and its end_datetime has passed
      - Automatically set by cleanup process when invited session's end time is in the past
      - Terminal state (no transitions out)
      - Cannot be modified, moved, or deleted
      - Historical record preserved for reference
    
    • completed
      - Session was in 'confirmed' status and its end_datetime has passed
      - Automatically set by cleanup process when confirmed session's end time is in the past
      - Terminal state (no transitions out)
      - Cannot be modified, moved, or deleted
      - Can be refunded (transitions to 'refunded' status)
      - Historical record preserved for reference
    
    • refunded
      - Session was 'completed' and has been refunded
      - Set when mentor refunds a completed session
      - Terminal state (no transitions out)
      - Cannot be modified, moved, or deleted
      - Historical record preserved for reference
    
    
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
    
    6. invited → expired
       - Trigger: Cleanup process detects invited session with end_datetime in the past
       - Action: Session status automatically changed to expired
       - Note: This is a system-initiated transition, not user-initiated
    
    7. confirmed → completed
       - Trigger: Cleanup process detects confirmed session with end_datetime in the past
       - Action: Session status automatically changed to completed
       - Note: This is a system-initiated transition, not user-initiated
    
    8. completed → refunded
       - Trigger: Mentor refunds a completed session
       - Action: Session status changed to refunded
       - Note: Only completed sessions can be refunded
    
    Invalid transitions (not allowed):
    - draft → confirmed (must go through invited first)
    - confirmed → draft (cannot revert to draft)
    - cancelled → any state (cancelled is terminal)
    - expired → any state (expired is terminal)
    - completed → any state except refunded (completed is terminal)
    - refunded → any state (refunded is terminal)
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
    
    • No automatic cancellation
      - Sessions are not cancelled by system processes
      - Only explicit user action (client decline) cancels sessions
      - Note: Automatic expiration (invited → expired) and completion (confirmed → completed)
        are implemented via cleanup processes, but these are status transitions, not cancellations
    
    • No auto-confirmation
      - Sessions are not automatically confirmed
      - Client must explicitly confirm each invitation or change
    
    • Sessions remain pending until user action
      - A session with previous_data populated will remain in that state
        indefinitely until the client takes action
      - No automatic cleanup of pending changes
    
    AUTOMATIC STATUS TRANSITIONS (CLEANUP PROCESSES)
    -------------------------------------------------
    
    The following automatic transitions are implemented via cleanup processes:
    
    • invited → expired
      - Triggered by cleanup process when invited session's end_datetime < now (UTC)
      - Runs periodically (via cron) and synchronously before calendar data fetch
      - Preserves session as historical record (does not delete)
    
    • confirmed → completed
      - Triggered by cleanup process when confirmed session's end_datetime < now (UTC)
      - Runs periodically (via cron) and synchronously before calendar data fetch
      - Preserves session as historical record (does not delete)
    
    • draft → deleted
      - Triggered by cleanup process when draft session's end_datetime < now (UTC)
      - Only draft sessions are deleted (not terminal state sessions)
      - Runs periodically (via cron) and synchronously before calendar data fetch
    
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
        ('expired', 'Expired'),
        ('completed', 'Completed'),
        ('refunded', 'Refunded'),
    ]
    
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    created_by = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="created_sessions")
    attendees = models.ManyToManyField("accounts.CustomUser", related_name="attended_sessions", blank=True)
    note = models.TextField(blank=True)
    first_lesson_user_note = models.TextField(blank=True, null=True, help_text="Note from user when booking their first session")
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES, default='individual')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    expires_at = models.DateTimeField(blank=True, null=True)
    session_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    client_first_name = models.CharField(max_length=150, blank=True, null=True)
    client_last_name = models.CharField(max_length=150, blank=True, null=True)
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

    def save(self, *args, **kwargs):
        # Track if end_datetime is changing
        end_datetime_changed = False
        old_end_datetime = None
        
        if self.pk:
            # Check if end_datetime has changed by comparing with database
            try:
                old_instance = type(self).objects.get(pk=self.pk)
                old_end_datetime = old_instance.end_datetime
                if old_end_datetime != self.end_datetime:
                    end_datetime_changed = True
            except type(self).DoesNotExist:
                pass
        else:
            # New instance, end_datetime is being set for the first time
            if self.end_datetime:
                end_datetime_changed = True
        
        super().save(*args, **kwargs)
        
        # Update related invitations when end_datetime changes
        if end_datetime_changed and self.end_datetime:
            # Update all non-expired, non-cancelled invitations for this session
            # Only update if the new expiration is in the future
            if self.end_datetime > timezone.now():
                self.invitations.filter(
                    cancelled_at__isnull=True
                ).exclude(
                    expires_at__lt=timezone.now()
                ).update(expires_at=self.end_datetime)

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
            # Set expiration to the session's end_datetime if available
            if self.session and self.session.end_datetime:
                self.expires_at = self.session.end_datetime
            else:
                # Fallback to 7 days if session doesn't have end_datetime (shouldn't happen normally)
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
    TARGET_TYPE_CHOICES = [
        ('all', 'All Users'),
        ('all_users', 'All User Role'),
        ('all_mentors', 'All Mentor Role'),
        ('single', 'Single User'),
    ]
    
    user = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="notifications")
    batch_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True, help_text="Groups notifications created in the same admin action")
    target_type = models.CharField(
        max_length=20,
        choices=TARGET_TYPE_CHOICES,
        default='all',
        db_index=True,
        help_text="Target audience type when notification was created"
    )
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


class Ticket(models.Model):
    """Support ticket model for users and mentors to submit issues"""
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    user = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="tickets")
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to="tickets/", blank=True, null=True, help_text="Optional image attachment (max 5MB)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted', db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Support Ticket"
        verbose_name_plural = "Support Tickets"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"Ticket #{self.id} - {self.title} ({self.get_status_display()})"
    
    @property
    def is_resolved(self):
        """Check if ticket is resolved or closed"""
        return self.status in ['resolved', 'closed']
    
    @property
    def is_unresolved(self):
        """Check if ticket is unresolved"""
        return self.status in ['submitted', 'in_progress']


class TicketComment(models.Model):
    """Comments on support tickets for communication between users/mentors and admins"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="ticket_comments")
    comment = models.TextField()
    image = models.ImageField(upload_to="ticket_comments/", blank=True, null=True, help_text="Optional image attachment (max 5MB)")
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = "Ticket Comment"
        verbose_name_plural = "Ticket Comments"
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['ticket', 'created_at']),
        ]
    
    def __str__(self):
        return f"Comment on Ticket #{self.ticket.id} by {self.user.email}"


def blog_cover_image_upload_to(instance, filename: str) -> str:
    """Upload path for blog post cover images"""
    _, ext = os.path.splitext(filename or "")
    ext = (ext or "").lower()
    if ext and len(ext) > 10:
        ext = ext[:10]
    return f"blog_covers/{uuid.uuid4().hex}{ext}"


class BlogPost(models.Model):
    """Blog post model for mentors and admins"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]
    
    # Basic fields
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True, db_index=True)
    content = models.TextField(help_text="Rich text content of the blog post")
    excerpt = models.TextField(max_length=500, blank=True, help_text="Short excerpt for preview (optional)")
    
    # Author
    author = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="blog_posts",
        help_text="Author of the blog post"
    )
    
    # Cover image
    cover_image = models.ImageField(
        upload_to=blog_cover_image_upload_to,
        blank=True,
        null=True,
        max_length=255,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])],
        help_text="Cover image for the blog post (max 5MB)"
    )
    
    # Cover image placeholder color (if no image)
    cover_color = models.CharField(
        max_length=7,
        default='#10b981',
        help_text="Hex color for cover placeholder (e.g., #10b981)"
    )
    
    # Categories (multiple selection stored as JSON array)
    categories = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of category IDs from predefined categories"
    )
    
    # SEO tags (array of strings for meta keywords)
    seo_tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of SEO tags/keywords for meta tags"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="Draft posts are only visible in management pages, not in public blog"
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True, db_index=True, help_text="Publication date (set when status changes to published)")
    
    class Meta:
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', '-published_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['slug']),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-generate slug from title if not provided
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while BlogPost.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Set published_at when status changes to published
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        elif self.status == 'draft' and self.published_at:
            # Keep published_at even if reverted to draft (for history)
            pass
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    @property
    def is_published(self):
        """Check if post is published"""
        return self.status == 'published'
    
    @property
    def author_name(self):
        """Get author's display name"""
        if hasattr(self.author, 'mentor_profile'):
            profile = self.author.mentor_profile
            return f"{profile.first_name} {profile.last_name}"
        elif hasattr(self.author, 'profile'):
            profile = self.author.profile
            if hasattr(profile, 'first_name') and hasattr(profile, 'last_name'):
                return f"{profile.first_name} {profile.last_name}"
        return self.author.email
    
    @property
    def author_is_mentor(self):
        """Check if author is a mentor (has mentor profile)"""
        return hasattr(self.author, 'mentor_profile')
    
    @property
    def author_is_admin(self):
        """Check if author is an admin"""
        if hasattr(self.author, 'profile'):
            return getattr(self.author.profile, 'role', None) == 'admin'
        return False
