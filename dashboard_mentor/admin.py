from django.contrib import admin
from .models import Guide, GuideStep, MentorGuideProgress

# MentorAvailability model has been removed - availability is now stored in MentorProfile JSON fields
# See accounts.models.MentorProfile.availability_slots and recurring_availability_slots


class GuideStepInline(admin.TabularInline):
    model = GuideStep
    extra = 0
    ordering = ['order', 'name']


@admin.register(Guide)
class GuideAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'ai_coins', 'is_active', 'button_name']
    list_editable = ['order', 'ai_coins', 'is_active']
    ordering = ['order', 'name']
    inlines = [GuideStepInline]


@admin.register(GuideStep)
class GuideStepAdmin(admin.ModelAdmin):
    list_display = ['name', 'guide', 'order', 'ai_coins', 'url', 'action_id', 'is_active']
    list_editable = ['ai_coins', 'order', 'is_active']
    list_filter = ['guide']
    ordering = ['guide', 'order', 'name']


@admin.register(MentorGuideProgress)
class MentorGuideProgressAdmin(admin.ModelAdmin):
    list_display = ['mentor_profile', 'guide', 'guide_step', 'completed_at']
    list_filter = ['guide']
    readonly_fields = ['completed_at']
    ordering = ['-completed_at']
