from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django import forms
from .models import (
    CustomUser, UserProfile, MentorProfile
)
from .forms import CustomUserCreationForm, CustomUserChangeForm

# Hide Authentication and Authorization groups
admin.site.unregister(Group)

# User Admin (no inline profiles since we have separate models)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ("email", "is_staff", "is_superuser")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {"fields": ("is_staff","is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )

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
            'fields': ('first_name', 'last_name', 'time_zone', 'profile_picture')
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

# Mentor Profile Admin
class MentorProfileAdmin(admin.ModelAdmin):
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
            'fields': ('time_zone', 'mentor_type', 'bio', 'quote', 'credentials', 'tags', 'languages', 'categories', 'nationality')
        }),
        ('Pricing & Session', {
            'fields': ('price_per_hour', 'first_session_free')
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
    filter_horizontal = ('credentials', 'sessions', 'clients')
    
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
