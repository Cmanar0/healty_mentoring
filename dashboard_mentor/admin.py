from django.contrib import admin
from .models import Credential, Tag, MentorType

class CredentialAdmin(admin.ModelAdmin):
    list_display = ('title', 'description_preview')
    search_fields = ('title', 'description')
    
    def description_preview(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_preview.short_description = 'Description'

class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class MentorTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_custom', 'created_at')
    list_filter = ('is_custom', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at',)

admin.site.register(Credential, CredentialAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(MentorType, MentorTypeAdmin)
