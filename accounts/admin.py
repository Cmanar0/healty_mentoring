from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django import forms
from django.utils import timezone
from .models import (
    CustomUser, UserProfile, MentorProfile, MentorClientRelationship
)
from .forms import CustomUserCreationForm, CustomUserChangeForm
from dashboard_mentor.models import MentorProfileQualification

# Hide Authentication and Authorization groups
admin.site.unregister(Group)

# User Admin (no inline profiles since we have separate models)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ("email", "is_email_verified", "is_staff", "is_superuser")
    list_filter = ("is_email_verified", "is_staff", "is_superuser")
    ordering = ("email",)
    actions = ["verify_emails", "unverify_emails"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Email Verification", {"fields": ("is_email_verified",)}),
        ("Permissions", {"fields": ("is_staff","is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
    
    def verify_emails(self, request, queryset):
        """Admin action to verify selected users' emails"""
        updated = queryset.update(is_email_verified=True)
        self.message_user(request, f"{updated} user(s) email(s) verified successfully.")
    verify_emails.short_description = "Verify email for selected users"
    
    def unverify_emails(self, request, queryset):
        """Admin action to unverify selected users' emails"""
        updated = queryset.update(is_email_verified=False)
        self.message_user(request, f"{updated} user(s) email(s) unverified.")
    unverify_emails.short_description = "Unverify email for selected users"

# User Profile Admin
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email_display', 'role')
    list_filter = ('role',)
    search_fields = ('first_name', 'last_name', 'user__email')
    readonly_fields = ('role', 'user_email_display')  # Role is not changeable
    exclude = ('user',)  # Hide User field from form, but show email in readonly
    
    fieldsets = (
        ('User Information', {
            'fields': ('user_email_display', 'role')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'profile_picture')
        }),
        ('Timezone Settings', {
            'fields': ('detected_timezone', 'selected_timezone', 'confirmed_timezone_mismatch'),
            'description': 'Detected timezone is updated automatically. Selected timezone is user\'s preference. Confirmed mismatch indicates user wants to keep a different timezone than detected.'
        }),
        ('Legacy Timezone', {
            'fields': ('time_zone',),
            'classes': ('collapse',),
            'description': 'Legacy field - kept for backward compatibility. Use selected_timezone instead.'
        }),
        ('Relations', {
            'fields': ('mentors', 'sessions'),
            'classes': ('collapse',)
        }),
        ('Tutorial Manuals', {
            'fields': ('manuals',),
            'classes': ('collapse',),
            'description': 'Navigation tutorial manuals. See documentation for data structure.'
        }),
    )
    filter_horizontal = ('mentors', 'sessions')
    
    def email_display(self, obj):
        return obj.user.email
    email_display.short_description = 'Email'
    
    def user_email_display(self, obj):
        return obj.user.email
    user_email_display.short_description = 'User Email'
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

# Inline for Qualifications
class MentorProfileQualificationInline(admin.TabularInline):
    model = MentorProfileQualification
    extra = 1
    ordering = ('order',)

# Mentor Profile Admin
class MentorProfileAdmin(admin.ModelAdmin):
    inlines = [MentorProfileQualificationInline]
    list_display = ('first_name', 'last_name', 'email_display', 'role', 'mentor_type')
    list_filter = ('role', 'mentor_type')
    search_fields = ('first_name', 'last_name', 'user__email')
    readonly_fields = ('role', 'user_email_display')  # Role is not changeable
    exclude = ('user',)  # Hide User field from form, but show email in readonly
    
    fieldsets = (
        ('User Information', {
            'fields': ('user_email_display', 'role')
        }),
        ('Basic Information', {
            'fields': ('first_name', 'last_name', 'profile_picture')
        }),
        ('Personal Information', {
            'fields': ('mentor_type', 'bio', 'quote', 'tags', 'languages', 'categories')
        }),
        ('Timezone Settings', {
            'fields': ('detected_timezone', 'selected_timezone', 'confirmed_timezone_mismatch'),
            'description': 'Detected timezone is updated automatically. Selected timezone is user\'s preference. Confirmed mismatch indicates user wants to keep a different timezone than detected.'
        }),
        ('Legacy Timezone', {
            'fields': ('time_zone',),
            'classes': ('collapse',),
            'description': 'Legacy field - kept for backward compatibility. Use selected_timezone instead.'
        }),
        ('Pricing & Session', {
            'fields': ('price_per_hour', 'session_length', 'first_session_free', 'first_session_length')
        }),
        ('Social Media & Links', {
            'fields': ('instagram_name', 'linkedin_name', 'personal_website')
        }),
        ('Billing', {
            'fields': ('billing',),
            'classes': ('collapse',)
        }),
        ('Subscription', {
            'fields': ('subscription',),
            'classes': ('collapse',)
        }),
        ('Promotions', {
            'fields': ('promotions',),
            'classes': ('collapse',)
        }),
        ('Relations', {
            'fields': ('sessions', 'clients', 'reviews'),
            'classes': ('collapse',)
        }),
        ('Tutorial Manuals', {
            'fields': ('manuals',),
            'classes': ('collapse',),
            'description': 'Navigation tutorial manuals. See documentation for data structure.'
        }),
        ('Availability - One-Time Slots', {
            'fields': ('one_time_slots',),
            'description': 'List of one-time availability windows. Format: [{"id": "<uuid>", "start": "YYYY-MM-DDTHH:MM:SS+00:00", "end": "YYYY-MM-DDTHH:MM:SS+00:00", "length": <minutes>, "created_at": "YYYY-MM-DDTHH:MM:SS+00:00"}]'
        }),
        ('Availability - Recurring Slots', {
            'fields': ('recurring_slots',),
            'description': 'List of recurring availability rules. Format: [{"id": "<uuid>", "type": "daily"|"weekly"|"monthly", "weekdays": [...], "day_of_month": <1-31|null>, "start_time": "HH:MM", "end_time": "HH:MM", "created_at": "YYYY-MM-DDTHH:MM:SS+00:00"}]'
        }),
    )
    filter_horizontal = ('sessions', 'clients')
    
    def email_display(self, obj):
        return obj.user.email
    email_display.short_description = 'Email'
    
    def user_email_display(self, obj):
        return obj.user.email
    user_email_display.short_description = 'User Email'
    
    class Meta:
        verbose_name = "Mentor Profile"
        verbose_name_plural = "Mentor Profiles"

# Mentor-Client Relationship Admin
class MentorClientRelationshipAdmin(admin.ModelAdmin):
    list_display = ('mentor_name', 'client_name', 'client_email', 'status', 'confirmed', 'created_at', 'invited_at', 'verified_at')
    list_filter = ('status', 'confirmed', 'created_at', 'invited_at', 'verified_at')
    search_fields = ('mentor__first_name', 'mentor__last_name', 'mentor__user__email', 
                    'client__first_name', 'client__last_name', 'client__user__email',
                    'invitation_token', 'confirmation_token')
    readonly_fields = ('created_at', 'updated_at', 'invited_at', 'verified_at', 'sessions_count', 'total_earnings')
    fieldsets = (
        ('Relationship', {
            'fields': ('mentor', 'client', 'status', 'confirmed')
        }),
        ('Tokens', {
            'fields': ('invitation_token', 'confirmation_token'),
            'description': 'Tokens are used for invitation links. They are cleared after acceptance.'
        }),
        ('Statistics', {
            'fields': ('sessions_count', 'total_earnings'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'invited_at', 'verified_at'),
            'classes': ('collapse',)
        }),
    )
    
    def mentor_name(self, obj):
        return f"{obj.mentor.first_name} {obj.mentor.last_name}"
    mentor_name.short_description = 'Mentor'
    
    def client_name(self, obj):
        return f"{obj.client.first_name} {obj.client.last_name}"
    client_name.short_description = 'Client'
    
    def client_email(self, obj):
        return obj.client.user.email
    client_email.short_description = 'Client Email'
    
    actions = ['reset_to_inactive', 'activate_relationship', 'deny_relationship']
    
    def reset_to_inactive(self, request, queryset):
        """Reset selected relationships to inactive status (unconfirmed)"""
        count = 0
        for relationship in queryset:
            relationship.status = 'inactive'
            relationship.confirmed = False
            # Regenerate confirmation token if user is verified, invitation token if not
            from django.utils.crypto import get_random_string
            if relationship.client.user.is_email_verified:
                if not relationship.confirmation_token:
                    relationship.confirmation_token = get_random_string(64)
            else:
                if not relationship.invitation_token:
                    relationship.invitation_token = get_random_string(64)
            relationship.save()
            count += 1
        self.message_user(request, f"{count} relationship(s) reset to inactive (unconfirmed).")
    reset_to_inactive.short_description = "Reset to inactive (unconfirmed)"
    
    def activate_relationship(self, request, queryset):
        """Confirm selected relationships"""
        count = 0
        for relationship in queryset:
            relationship.confirmed = True
            relationship.status = 'confirmed'
            relationship.verified_at = relationship.verified_at or timezone.now()
            # Clear tokens after confirmation
            relationship.invitation_token = None
            relationship.confirmation_token = None
            # Add to ManyToMany if not already there
            if relationship.client not in relationship.mentor.clients.all():
                relationship.mentor.clients.add(relationship.client)
            relationship.save()
            count += 1
        self.message_user(request, f"{count} relationship(s) confirmed.")
    activate_relationship.short_description = "Confirm relationship(s)"
    
    def deny_relationship(self, request, queryset):
        """Deny selected relationships"""
        count = 0
        for relationship in queryset:
            relationship.status = 'denied'
            relationship.confirmed = False
            relationship.confirmation_token = None
            relationship.invitation_token = None
            relationship.save()
            count += 1
        self.message_user(request, f"{count} relationship(s) denied.")
    deny_relationship.short_description = "Deny relationship(s)"

# Register models
admin.site.register(CustomUser, UserAdmin)

# Group User Profile related models
admin.site.register(UserProfile, UserProfileAdmin)

# Group Mentor Profile related models
admin.site.register(MentorProfile, MentorProfileAdmin)

# Register Mentor-Client Relationship
admin.site.register(MentorClientRelationship, MentorClientRelationshipAdmin)
