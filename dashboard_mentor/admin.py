from django.contrib import admin
from .models import Qualification, Tag, MentorProfileQualification, MentorAvailability

class QualificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'subtitle', 'description_preview')
    search_fields = ('title', 'subtitle', 'description')
    
    def description_preview(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_preview.short_description = 'Description'

class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class MentorProfileQualificationAdmin(admin.ModelAdmin):
    list_display = ('mentor_profile', 'qualification', 'order')
    list_filter = ('mentor_profile',)
    ordering = ('mentor_profile', 'order')

class MentorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('mentor', 'start_datetime', 'end_datetime', 'is_recurring', 'recurrence_rule', 'is_active')
    list_filter = ('is_recurring', 'is_active', 'recurrence_rule', 'start_datetime')
    search_fields = ('mentor__email', 'recurrence_rule')
    date_hierarchy = 'start_datetime'
    ordering = ('start_datetime',)

admin.site.register(Qualification, QualificationAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(MentorProfileQualification, MentorProfileQualificationAdmin)
admin.site.register(MentorAvailability, MentorAvailabilityAdmin)
