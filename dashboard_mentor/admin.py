from django.contrib import admin
from .models import MentorAvailability
from accounts.models import MentorProfile, CustomUser

class MentorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('mentor', 'start_datetime', 'end_datetime', 'is_recurring', 'recurrence_rule', 'is_active')
    list_filter = ('is_recurring', 'is_active', 'recurrence_rule', 'start_datetime')
    search_fields = ('mentor__email', 'recurrence_rule')
    date_hierarchy = 'start_datetime'
    ordering = ('start_datetime',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "mentor":
            # Only show users who have a mentor profile
            mentor_user_ids = MentorProfile.objects.all().values_list('user_id', flat=True)
            kwargs["queryset"] = CustomUser.objects.filter(id__in=mentor_user_ids)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(MentorAvailability, MentorAvailabilityAdmin)
