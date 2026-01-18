from django.contrib import admin
from .models import Project, ProjectTemplate


@admin.register(ProjectTemplate)
class ProjectTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active', 'order', 'created_at')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')
    list_editable = ('is_active', 'order')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category')
        }),
        ('Display Settings', {
            'fields': ('icon', 'color', 'order', 'is_active')
        }),
        ('Advanced', {
            'fields': ('template_fields',),
            'classes': ('collapse',)
        }),
    )


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'template', 'project_owner', 'supervised_by', 'created_at')
    list_filter = ('template', 'template__category')
    search_fields = ('title',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'template')
        }),
        ('Ownership & Supervision', {
            'fields': ('project_owner', 'supervised_by')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make project_owner readonly after creation"""
        readonly = list(super().get_readonly_fields(request, obj))
        if obj:  # Editing an existing object
            readonly.append('project_owner')
        return readonly
    
    def save_model(self, request, obj, form, change):
        """Auto-set project_owner and supervised_by based on who creates the project"""
        if not change:  # Creating new project
            # Check if request.user has a UserProfile or MentorProfile
            try:
                user_profile = request.user.user_profile
                # User is creating the project
                obj.project_owner = user_profile
                # Auto-set supervised_by to the mentor selected in form, or first mentor if user has mentors
                if not obj.supervised_by and user_profile.mentors.exists():
                    obj.supervised_by = user_profile.mentors.first()
            except:
                try:
                    mentor_profile = request.user.mentor_profile
                    # Mentor is creating the project
                    obj.supervised_by = mentor_profile
                    # Mentor can set project_owner manually in form, or leave blank
                except:
                    pass  # Admin user without profile
        else:
            # When editing, supervised_by can be changed, but project_owner cannot
            # If supervised_by is being set and project_owner is a user, ensure the mentor is in user's mentors list
            if obj.project_owner and obj.supervised_by:
                if obj.supervised_by not in obj.project_owner.mentors.all():
                    # Add the mentor to user's mentors if not already there
                    obj.project_owner.mentors.add(obj.supervised_by)
        super().save_model(request, obj, form, change)

admin.site.register(Project, ProjectAdmin)
