from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class ProjectTemplate(models.Model):
    """Template model for project types (e.g., Mindset, Trading, Weight Loss, Business Plan)"""
    
    name = models.CharField(max_length=100, unique=True, help_text="Template name (e.g., 'Mindset', 'Trading', 'Weight Loss')")
    description = models.TextField(blank=True, help_text="Description of what this template is for")
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class (e.g., 'fa-brain', 'fa-chart-line')")
    color = models.CharField(max_length=7, default='#10b981', help_text="Hex color for template (e.g., #10b981)")
    image = models.ImageField(upload_to='project_templates/', blank=True, null=True, help_text="Template image/icon")
    is_active = models.BooleanField(default=True, help_text="Whether this template is available for selection")
    order = models.IntegerField(default=0, help_text="Display order (lower numbers appear first)")
    
    # Template structure/metadata (for future extensibility)
    template_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="Optional: Custom fields structure for this template type"
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Custom Template Fields
    is_custom = models.BooleanField(default=False, help_text="True if created by a mentor")
    author = models.ForeignKey(
        "accounts.MentorProfile", 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name="custom_templates",
        help_text="The mentor who created this template"
    )
    
    # Preselected modules for this template
    preselected_modules = models.ManyToManyField(
        'ProjectModule',
        blank=True,
        related_name='templates',
        help_text="Modules that should be automatically selected when using this template"
    )

    class Meta:
        verbose_name = "Project Template"
        verbose_name_plural = "Project Templates"
        ordering = ['-is_custom', 'order', 'name']

    def __str__(self):
        return self.name


class Project(models.Model):
    """Project model for users"""
    
    ASSIGNMENT_STATUS_CHOICES = [
        ('pending', 'Pending Assignment'),
        ('assigned', 'Assigned'),
        ('accepted', 'Accepted'),
    ]
    
    # Basic Fields
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, help_text="Project description")
    
    # Relationships
    template = models.ForeignKey(
        ProjectTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        help_text="Project template (e.g., Mindset, Trading, Weight Loss)"
    )
    project_owner = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE, related_name="owned_projects", null=True, blank=True)
    supervised_by = models.ForeignKey("accounts.MentorProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="supervised_projects")
    created_by = models.ForeignKey("accounts.CustomUser", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_projects")
    
    # Assignment Flow
    assignment_status = models.CharField(max_length=20, choices=ASSIGNMENT_STATUS_CHOICES, default='pending')
    assignment_token = models.CharField(max_length=64, blank=True, null=True)
    
    # Questionnaire
    questionnaire_completed = models.BooleanField(default=False)
    questionnaire_completed_at = models.DateTimeField(blank=True, null=True)
    
    # Project Goals
    goal = models.TextField(blank=True)
    target_completion_date = models.DateField(blank=True, null=True)
    current_status = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        ordering = ['-created_at', 'title']

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        """Override save to recalculate stage statuses when target_completion_date changes"""
        # Check if target_completion_date is being changed
        if self.pk:
            try:
                old_project = Project.objects.get(pk=self.pk)
                target_date_changed = old_project.target_completion_date != self.target_completion_date
            except Project.DoesNotExist:
                target_date_changed = False
        else:
            target_date_changed = False
        
        # Save the project first
        super().save(*args, **kwargs)
        
        # If target_completion_date changed, recalculate all stage statuses
        if target_date_changed:
            for stage in self.stages.filter(is_disabled=False):
                stage.progress_status = stage.calculate_progress_status()
                stage.save(update_fields=['progress_status'])

    def create_stages_from_template(self):
        """
        Create stages from template's stage templates.
        Called when project is created from a template.
        Note: ProjectStageTemplate has been removed - this method is kept for compatibility but does nothing.
        """
        # ProjectStageTemplate has been removed - stages are now created manually or via AI
        pass


class ProjectModule(models.Model):
    """Reusable modules that can be added to projects"""
    MODULE_TYPES = [
        ('financial_planning', 'Financial Planning'),
        ('real_world_validation', 'Real World Validation'),
        ('progress_tracking', 'Progress Tracking'),
        ('milestone_checkpoints', 'Milestone Checkpoints'),
        ('resource_management', 'Resource Management'),
        ('stakeholder_feedback', 'Stakeholder Feedback'),
        ('risk_assessment', 'Risk Assessment'),
        ('timeline_management', 'Timeline Management'),
        ('habit_tracking', 'Habit Tracking'),
        ('identity_mindset', 'Identity/Mindset Tracking'),
        ('career_transition', 'Career Transition'),
        ('health_metrics', 'Health Metrics'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    module_type = models.CharField(max_length=50, choices=MODULE_TYPES)
    description = models.TextField()
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=7, default='#10b981')
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    config_schema = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = "Project Module"
        verbose_name_plural = "Project Modules"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class ProjectModuleInstance(models.Model):
    """Instance of a module added to a specific project"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="module_instances")
    module = models.ForeignKey(ProjectModule, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    module_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Project Module Instance"
        verbose_name_plural = "Project Module Instances"
        unique_together = ['project', 'module']
        ordering = ['order']
    
    def __str__(self):
        return f"{self.project.title} - {self.module.name}"


class Questionnaire(models.Model):
    """Questionnaire model - one per template"""
    template = models.OneToOneField(
        ProjectTemplate,
        on_delete=models.CASCADE,
        related_name="questionnaire",
        help_text="The questionnaire for this template"
    )
    title = models.CharField(max_length=200, default="Onboarding Questionnaire")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Questionnaire"
        verbose_name_plural = "Questionnaires"
    
    def __str__(self):
        return f"{self.template.name} - {self.title}"


class Question(models.Model):
    """Individual question within a questionnaire"""
    QUESTION_TYPES = [
        ('text', 'Text'),
        ('textarea', 'Long Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('select', 'Select'),
        ('multiselect', 'Multiple Select'),
    ]
    
    questionnaire = models.ForeignKey(
        Questionnaire,
        on_delete=models.CASCADE,
        related_name="questions",
        help_text="The questionnaire this question belongs to"
    )
    question_text = models.CharField(max_length=500)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='text')
    is_required = models.BooleanField(default=True)
    is_target_date = models.BooleanField(
        default=False,
        help_text="If True, this date answer will be used as the project's target completion date. Only one date question per questionnaire can be marked as target date."
    )
    order = models.IntegerField(default=0)
    options = models.JSONField(default=list, blank=True, help_text="Options for select/multiselect questions")
    help_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Question"
        verbose_name_plural = "Questions"
        ordering = ['order']
        unique_together = ['questionnaire', 'order']
    
    def __str__(self):
        return self.question_text


class QuestionnaireResponse(models.Model):
    """Client's answers to a questionnaire - stored as JSON"""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="questionnaire_responses",
        help_text="The project this response belongs to"
    )
    questionnaire = models.ForeignKey(
        Questionnaire,
        on_delete=models.CASCADE,
        related_name="responses",
        help_text="The questionnaire that was answered"
    )
    answers = models.JSONField(
        default=dict,
        help_text="JSON object mapping question IDs to answers: {question_id: answer_text}"
    )
    completed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Questionnaire Response"
        verbose_name_plural = "Questionnaire Responses"
        unique_together = ['project', 'questionnaire']
    
    def __str__(self):
        return f"{self.project.title} - {self.questionnaire.title}"


class ProjectStage(models.Model):
    """Stages/steps for a project"""
    PROGRESS_STATUS_CHOICES = [
        ('created', 'Created'),
        ('in_progress', 'In Progress'),
        ('overdue', 'Overdue'),
        ('completed', 'Completed'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="stages")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    start_date = models.DateField(blank=True, null=True, help_text="Start date for this stage")
    end_date = models.DateField(blank=True, null=True, help_text="End date for this stage")
    target_date = models.DateField(blank=True, null=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    completed_by = models.ForeignKey("accounts.CustomUser", on_delete=models.SET_NULL, null=True, blank=True)
    depends_on = models.ManyToManyField('self', symmetrical=False, blank=True, related_name="blocks")
    created_from_template = models.BooleanField(default=False)
    is_ai_generated = models.BooleanField(default=False, help_text="True if stage was generated by AI")
    is_pending_confirmation = models.BooleanField(default=False, help_text="True if AI-generated stage is pending confirmation")
    progress_status = models.CharField(
        max_length=20,
        choices=PROGRESS_STATUS_CHOICES,
        default='created',
        help_text="Current progress status of the stage"
    )
    is_disabled = models.BooleanField(
        default=False,
        help_text="True if stage is disabled"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Project Stage"
        verbose_name_plural = "Project Stages"
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['project', 'order']),
            models.Index(fields=['progress_status']),
            models.Index(fields=['is_disabled']),
        ]
    
    def __str__(self):
        return f"{self.project.title} - {self.title}"
    
    def calculate_progress_status(self):
        """
        Calculate and return the current progress status based on dates and tasks.
        Priority: completed > overdue > in_progress > created
        
        A stage is considered overdue if:
        1. Today is past the stage's end_date, OR
        2. The stage's end_date is later than the project's target_completion_date
        """
        from datetime import date
        
        today = date.today()
        
        # Check if completed (highest priority)
        # Must have at least one task and all tasks completed
        # Only check tasks if the stage has been saved (has a primary key)
        if self.pk:
            total_tasks = self.backlog_tasks.count()
            completed_tasks = self.backlog_tasks.filter(completed=True).count()
            
            if total_tasks > 0 and completed_tasks == total_tasks:
                return 'completed'
        
        # Check if stage end_date is past project target_completion_date (overdue)
        if self.end_date and hasattr(self, 'project') and self.project and self.project.target_completion_date:
            if self.end_date > self.project.target_completion_date:
                return 'overdue'
        
        # Check dates
        if self.start_date and self.end_date:
            if today < self.start_date:
                return 'created'
            elif today >= self.start_date and today <= self.end_date:
                return 'in_progress'
            else:  # today > end_date
                return 'overdue'
        elif self.start_date:
            if today < self.start_date:
                return 'created'
            else:
                return 'in_progress'
        else:
            # No dates set, default to created
            return 'created'
    
    def save(self, *args, **kwargs):
        """Auto-update progress_status on save"""
        if not self.is_disabled:
            self.progress_status = self.calculate_progress_status()
        super().save(*args, **kwargs)


class ProjectStageNote(models.Model):
    """Notes on project stages"""
    ROLE_CHOICES = [
        ('mentor', 'Mentor'),
        ('client', 'Client'),
    ]
    
    stage = models.ForeignKey(ProjectStage, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey("accounts.CustomUser", on_delete=models.SET_NULL, null=True, blank=True)
    author_name = models.CharField(max_length=200, blank=True)
    author_email = models.EmailField(blank=True)
    author_role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True)
    is_author_deleted = models.BooleanField(default=False)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Project Stage Note"
        verbose_name_plural = "Project Stage Notes"
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        """Cache author info on save for GDPR compliance"""
        if self.author and not self.is_author_deleted:
            if not self.author_name:
                if hasattr(self.author, 'profile'):
                    self.author_name = f"{self.author.profile.first_name} {self.author.profile.last_name}".strip()
                elif hasattr(self.author, 'user_profile'):
                    self.author_name = f"{self.author.user_profile.first_name} {self.author.user_profile.last_name}".strip()
            if not self.author_email:
                self.author_email = self.author.email
            if not self.author_role:
                if hasattr(self.author, 'profile') and self.author.profile.role == 'mentor':
                    self.author_role = 'mentor'
                elif hasattr(self.author, 'user_profile'):
                    self.author_role = 'client'
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.stage.title} - Note by {self.author_name or 'Unknown'}"


class ProjectStageNoteAttachment(models.Model):
    """Image attachments for stage notes"""
    note = models.ForeignKey(ProjectStageNote, on_delete=models.CASCADE, related_name="attachments")
    image = models.ImageField(upload_to='project_stages/attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Project Stage Note Attachment"
        verbose_name_plural = "Project Stage Note Attachments"
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"Attachment for {self.note.stage.title}"


class ProjectStageNoteComment(models.Model):
    """Comments on stage notes"""
    ROLE_CHOICES = [
        ('mentor', 'Mentor'),
        ('client', 'Client'),
    ]
    
    note = models.ForeignKey(ProjectStageNote, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey("accounts.CustomUser", on_delete=models.SET_NULL, null=True, blank=True)
    author_name = models.CharField(max_length=200, blank=True)
    author_email = models.EmailField(blank=True)
    author_role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True)
    is_author_deleted = models.BooleanField(default=False)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Project Stage Note Comment"
        verbose_name_plural = "Project Stage Note Comments"
        ordering = ['created_at']
    
    def save(self, *args, **kwargs):
        """Cache author info on save for GDPR compliance"""
        if self.author and not self.is_author_deleted:
            if not self.author_name:
                if hasattr(self.author, 'profile'):
                    self.author_name = f"{self.author.profile.first_name} {self.author.profile.last_name}".strip()
                elif hasattr(self.author, 'user_profile'):
                    self.author_name = f"{self.author.user_profile.first_name} {self.author.user_profile.last_name}".strip()
            if not self.author_email:
                self.author_email = self.author.email
            if not self.author_role:
                if hasattr(self.author, 'profile') and self.author.profile.role == 'mentor':
                    self.author_role = 'mentor'
                elif hasattr(self.author, 'user_profile'):
                    self.author_role = 'client'
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Comment by {self.author_name or 'Unknown'} on {self.note.stage.title}"


class ProjectNote(models.Model):
    """Notes on projects (project-level, not stage-level)"""
    ROLE_CHOICES = [
        ('mentor', 'Mentor'),
        ('client', 'Client'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey("accounts.CustomUser", on_delete=models.SET_NULL, null=True, blank=True)
    author_name = models.CharField(max_length=200, blank=True)
    author_email = models.EmailField(blank=True)
    author_role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True)
    is_author_deleted = models.BooleanField(default=False)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Project Note"
        verbose_name_plural = "Project Notes"
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        """Cache author info on save for GDPR compliance"""
        if self.author and not self.is_author_deleted:
            if not self.author_name:
                if hasattr(self.author, 'profile'):
                    self.author_name = f"{self.author.profile.first_name} {self.author.profile.last_name}".strip()
                elif hasattr(self.author, 'user_profile'):
                    self.author_name = f"{self.author.user_profile.first_name} {self.author.user_profile.last_name}".strip()
            if not self.author_email:
                self.author_email = self.author.email
            if not self.author_role:
                if hasattr(self.author, 'profile') and self.author.profile.role == 'mentor':
                    self.author_role = 'mentor'
                elif hasattr(self.author, 'user_profile'):
                    self.author_role = 'client'
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.project.title} - Note by {self.author_name or 'Unknown'}"


class Task(models.Model):
    """Tasks for projects, stages, and backlogs"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Not Activated'),
        ('active', 'Activated'),
        ('in_progress', 'In Progress'),
        ('review', 'Review'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]
    
    ROLE_CHOICES = [
        ('mentor', 'Mentor'),
        ('client', 'Client'),
    ]
    
    # Basic fields
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    completed = models.BooleanField(default=False)  # Explicit completion flag
    deadline = models.DateField(blank=True, null=True)  # Task deadline
    created_at = models.DateTimeField(auto_now_add=True)  # Date of creation
    
    # Lifecycle timestamps - track task progression through different stages
    moved_to_active_backlog_at = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="Timestamp when task was moved to user's active backlog"
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when task was marked as completed"
    )
    reviewed_by_mentor_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when task was reviewed by mentor"
    )
    reviewed_by_mentor = models.ForeignKey(
        "accounts.MentorProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_tasks",
        help_text="Mentor who reviewed this task"
    )
    
    # Location fields (task can be in one of three places)
    stage = models.ForeignKey(ProjectStage, on_delete=models.CASCADE, related_name="backlog_tasks", null=True, blank=True)
    user_active_backlog = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE, related_name="active_backlog_tasks", null=True, blank=True)
    mentor_backlog = models.ForeignKey("accounts.MentorProfile", on_delete=models.CASCADE, related_name="mentor_backlog_tasks", null=True, blank=True)
    
    # Project connection (for tasks linked to projects/stages even when in mentor backlog)
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_tasks",
        help_text="Project this task is linked to (optional, for tasks in mentor backlog)"
    )
    
    # Assignment fields (for tasks assigned from stage to client)
    assigned = models.BooleanField(default=False)  # True if assigned to client's active backlog
    assigned_to = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
        help_text="Client this task is assigned to (for future multi-client projects)"
    )
    
    # Additional fields
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    due_date = models.DateField(blank=True, null=True)  # Alternative deadline field (can use deadline instead)
    estimated_duration = models.IntegerField(blank=True, null=True)
    depends_on = models.ManyToManyField('self', symmetrical=False, blank=True, related_name="blocked_by")
    order = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_by = models.ForeignKey("accounts.CustomUser", on_delete=models.SET_NULL, null=True, blank=True)
    author_name = models.CharField(max_length=200, blank=True)
    author_email = models.EmailField(blank=True)
    author_role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True)
    is_author_deleted = models.BooleanField(default=False)
    is_ai_generated = models.BooleanField(default=False)
    ai_confidence = models.FloatField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Task"
        verbose_name_plural = "Tasks"
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['stage', 'order']),
            models.Index(fields=['user_active_backlog', 'order']),
            models.Index(fields=['mentor_backlog', 'order']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['assigned', 'assigned_to']),
        ]
    
    def clean(self):
        """
        Validate task location.
        Tasks can be:
        - In stage only (pending)
        - In stage AND user_active_backlog (active - activated from stage)
        - In user_active_backlog only (created directly in active backlog)
        - In mentor_backlog only
        But NOT in multiple backlogs (mentor_backlog + user_active_backlog)
        """
        locations = [self.stage, self.user_active_backlog, self.mentor_backlog]
        non_null_locations = sum(1 for loc in locations if loc is not None)
        
        # Allow: stage only, user_active_backlog only, mentor_backlog only, or stage + user_active_backlog
        if non_null_locations == 0:
            raise ValidationError("Task must be in at least one location: stage, user_active_backlog, or mentor_backlog")
        elif non_null_locations > 2:
            raise ValidationError("Task cannot be in more than 2 locations")
        elif self.mentor_backlog and self.user_active_backlog:
            raise ValidationError("Task cannot be in both mentor_backlog and user_active_backlog")
        elif self.mentor_backlog and self.stage:
            raise ValidationError("Task cannot be in both mentor_backlog and stage")
    
    def save(self, *args, **kwargs):
        """Cache author info and validate location"""
        # Cache author info for GDPR compliance
        if self.created_by and not self.is_author_deleted:
            if not self.author_name:
                if hasattr(self.created_by, 'profile'):
                    self.author_name = f"{self.created_by.profile.first_name} {self.created_by.profile.last_name}".strip()
                elif hasattr(self.created_by, 'user_profile'):
                    self.author_name = f"{self.created_by.user_profile.first_name} {self.created_by.user_profile.last_name}".strip()
            if not self.author_email:
                self.author_email = self.created_by.email
            if not self.author_role:
                if hasattr(self.created_by, 'profile') and self.created_by.profile.role == 'mentor':
                    self.author_role = 'mentor'
                elif hasattr(self.created_by, 'user_profile'):
                    self.author_role = 'client'
        
        # Validate location
        self.clean()
        super().save(*args, **kwargs)
    
    def activate_task(self, user_profile):
        """
        Activate a stage task - adds it to client's active backlog.
        Task remains in stage backlog but also appears in active backlog.
        Sets status to 'active' and user_active_backlog FK.
        """
        if not self.stage:
            raise ValidationError("Only stage tasks can be activated")
        
        if self.user_active_backlog == user_profile:
            return  # Already activated
        
        self.user_active_backlog = user_profile
        self.status = 'active'
        from django.utils import timezone
        if not self.moved_to_active_backlog_at:
            self.moved_to_active_backlog_at = timezone.now()
        self.save()
    
    def deactivate_task(self):
        """
        Deactivate a task - removes it from active backlog.
        Task remains in stage backlog.
        Removes user_active_backlog FK and sets status back to 'pending'.
        """
        if not self.user_active_backlog:
            return  # Not activated
        
        self.user_active_backlog = None
        if self.status == 'active':
            self.status = 'pending'
        # Keep moved_to_active_backlog_at for history
        self.save()
    
    def move_to_active_backlog(self, user_profile):
        """
        Move task to user's active backlog (for tasks created directly in active backlog).
        Sets moved_to_active_backlog_at timestamp.
        """
        if self.user_active_backlog == user_profile:
            return  # Already in active backlog
        
        self.user_active_backlog = user_profile
        self.stage = None  # Remove from stage if it was there
        self.mentor_backlog = None  # Remove from mentor backlog if it was there
        self.moved_to_active_backlog_at = timezone.now()
        self.save()
    
    def complete_activated_task(self, user_profile):
        """
        When client completes an activated task from stage:
        - Remove from active backlog (user_active_backlog = None)
        - Mark as completed
        - Keep task in stage backlog
        - Set completed_at timestamp
        """
        if not self.user_active_backlog or self.user_active_backlog != user_profile:
            raise ValidationError("Task is not activated for this client")
        
        self.user_active_backlog = None  # Remove from active backlog
        self.completed = True
        self.status = 'completed'
        if not self.completed_at:
            from django.utils import timezone
            self.completed_at = timezone.now()
        self.save()
    
    def complete_active_backlog_task(self):
        """
        When client completes a task originally created in active backlog:
        - Keep it in active backlog
        - Mark as completed
        - Set completed_at timestamp
        """
        if not self.user_active_backlog:
            raise ValidationError("Task is not in active backlog")
        
        self.completed = True
        self.status = 'completed'
        if not self.completed_at:
            from django.utils import timezone
            self.completed_at = timezone.now()
        self.save()
    
    def mark_as_reviewed(self, mentor_profile):
        """
        Mark task as reviewed by mentor.
        Sets reviewed_by_mentor_at timestamp and reviewed_by_mentor.
        """
        self.reviewed_by_mentor = mentor_profile
        self.reviewed_by_mentor_at = timezone.now()
        self.save()
    
    def archive_task(self):
        """
        Archive a completed task.
        Moves task to history by setting status to 'archived'.
        Only works on completed tasks.
        """
        if not self.completed:
            raise ValidationError("Only completed tasks can be archived")
        
        self.status = 'archived'
        self.save()
    
    def __str__(self):
        return self.title