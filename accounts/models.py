from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from .managers import CustomUserManager

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("email address", unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_email_verified = models.BooleanField(default=False, help_text="Designates whether this user's email has been verified.")
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def save(self, *args, **kwargs):
        """Override save to ensure email is always stored in lowercase"""
        if self.email:
            self.email = self.email.lower().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

    @property
    def profile(self):
        """Return the appropriate profile (UserProfile or MentorProfile) for backward compatibility"""
        try:
            return self.mentor_profile
        except MentorProfile.DoesNotExist:
            try:
                return self.user_profile
            except UserProfile.DoesNotExist:
                return None

# Profile Models
class UserProfile(models.Model):
    """Profile for regular users"""
    ROLE_CHOICES = [
        ('user', 'User'),
    ]
    
    user = models.OneToOneField("accounts.CustomUser", on_delete=models.CASCADE, related_name="user_profile")
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user', editable=False)  # Not changeable
    # Timezone fields
    detected_timezone = models.CharField(max_length=64, blank=True, null=True, help_text="Browser-detected timezone, updated on each page load")
    selected_timezone = models.CharField(max_length=64, blank=True, null=True, help_text="User's selected/preferred timezone")
    confirmed_timezone_mismatch = models.BooleanField(default=False, help_text="True if user confirmed they want to keep a different timezone than detected")
    # Legacy field (kept for backward compatibility, will be migrated)
    time_zone = models.CharField(max_length=64, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    mentors = models.ManyToManyField("accounts.MentorProfile", related_name="users", blank=True)
    sessions = models.ManyToManyField("general.Session", related_name="user_profiles", blank=True)
    manuals = models.JSONField(default=list, blank=True)  # Navigation tutorial manuals

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user.email})"

# Import constants function to avoid circular imports
def get_first_session_free_choices():
    from dashboard_mentor.constants import FIRST_SESSION_FREE_CHOICES
    return FIRST_SESSION_FREE_CHOICES

class MentorProfile(models.Model):
    """Profile for mentors"""
    ROLE_CHOICES = [
        ('mentor', 'Mentor'),
    ]
    
    MENTOR_TYPES = [
        ('life_coach', 'Life Coach'),
        ('career_coach', 'Career Coach'),
        ('business_coach', 'Business Coach'),
        ('health_coach', 'Health Coach'),
        ('other', 'Other'),
    ]
    
    SUBSCRIPTION_TYPES = [
        ('free_trial', 'Free Trial'),
        ('monthly_basic', 'Monthly Basic'),
        ('monthly_pro', 'Monthly Pro'),
        ('annual_basic', 'Annual Basic'),
        ('annual_pro', 'Annual Pro'),
        ('per_session', 'Per Session (%)'),
    ]
    
    PROMOTION_STATUSES = [
        ('draft', 'Draft'),
        ('to_be_paid', 'To Be Paid'),
        ('paid', 'Paid'),
        ('active', 'Active'),
        ('finished', 'Finished'),
    ]
    
    # Basic Info
    user = models.OneToOneField("accounts.CustomUser", on_delete=models.CASCADE, related_name="mentor_profile")
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='mentor', editable=False)  # Not changeable
    
    # Personal Info (could be JSON, but using separate fields for better querying)
    # Timezone fields
    detected_timezone = models.CharField(max_length=64, blank=True, null=True, help_text="Browser-detected timezone, updated on each page load")
    selected_timezone = models.CharField(max_length=64, blank=True, null=True, help_text="User's selected/preferred timezone")
    confirmed_timezone_mismatch = models.BooleanField(default=False, help_text="True if user confirmed they want to keep a different timezone than detected")
    # Legacy field (kept for backward compatibility, will be migrated)
    time_zone = models.CharField(max_length=64, blank=True, null=True)
    qualifications = models.ManyToManyField("dashboard_mentor.Qualification", related_name="mentors", blank=True)
    
    def get_qualifications_ordered(self):
        """Get qualifications in order using through model"""
        from dashboard_mentor.models import MentorProfileQualification
        # Get through model instances ordered by order field
        mpqs = MentorProfileQualification.objects.filter(
            mentor_profile=self
        ).select_related('qualification').order_by('order', 'qualification__title')
        return mpqs
    mentor_type = models.CharField(max_length=100, blank=True, null=True)  # Free text, suggestions from predefined list
    tags = models.JSONField(default=list, blank=True)  # Array of tag strings from predefined list
    languages = models.JSONField(default=list, blank=True)  # Array of language IDs from predefined list
    categories = models.JSONField(default=list, blank=True)  # Array of category IDs from predefined list
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    session_length = models.PositiveIntegerField(default=60, blank=True, null=True, help_text="Session length in minutes")
    first_session_free = models.BooleanField(default=False, help_text="Offer first session for free")
    first_session_length = models.PositiveIntegerField(blank=True, null=True, help_text="First session length in minutes (only used if first_session_free is True)")
    instagram_name = models.CharField(max_length=100, blank=True, null=True)
    linkedin_name = models.CharField(max_length=100, blank=True, null=True)
    personal_website = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True)
    quote = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    
    # Billing Info (JSON for flexibility)
    billing = models.JSONField(default=dict, blank=True)
    # Structure: {
    #   "residential_address": "...",
    #   "tax_id": "...",
    #   "bank_account": "...",
    #   "payment_method": "...",
    #   ... other payment fields
    # }
    
    # Subscription (JSON for complex subscription management)
    subscription = models.JSONField(default=dict, blank=True)
    # Structure: {
    #   "type": "monthly_basic" | "monthly_pro" | "annual_basic" | "annual_pro" | "free_trial" | "per_session",
    #   "subscription_id": "...",
    #   "start_date": "YYYY-MM-DD",
    #   "end_date": "YYYY-MM-DD",
    #   "status": "active" | "inactive" | "cancelled" | "expired",
    #   "per_session_percentage": 0.15,  # if type is "per_session"
    #   "history": [  # Track subscription changes
    #     {
    #       "type": "monthly_basic",
    #       "start_date": "YYYY-MM-DD",
    #       "end_date": "YYYY-MM-DD",
    #       "status": "active"
    #     }
    #   ]
    # }
    
    # Promotions (JSON for promotion management)
    promotions = models.JSONField(default=list, blank=True)
    # Structure: [
    #   {
    #     "type": "boost" | "featured" | "sponsored",
    #     "from_date": "YYYY-MM-DD",
    #     "to_date": "YYYY-MM-DD",
    #     "views_count": 1000,
    #     "status": "draft" | "to_be_paid" | "paid" | "active" | "finished"
    #   }
    # ]
    
    # Sessions (using ForeignKey relationship)
    sessions = models.ManyToManyField("general.Session", related_name="mentors", blank=True)
    
    # Clients (ManyToMany to UserProfile)
    clients = models.ManyToManyField("accounts.UserProfile", related_name="mentor_clients", blank=True)
    
    # Reviews (JSON for now, could be a separate model later)
    reviews = models.JSONField(default=list, blank=True)
    
    # Navigation tutorial manuals
    manuals = models.JSONField(default=list, blank=True)
    # Structure: [
    #   {
    #     "user_id": 123,
    #     "rating": 5,
    #     "comment": "...",
    #     "date": "YYYY-MM-DD"
    #   }
    # ]

    class Meta:
        verbose_name = "Mentor Profile"
        verbose_name_plural = "Mentor Profiles"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user.email})"

# Signal to auto-create appropriate profile when user is created
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """This signal will be handled by the registration view instead"""
    pass
