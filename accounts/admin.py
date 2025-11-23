from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, UserProfile
from .forms import CustomUserCreationForm, CustomUserChangeForm

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'profile'

class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ("email", "is_staff", "is_superuser")
    ordering = ("email",)
    inlines = (UserProfileInline,)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {"fields": ("is_staff","is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )

admin.site.register(CustomUser, UserAdmin)
admin.site.register(UserProfile)
