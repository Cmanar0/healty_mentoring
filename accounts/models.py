from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from .managers import CustomUserManager

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("email address", unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


    def __str__(self):
        return self.email

def credentials_upload_to(instance, filename):
    return f"credentials/{instance.user.id}/{filename}"

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('mentor', 'Mentor'),
    ]
    
    user = models.OneToOneField("accounts.CustomUser", on_delete=models.CASCADE, related_name="profile")
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    # email is stored on user.email; duplicate only if needed:
    time_zone = models.CharField(max_length=64, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    # credentials: array-like JSON field containing items with a title
    # Use JSONField (requires Postgres in prod) but ok in Django with SQLite too.
    credentials = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user.email})"

# Signal to auto-create profile when user is created
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=CustomUser)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance, first_name="", last_name="")
    else:
        instance.profile.save()
