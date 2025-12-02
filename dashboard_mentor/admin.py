from django.contrib import admin
from .models import Credential, Tag

class CredentialAdmin(admin.ModelAdmin):
    list_display = ('title', 'description_preview')
    search_fields = ('title', 'description')
    
    def description_preview(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_preview.short_description = 'Description'

class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

admin.site.register(Credential, CredentialAdmin)
admin.site.register(Tag, TagAdmin)
