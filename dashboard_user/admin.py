from django.contrib import admin
from .models import (
    Project, ProjectTemplate, ProjectModule, ProjectModuleInstance,
    Questionnaire, Question, QuestionnaireResponse,
    ProjectStage, ProjectStageNote, 
    ProjectStageNoteAttachment, ProjectStageNoteComment,
    Task
)


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ('question_text', 'question_type', 'is_required', 'order')
    ordering = ('order',)
    show_change_link = True


class QuestionnaireInline(admin.StackedInline):
    model = Questionnaire
    extra = 0
    can_delete = False
    fields = ('title', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    show_change_link = True


@admin.register(ProjectTemplate)
class ProjectTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_custom', 'author', 'get_questionnaire', 'get_question_count', 'is_active', 'order', 'created_at')
    list_filter = ('is_custom', 'is_active')
    search_fields = ('name', 'description')
    list_editable = ('is_active', 'order')
    filter_horizontal = ('preselected_modules',)
    inlines = [QuestionnaireInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Display Settings', {
            'fields': ('icon', 'color', 'order', 'is_active')
        }),
        ('Custom Template', {
            'fields': ('is_custom', 'author'),
        }),
        ('Preselected Modules', {
            'fields': ('preselected_modules',),
            'description': 'Modules that will be automatically selected when this template is chosen in the Create Project popup.'
        }),
        ('Advanced', {
            'fields': ('template_fields',),
            'classes': ('collapse',)
        }),
    )
    
    def get_questionnaire(self, obj):
        """Display the questionnaire linked to this template"""
        if hasattr(obj, 'questionnaire'):
            return f"{obj.questionnaire.title} (ID: {obj.questionnaire.id})"
        return "No questionnaire"
    get_questionnaire.short_description = 'Questionnaire'
    
    def get_question_count(self, obj):
        """Display the number of questions in the questionnaire"""
        if hasattr(obj, 'questionnaire'):
            count = obj.questionnaire.questions.count()
            return f"{count} question{'s' if count != 1 else ''}"
        return "0 questions"
    get_question_count.short_description = 'Questions'


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'template', 'project_owner', 'supervised_by', 'created_at')
    list_filter = ('template', 'template__is_custom')
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


@admin.register(ProjectStage)
class ProjectStageAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'order', 'is_completed', 'created_at')
    list_filter = ('is_completed', 'created_from_template', 'project')
    search_fields = ('title', 'description', 'project__title')
    list_editable = ('is_completed',)
    ordering = ('project', 'order')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'stage', 'user_active_backlog', 'mentor_backlog', 'completed', 'deadline', 'created_at')
    list_filter = ('completed', 'assigned', 'is_ai_generated', 'stage__project')
    search_fields = ('title', 'description')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(ProjectModule)
class ProjectModuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'module_type', 'is_active', 'order')
    list_filter = ('module_type', 'is_active')
    search_fields = ('name', 'description')
    list_editable = ('is_active', 'order')


@admin.register(ProjectModuleInstance)
class ProjectModuleInstanceAdmin(admin.ModelAdmin):
    list_display = ('project', 'module', 'is_active', 'order')
    list_filter = ('is_active', 'module')
    search_fields = ('project__title', 'module__name')


@admin.register(Questionnaire)
class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = ('template', 'title', 'get_question_count', 'created_at')
    list_filter = ('template__is_custom',)
    search_fields = ('template__name', 'title')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [QuestionInline]
    
    def get_question_count(self, obj):
        """Display the number of questions in this questionnaire"""
        count = obj.questions.count()
        return f"{count} question{'s' if count != 1 else ''}"
    get_question_count.short_description = 'Questions'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'questionnaire', 'get_template', 'question_type', 'is_required', 'order')
    list_filter = ('question_type', 'is_required', 'questionnaire__template')
    search_fields = ('question_text',)
    ordering = ('questionnaire', 'order')
    
    def get_template(self, obj):
        """Display the template this question belongs to"""
        if obj.questionnaire and obj.questionnaire.template:
            return obj.questionnaire.template.name
        return "-"
    get_template.short_description = 'Template'


@admin.register(QuestionnaireResponse)
class QuestionnaireResponseAdmin(admin.ModelAdmin):
    list_display = ('project', 'questionnaire', 'completed_at')
    list_filter = ('questionnaire__template', 'completed_at')
    search_fields = ('project__title', 'questionnaire__title')
    readonly_fields = ('completed_at', 'updated_at')
