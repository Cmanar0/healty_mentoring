from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError

class Qualification(models.Model):
    """Qualifications model for mentors"""
    QUALIFICATION_TYPE_CHOICES = [
        ('degree', 'Degree'),
        ('certificate', 'Certificate'),
        ('license', 'License'),
        ('diploma', 'Diploma'),
        ('award', 'Award'),
        ('training', 'Training'),
        ('workshop', 'Workshop'),
        ('seminar', 'Seminar'),
        ('conference', 'Conference'),
        ('publication', 'Publication'),
        ('research', 'Research'),
        ('experience', 'Experience'),
        ('membership', 'Membership'),
        ('accreditation', 'Accreditation'),
        ('endorsement', 'Endorsement'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)
    description = models.TextField(max_length=450, blank=True)
    type = models.CharField(
        max_length=20,
        choices=QUALIFICATION_TYPE_CHOICES,
        default='certificate',
        help_text="Type of qualification to determine the icon displayed"
    )

    class Meta:
        verbose_name = "Qualification"
        verbose_name_plural = "Qualifications"
        ordering = ['title']

    def __str__(self):
        return self.title
    
    def get_icon(self):
        """Get FontAwesome icon class for this qualification type"""
        from dashboard_mentor.constants import get_qualification_icon
        return get_qualification_icon(self.type)

class MentorProfileQualification(models.Model):
    """Through model for MentorProfile-Qualification relationship with order"""
    mentor_profile = models.ForeignKey("accounts.MentorProfile", on_delete=models.CASCADE)
    qualification = models.ForeignKey("Qualification", on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'qualification__title']
        unique_together = ['mentor_profile', 'qualification']

    def __str__(self):
        return f"{self.mentor_profile} - {self.qualification} (order: {self.order})"

class Tag(models.Model):
    """Tags for filtering mentors"""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ['name']

    def __str__(self):
        return self.name

# MentorAvailability model has been removed - availability is now stored in MentorProfile.availability_slots and MentorProfile.recurring_availability_slots JSON fields


class Guide(models.Model):
    """
    Main mentor onboarding guide item (e.g. "Set up your profile", "Define your Availability").
    Order is used for display; image is uploaded and stored in media/guides/.
    """
    name = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    button_name = models.CharField(max_length=100)
    image = models.ImageField(
        upload_to="guides/",
        blank=True,
        null=True,
        help_text="Upload an image for this guide (shown on the Next step card)."
    )
    youtube_url = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    ai_coins = models.PositiveIntegerField(
        default=50,
        help_text="Amount of AI coins awarded for this guide (editable in admin)."
    )

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Guide"
        verbose_name_plural = "Guides"

    def __str__(self):
        return self.name


class GuideStep(models.Model):
    """
    Subtask under a Guide (no image). Same fields as Guide except image.
    url: page to redirect to when the user clicks the subtask.
    action_id: optional query param (e.g. ?action_id=...) so the target page knows they came from the guide.
    """
    guide = models.ForeignKey(Guide, on_delete=models.CASCADE, related_name="steps")
    name = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    button_name = models.CharField(max_length=100)
    url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Page to redirect to when the user clicks this subtask (e.g. /dashboard/mentor/profile/)."
    )
    action_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional query param added to url (e.g. ?action_id=...) so the target page knows they came from the guide."
    )
    youtube_url = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    ai_coins = models.PositiveIntegerField(
        default=10,
        help_text="Amount of AI coins awarded for this subtask (editable in admin)."
    )

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Guide step"
        verbose_name_plural = "Guide steps"

    def __str__(self):
        return f"{self.guide.name} – {self.name}"


class MentorGuideProgress(models.Model):
    """
    Tracks completion of a guide (main) or a guide step (subtask) by a mentor.
    - guide_step is null: mentor completed the main guide.
    - guide_step is set: mentor completed that subtask.
    Mentors without any rows are treated as "nothing completed" (safe for existing mentors).
    """
    mentor_profile = models.ForeignKey(
        "accounts.MentorProfile",
        on_delete=models.CASCADE,
        related_name="guide_progress"
    )
    guide = models.ForeignKey(Guide, on_delete=models.CASCADE, related_name="progress")
    guide_step = models.ForeignKey(
        GuideStep,
        on_delete=models.CASCADE,
        related_name="progress",
        null=True,
        blank=True,
        help_text="Null = completed main guide; set = completed this subtask"
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']
        verbose_name = "Mentor guide progress"
        verbose_name_plural = "Mentor guide progress"
        unique_together = [['mentor_profile', 'guide', 'guide_step']]
        constraints = [
            # Only one "main guide" completion per mentor per guide (guide_step is null)
            models.UniqueConstraint(
                fields=['mentor_profile', 'guide'],
                condition=Q(guide_step__isnull=True),
                name='dashboard_mentor_mentorguideprogress_unique_main',
            ),
        ]

    def __str__(self):
        if self.guide_step_id:
            return f"{self.mentor_profile} – {self.guide.name} / {self.guide_step.name}"
        return f"{self.mentor_profile} – {self.guide.name} (main)"
