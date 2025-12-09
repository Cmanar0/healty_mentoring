from django.db import models
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

class MentorAvailability(models.Model):
    """Model to store time periods when a mentor is available for booking"""
    mentor = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="availabilities"
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    is_recurring = models.BooleanField(default=False)
    recurrence_rule = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Mentor Availability"
        verbose_name_plural = "Mentor Availabilities"
        ordering = ['start_datetime']

    def clean(self):
        """Validate that end_datetime is strictly greater than start_datetime"""
        if self.start_datetime and self.end_datetime:
            if self.end_datetime <= self.start_datetime:
                raise ValidationError({
                    'end_datetime': 'End datetime must be strictly greater than start datetime.'
                })

    def save(self, *args, **kwargs):
        """Override save to call clean validation"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Availability for {self.mentor}: {self.start_datetime} → {self.end_datetime}"
