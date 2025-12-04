from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django import forms
from .models import (
    CustomUser, UserProfile, MentorProfile
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
            'fields': ('mentor_type', 'bio', 'quote', 'tags', 'languages', 'categories', 'nationality')
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

# Register models
admin.site.register(CustomUser, UserAdmin)

# Group User Profile related models
admin.site.register(UserProfile, UserProfileAdmin)

# Group Mentor Profile related models
admin.site.register(MentorProfile, MentorProfileAdmin)
