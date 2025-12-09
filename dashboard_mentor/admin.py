from django.contrib import admin
from .models import Tag, MentorAvailability

class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class MentorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('mentor', 'start_datetime', 'end_datetime', 'is_recurring', 'recurrence_rule', 'is_active')
    list_filter = ('is_recurring', 'is_active', 'recurrence_rule', 'start_datetime')
    search_fields = ('mentor__email', 'recurrence_rule')
    date_hierarchy = 'start_datetime'
    ordering = ('start_datetime',)

admin.site.register(Tag, TagAdmin)
admin.site.register(MentorAvailability, MentorAvailabilityAdmin)
