from django.contrib import admin
from .models import Session

class SessionAdmin(admin.ModelAdmin):
    list_display = ('start_datetime', 'end_datetime', 'created_by', 'session_type')
    list_filter = ('session_type', 'start_datetime')
    search_fields = ('created_by__email', 'note')
    filter_horizontal = ('attendees',)

admin.site.register(Session, SessionAdmin)
