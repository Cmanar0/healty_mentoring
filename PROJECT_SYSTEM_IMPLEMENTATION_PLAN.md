# Project System Implementation Plan

**Status:** Planning Phase  
**Last Updated:** 2025-01-XX  
**Version:** 1.0

---

## Table of Contents

1. [Overview](#overview)
2. [Database Models](#database-models)
3. [Implementation Phases](#implementation-phases)
4. [API Endpoints](#api-endpoints)
5. [UI/UX Requirements](#uiux-requirements)
6. [GDPR Compliance](#gdpr-compliance)
7. [AI Integration Preparation](#ai-integration-preparation)
8. [Implementation Checklist](#implementation-checklist)

---

## Overview

This document outlines the complete implementation plan for an enhanced project management system that includes:

- **Modular Projects**: Projects with attachable modules (Financial Planning, Real World Validation, etc.)
- **Questionnaire System**: Template-based questionnaires for project initialization
- **Stage Management**: Multi-stage project plans with dependencies
- **Task Management**: Stage backlogs and user active backlogs
- **Project Assignment Flow**: Mentor creates → Client accepts workflow
- **AI Integration Ready**: Prepared structure for AI-powered stage and task generation

### Key Features

1. **Modular Architecture**: Projects can have multiple modules attached
2. **Template System**: Predefined project templates with custom questionnaires and stages
3. **Questionnaire Flow**: Mandatory questionnaire completion after project creation
4. **Stage Planning**: Visual waterfall/timeline of project stages
5. **Task Backlogs**: Stage-specific backlogs and user active backlogs
6. **Assignment Workflow**: Email-based project assignment and acceptance
7. **GDPR Compliant**: Proper handling of deleted user accounts

---

## Database Models

### 1. Enhanced Project Model

**File:** `dashboard_user/models.py`

```python
class Project(models.Model):
    # Basic Fields
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Relationships
    template = models.ForeignKey(ProjectTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    project_owner = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    supervised_by = models.ForeignKey(MentorProfile, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Assignment Flow
    assignment_status = models.CharField(max_length=20, choices=[...], default='pending')
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
```

**Status:** ⬜ Not Started

---

### 2. ProjectModule Model

**File:** `dashboard_user/models.py`

```python
class ProjectModule(models.Model):
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
```

**Status:** ⬜ Not Started

---

### 3. ProjectModuleInstance Model

**File:** `dashboard_user/models.py`

```python
class ProjectModuleInstance(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="module_instances")
    module = models.ForeignKey(ProjectModule, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    module_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['project', 'module']
        ordering = ['order']
```

**Status:** ⬜ Not Started

---

### 4. ProjectQuestionnaire Model

**File:** `dashboard_user/models.py`

```python
class ProjectQuestionnaire(models.Model):
    QUESTION_TYPES = [
        ('text', 'Text'),
        ('textarea', 'Long Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('select', 'Select'),
        ('multiselect', 'Multiple Select'),
    ]
    
    template = models.ForeignKey(ProjectTemplate, on_delete=models.CASCADE, related_name="questions", null=True, blank=True)
    question_text = models.CharField(max_length=500)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='text')
    is_required = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    options = models.JSONField(default=list, blank=True)
    help_text = models.TextField(blank=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ['template', 'order']
```

**Status:** ⬜ Not Started

---

### 5. ProjectQuestionnaireAnswer Model

**File:** `dashboard_user/models.py`

```python
class ProjectQuestionnaireAnswer(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="questionnaire_answers")
    question = models.ForeignKey(ProjectQuestionnaire, on_delete=models.CASCADE)
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['project', 'question']
        ordering = ['question__order']
```

**Status:** ⬜ Not Started

---

### 6. ProjectStage Model

**File:** `dashboard_user/models.py`

```python
class ProjectStage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="stages")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    target_date = models.DateField(blank=True, null=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    completed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    depends_on = models.ManyToManyField('self', symmetrical=False, blank=True, related_name="blocks")
    created_from_template = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['project', 'order']),
        ]
```

**Status:** ⬜ Not Started

---

### 7. ProjectStageTemplate Model

**File:** `dashboard_user/models.py`

```python
class ProjectStageTemplate(models.Model):
    template = models.ForeignKey(ProjectTemplate, on_delete=models.CASCADE, related_name="stage_templates")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    default_target_date_offset = models.IntegerField(blank=True, null=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ['template', 'order']
```

**Status:** ⬜ Not Started

---

### 8. ProjectStageNote Model

**File:** `dashboard_user/models.py`

```python
class ProjectStageNote(models.Model):
    stage = models.ForeignKey(ProjectStage, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    author_name = models.CharField(max_length=200, blank=True)
    author_email = models.EmailField(blank=True)
    author_role = models.CharField(max_length=20, choices=[('mentor', 'Mentor'), ('client', 'Client')], blank=True)
    is_author_deleted = models.BooleanField(default=False)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
```

**Status:** ⬜ Not Started

---

### 9. ProjectStageNoteAttachment Model

**File:** `dashboard_user/models.py`

```python
class ProjectStageNoteAttachment(models.Model):
    note = models.ForeignKey(ProjectStageNote, on_delete=models.CASCADE, related_name="attachments")
    image = models.ImageField(upload_to='project_stages/attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
```

**Status:** ⬜ Not Started

---

### 10. ProjectStageNoteComment Model

**File:** `dashboard_user/models.py`

```python
class ProjectStageNoteComment(models.Model):
    note = models.ForeignKey(ProjectStageNote, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    author_name = models.CharField(max_length=200, blank=True)
    author_email = models.EmailField(blank=True)
    author_role = models.CharField(max_length=20, choices=[('mentor', 'Mentor'), ('client', 'Client')], blank=True)
    is_author_deleted = models.BooleanField(default=False)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
```

**Status:** ⬜ Not Started

---

### 11. Task Model

**File:** `dashboard_user/models.py`

```python
class Task(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('review', 'Review'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic fields
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    completed = models.BooleanField(default=False)  # Explicit completion flag
    deadline = models.DateField(blank=True, null=True)  # Task deadline
    created_at = models.DateTimeField(auto_now_add=True)  # Date of creation
    
    # Location fields (task can be in one of three places)
    stage = models.ForeignKey(ProjectStage, on_delete=models.CASCADE, related_name="backlog_tasks", null=True, blank=True)
    user_active_backlog = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="active_backlog_tasks", null=True, blank=True)
    mentor_backlog = models.ForeignKey('accounts.MentorProfile', on_delete=models.CASCADE, related_name="mentor_backlog_tasks", null=True, blank=True)
    
    # Assignment fields (for tasks assigned from stage to client)
    assigned = models.BooleanField(default=False)  # True if assigned to client's active backlog
    assigned_to = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tasks", help_text="Client this task is assigned to (for future multi-client projects)")
    
    # Additional fields
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    due_date = models.DateField(blank=True, null=True)  # Alternative deadline field (can use deadline instead)
    estimated_duration = models.IntegerField(blank=True, null=True)
    depends_on = models.ManyToManyField('self', symmetrical=False, blank=True, related_name="blocked_by")
    order = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    author_name = models.CharField(max_length=200, blank=True)
    author_email = models.EmailField(blank=True)
    author_role = models.CharField(max_length=20, choices=[('mentor', 'Mentor'), ('client', 'Client')], blank=True)
    is_author_deleted = models.BooleanField(default=False)
    is_ai_generated = models.BooleanField(default=False)
    ai_confidence = models.FloatField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['stage', 'order']),
            models.Index(fields=['user_active_backlog', 'order']),
            models.Index(fields=['mentor_backlog', 'order']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['assigned', 'assigned_to']),
        ]
    
    def clean(self):
        """Validate that task is in exactly one location"""
        locations = [self.stage, self.user_active_backlog, self.mentor_backlog]
        if sum(1 for loc in locations if loc is not None) != 1:
            raise ValidationError("Task must be in exactly one location: stage, user_active_backlog, or mentor_backlog")
    
    def assign_to_client(self, user_profile):
        """
        Assign a stage task to client's active backlog.
        Task remains in stage backlog but is marked as assigned.
        """
        if not self.stage:
            raise ValidationError("Only stage tasks can be assigned to clients")
        
        self.assigned = True
        self.assigned_to = user_profile
        # Create a copy in client's active backlog (or link to same task - depends on implementation)
        # For now, we'll keep it in stage and just mark as assigned
        self.save()
    
    def unassign_from_client(self):
        """
        Unassign task from client when completed.
        Keeps assignment history but marks as unassigned.
        """
        self.assigned = False
        # Keep assigned_to for history
        self.save()
    
    def complete_assigned_task(self, user_profile):
        """
        When client completes an assigned task from stage:
        - Unassign it (assigned=False)
        - Mark as completed in stage backlog
        - Keep assignment history (assigned_to remains)
        """
        if not self.assigned or self.assigned_to != user_profile:
            raise ValidationError("Task is not assigned to this client")
        
        self.assigned = False
        self.completed = True
        self.status = 'completed'
        self.save()
    
    def complete_active_backlog_task(self):
        """
        When client completes a task originally in active backlog:
        - Keep it in active backlog
        - Mark as completed
        """
        if not self.user_active_backlog:
            raise ValidationError("Task is not in active backlog")
        
        self.completed = True
        self.status = 'completed'
        self.save()
```

**Status:** ⬜ Not Started

**Important Notes:**
- Tasks can be created in three locations: stage backlog, client active backlog, or mentor backlog
- Tasks do NOT move between backlogs - they remain in their original location
- Stage tasks can be assigned to client's active backlog (assigned=True, assigned_to set)
- When assigned task is completed by client: unassigns (assigned=False) and marks complete in stage backlog
- When active backlog task is completed: stays in active backlog and is marked complete
- Mentor backlog is for mentor's personal tasks
- `assigned_to` field is for future multi-client project support

---

### 12. Enhanced ProjectTemplate Model

**File:** `dashboard_user/models.py`

**Add fields:**
```python
has_default_questions = models.BooleanField(
    default=True,
    help_text="Use default questions if no template-specific questions exist"
)
```

**Status:** ⬜ Not Started

---

## Implementation Phases

### Phase 1: Database Foundation ⬜

**Goal:** Create all database models and migrations

**Tasks:**
- [ ] Update `Project` model with new fields
- [ ] Create `ProjectModule` model
- [ ] Create `ProjectModuleInstance` model
- [ ] Create `ProjectQuestionnaire` model
- [ ] Create `ProjectQuestionnaireAnswer` model
- [ ] Create `ProjectStage` model
- [ ] Create `ProjectStageTemplate` model
- [ ] Create `ProjectStageNote` model
- [ ] Create `ProjectStageNoteAttachment` model
- [ ] Create `ProjectStageNoteComment` model
- [ ] Create `Task` model
- [ ] Update `ProjectTemplate` model
- [ ] Create and run migrations
- [ ] Test model relationships

**Estimated Time:** 2-3 hours

---

### Phase 2: Project Assignment Flow ⬜

**Goal:** Implement mentor creates → client accepts workflow with secure email links

**Tasks:**
- [ ] Update `create_project` view to set `created_by` and `assignment_status`
- [ ] Create `assign_project_to_client` view
- [ ] Create secure link handler `accept_project_assignment_secure` (with logout/login logic)
- [ ] Create `accept_project_assignment` view (after authentication)
- [ ] Create email template for project assignment with secure link
- [ ] Add `send_project_assignment_email` to EmailService
- [ ] Generate assignment tokens with uidb64 and token (like review emails)
- [ ] Create URL patterns for assignment flow
- [ ] Add "Projects" button to user dashboard sidebar menu
- [ ] Add pending assignments badge to Projects menu item (red circle with count)
- [ ] Create user projects list page (`dashboard_user/projects_list`)
- [ ] Display pending assignments at top of projects list page
- [ ] Add accept/reject buttons for pending assignments
- [ ] Update context processor or base template to show pending assignments count
- [ ] Test assignment workflow with secure links

**Estimated Time:** 4-5 hours

---

### Phase 3: Questionnaire System ⬜

**Goal:** Template-based questionnaire with mandatory completion

**Tasks:**
- [ ] Create default template questions
- [ ] Create template-specific questions system
- [ ] Create questionnaire form view
- [ ] Create questionnaire display view (read-only after completion)
- [ ] Update project detail page to show questionnaire section
- [ ] Add questionnaire completion validation
- [ ] Save questionnaire answers
- [ ] Mark questionnaire as completed
- [ ] Test questionnaire flow

**Estimated Time:** 3-4 hours

---

### Phase 4: Module System ⬜

**Goal:** Allow modules to be added/removed from projects

**Tasks:**
- [ ] Create initial ProjectModule instances (seed data)
- [ ] Update create project modal to include module selection
- [ ] Create module selection UI component
- [ ] Save selected modules on project creation
- [ ] Create "Manage Modules" view for existing projects
- [ ] Add/remove modules from project
- [ ] Display active modules on project detail page
- [ ] Create module-specific UI placeholders
- [ ] Test module system

**Estimated Time:** 3-4 hours

---

### Phase 5: Stage Templates ⬜

**Goal:** Predefined stages per template

**Tasks:**
- [ ] Create `ProjectStageTemplate` instances for templates
- [ ] Create function to copy stage templates to project
- [ ] Auto-create stages when project is created from template
- [ ] Test stage template copying

**Estimated Time:** 1-2 hours

---

### Phase 6: Stage Management ⬜

**Goal:** Create, edit, delete, and reorder stages

**Tasks:**
- [ ] Create stage creation view
- [ ] Create stage edit view
- [ ] Create stage deletion view
- [ ] Implement drag-and-drop reordering
- [ ] Update order field on reorder
- [ ] Create stage dependencies UI
- [ ] Mark stages as completed
- [ ] Display stages in waterfall/timeline view
- [ ] Test stage management

**Estimated Time:** 4-5 hours

---

### Phase 7: Stage Notes & Comments ⬜

**Goal:** Notes with attachments and comments

**Tasks:**
- [ ] Create note creation view
- [ ] Create note edit view
- [ ] Create note deletion view
- [ ] Implement image upload for attachments
- [ ] Create comment system for notes
- [ ] Display notes with attachments
- [ ] Display comments on notes
- [ ] Test notes and comments

**Estimated Time:** 3-4 hours

---

### Phase 8: Task Management ⬜

**Goal:** Implement task system with stage, active, and mentor backlogs

**Tasks:**
- [ ] Create task CRUD views (create, update, delete)
- [ ] Create task assignment logic (assign from stage to client, task stays in stage)
- [ ] Implement task completion logic:
  - [ ] Complete assigned task: unassign and mark complete in stage
  - [ ] Complete active backlog task: mark complete in active backlog
  - [ ] Complete mentor backlog task: mark complete in mentor backlog
- [ ] Create stage backlog UI
- [ ] Create client active backlog UI
- [ ] Create mentor backlog UI
- [ ] Implement task reordering within each backlog
- [ ] Display task assignment status
- [ ] Display task dependencies
- [ ] Add mentor backlog to mentor dashboard
- [ ] Test task management and assignment flow

**Estimated Time:** 5-6 hours

---

### Phase 9: AI Integration Preparation ⬜

**Goal:** Mock AI service structure and endpoints

**Tasks:**
- [ ] Create `ProjectAIService` class with mock methods
- [ ] Create `generate_stages_ai` view endpoint
- [ ] Create `generate_tasks_ai` view endpoint
- [ ] Document expected API structure
- [ ] Create UI for AI suggestions
- [ ] Implement suggestion acceptance flow
- [ ] Add comments for future AI integration

**Estimated Time:** 2-3 hours

---

### Phase 10: UI/UX Implementation ⬜

**Goal:** Complete user interface

**Tasks:**
- [ ] Update projects list page with "Create New Project" button
- [ ] Update project detail page layout
- [ ] Create questionnaire form UI
- [ ] Create stages waterfall/timeline visualization
- [ ] Create stage management UI
- [ ] Create module selection UI
- [ ] Create task backlog UI
- [ ] Create active backlog UI
- [ ] Add loading states and error handling
- [ ] Test complete user flow

**Estimated Time:** 6-8 hours

---

### Phase 11: GDPR Compliance ⬜

**Goal:** Handle deleted user accounts properly

**Tasks:**
- [ ] Create signal handler for user deletion
- [ ] Update tasks, notes, comments on user deletion
- [ ] Cache author info on save for all models
- [ ] Display "Deleted Account" in UI
- [ ] Create admin anonymization page
- [ ] Add anonymization view and endpoint
- [ ] Create anonymization template with email selector
- [ ] Add "GDPR Anonymization" to admin sidebar menu
- [ ] Implement email search/select functionality
- [ ] Add confirmation modal for anonymization
- [ ] Display anonymization results
- [ ] Test GDPR compliance and anonymization

**Estimated Time:** 2-3 hours

---

## API Endpoints

### Project Management

**Mentor Endpoints:**
- `POST /dashboard/mentor/projects/create/` - Create new project
- `GET /dashboard/mentor/projects/` - List projects
- `GET /dashboard/mentor/projects/<id>/` - Project detail
- `POST /dashboard/mentor/projects/<id>/assign/` - Assign project to client
- `POST /dashboard/mentor/projects/<id>/change-supervisor/` - Change supervisor

**User/Client Endpoints:**
- `GET /dashboard/user/projects/` - List user's projects
- `GET /dashboard/user/projects/<id>/` - Project detail (user view)
- `GET /dashboard/user/projects/accept/<uidb64>/<token>/` - Secure link handler (with logout/login)
- `POST /dashboard/user/projects/<id>/accept/` - Accept project assignment (after auth)
- `POST /dashboard/user/projects/<id>/reject/` - Reject project assignment

### Questionnaire

- `GET /dashboard/mentor/projects/<id>/questionnaire/` - Get questionnaire form
- `POST /dashboard/mentor/projects/<id>/questionnaire/` - Submit questionnaire
- `GET /dashboard/mentor/projects/<id>/questionnaire/answers/` - View answers

### Modules

- `GET /dashboard/mentor/projects/<id>/modules/` - Get project modules
- `POST /dashboard/mentor/projects/<id>/modules/add/` - Add module
- `POST /dashboard/mentor/projects/<id>/modules/<module_id>/remove/` - Remove module

### Stages

- `GET /dashboard/mentor/projects/<id>/stages/` - List stages
- `POST /dashboard/mentor/projects/<id>/stages/create/` - Create stage
- `POST /dashboard/mentor/projects/<id>/stages/<stage_id>/update/` - Update stage
- `POST /dashboard/mentor/projects/<id>/stages/<stage_id>/delete/` - Delete stage
- `POST /dashboard/mentor/projects/<id>/stages/reorder/` - Reorder stages
- `POST /dashboard/mentor/projects/<id>/stages/<stage_id>/complete/` - Mark complete

### Stage Notes

- `GET /dashboard/mentor/stages/<stage_id>/notes/` - List notes
- `POST /dashboard/mentor/stages/<stage_id>/notes/create/` - Create note
- `POST /dashboard/mentor/stages/<stage_id>/notes/<note_id>/update/` - Update note
- `POST /dashboard/mentor/stages/<stage_id>/notes/<note_id>/delete/` - Delete note
- `POST /dashboard/mentor/stages/<stage_id>/notes/<note_id>/comments/create/` - Add comment

### Tasks

**Stage Backlog:**
- `GET /dashboard/mentor/stages/<stage_id>/tasks/` - List stage backlog tasks
- `POST /dashboard/mentor/stages/<stage_id>/tasks/create/` - Create task in stage backlog
- `POST /dashboard/mentor/tasks/<task_id>/assign-to-client/<user_id>/` - Assign stage task to client's active backlog (task stays in stage)

**Client Active Backlog:**
- `GET /dashboard/user/active-backlog/` - Get user active backlog
- `POST /dashboard/user/active-backlog/tasks/create/` - Create task directly in active backlog
- `POST /dashboard/user/tasks/<task_id>/complete/` - Complete task (handles both assigned and active backlog tasks)

**Mentor Backlog:**
- `GET /dashboard/mentor/backlog/` - Get mentor's own backlog
- `POST /dashboard/mentor/backlog/tasks/create/` - Create task in mentor backlog
- `POST /dashboard/mentor/tasks/<task_id>/update/` - Update task
- `POST /dashboard/mentor/tasks/<task_id>/delete/` - Delete task
- `POST /dashboard/mentor/tasks/<task_id>/complete/` - Complete mentor task

**Task Management:**
- `POST /dashboard/mentor/tasks/reorder/` - Reorder tasks within backlog

### AI Integration

- `POST /dashboard/mentor/projects/<id>/generate-stages/` - Generate stage suggestions
- `POST /dashboard/mentor/stages/<stage_id>/generate-tasks/` - Generate task suggestions

---

## UI/UX Requirements

### Projects List Pages

**Mentor Projects List Page:**
- [ ] Add "Create New Project" button (top right, same row as H1)
- [ ] Button opens existing create project modal
- [ ] Filter by client dropdown (existing)
- [ ] Display assigned/unassigned sections (existing)

**User Projects List Page:**
- [ ] Display pending assignments section at top
- [ ] Show accept/reject buttons for pending assignments
- [ ] Display accepted projects section
- [ ] Display user's own projects section (no supervisor)
- [ ] Each project row clickable to project detail
- [ ] Show project status badges
- [ ] Show mentor name for supervised projects

**User Dashboard Sidebar Menu:**
- [ ] Add "Projects" menu item (after "Your Mentors" or before "Your Profile")
- [ ] Add red badge circle with pending assignments count (like Sessions badge)
- [ ] Use `sidebar-icon-with-badge` class and `sidebar-badge` span
- [ ] Link to `/dashboard/user/projects/`
- [ ] Show active state when on projects pages

### Project Detail Page

**Layout Structure:**
1. **Header Section**
   - Project title, icon, badges
   - Back button
   - Status indicators

2. **Questionnaire Section**
   - If not completed: Show form (mandatory)
   - If completed: Show read-only answers with "Edit" option
   - Progress indicator

3. **Project Overview**
   - Goal, timeline, current status
   - Target completion date

4. **Modules Section**
   - Active modules display
   - Add/Remove modules button
   - Module-specific content areas

5. **Stages Section**
   - Waterfall/Timeline visualization
   - List of stages (collapsible/accordion)
   - Add/Edit/Delete stage buttons
   - Stage completion checkboxes
   - Dependencies visualization

6. **Stage Details (Expandable)**
   - Stage notes with attachments
   - Comments on notes
   - Stage backlog tasks
   - Assign tasks to client's active backlog (task remains in stage)

### Stage Visualization Options

**Recommended:** Horizontal timeline with:
- Stages as cards/boxes
- Connecting lines showing flow
- Color coding for completion status
- Dependencies shown with arrows
- Scrollable if many stages

### Task Management UI

**Stage Backlog:**
- List of tasks for the stage
- Drag-and-drop reordering
- Priority indicators
- Status badges
- Completion status
- "Assign to Client" button (assigns to client's active backlog, task stays in stage)
- Shows which tasks are assigned (assigned=True) and to whom

**Client Active Backlog:**
- Tasks originally created in active backlog
- Tasks assigned from stage backlogs (shows source stage)
- Grouped by source stage (optional)
- Quick actions (complete, edit)
- When completing assigned task: unassigns and marks complete in stage backlog
- When completing original active backlog task: marks complete in active backlog

**Mentor Backlog:**
- Mentor's own tasks (for mentor's personal use)
- Similar structure to stage/active backlogs
- Can be assigned to clients in future (assigned_to field ready)
- Full CRUD operations

---

## GDPR Compliance

### Approach

**When User Account is Deleted:**

1. **Keep all content** (projects, stages, tasks, notes, comments)
2. **Set ForeignKey to NULL** (`created_by`, `author`, etc.)
3. **Mark as deleted** (`is_author_deleted=True`)
4. **Keep cached info** (author_name, author_email, author_role)
5. **Display as "Deleted Account"** in UI

**Signal Handler:**
```python
@receiver(pre_delete, sender=CustomUser)
def handle_user_deletion(sender, instance, **kwargs):
    # Mark tasks
    Task.objects.filter(created_by=instance).update(
        is_author_deleted=True,
        created_by=None
    )
    
    # Mark stage notes
    ProjectStageNote.objects.filter(author=instance).update(
        is_author_deleted=True,
        author=None
    )
    
    # Mark note comments
    ProjectStageNoteComment.objects.filter(author=instance).update(
        is_author_deleted=True,
        author=None
    )
```

**When Supervisor is Removed:**
- Keep all content (stages, notes, comments, tasks)
- Only change `supervised_by` to NULL
- All content remains accessible

**UI Display:**
- Show "Deleted Account" or "Unknown User" instead of author name
- Keep author role visible if cached
- Maintain context of who created what

### Admin Anonymization Page

**Purpose:** Allow admins to manually trigger GDPR anonymization for deleted users by email.

**Email Availability:**
- Emails are cached in `author_email` fields across all models (Task, ProjectStageNote, ProjectStageNoteComment)
- Even after user deletion, emails remain accessible via cached fields
- Admin can search and select users by email from cached data

**Implementation:**

**File:** `dashboard_admin/views.py`

```python
@login_required
@admin_required
def gdpr_anonymization(request):
    """
    Admin page for GDPR anonymization.
    Allows selecting a user by email and anonymizing their cached data.
    
    This page displays:
    - Email search/select dropdown (includes cached emails from deleted users)
    - Preview of items that will be anonymized
    - Confirmation before anonymization
    - Results after anonymization
    """
    from dashboard_user.models import Task, ProjectStageNote, ProjectStageNoteComment
    from accounts.models import CustomUser
    
    # Get all unique emails from cached fields
    task_emails = Task.objects.exclude(author_email='').values_list('author_email', flat=True).distinct()
    note_emails = ProjectStageNote.objects.exclude(author_email='').values_list('author_email', flat=True).distinct()
    comment_emails = ProjectStageNoteComment.objects.exclude(author_email='').values_list('author_email', flat=True).distinct()
    
    all_emails = set(list(task_emails) + list(note_emails) + list(comment_emails))
    
    # Also include active users
    active_user_emails = CustomUser.objects.values_list('email', flat=True)
    all_emails.update(active_user_emails)
    
    # Get selected email from query param (if previewing)
    selected_email = request.GET.get('email', '').strip()
    preview_stats = None
    
    if selected_email:
        # Get preview stats
        preview_stats = {
            'tasks': Task.objects.filter(author_email=selected_email).count(),
            'notes': ProjectStageNote.objects.filter(author_email=selected_email).count(),
            'comments': ProjectStageNoteComment.objects.filter(author_email=selected_email).count(),
        }
        preview_stats['total'] = preview_stats['tasks'] + preview_stats['notes'] + preview_stats['comments']
    
    context = {
        'available_emails': sorted(all_emails),
        'selected_email': selected_email,
        'preview_stats': preview_stats,
    }
    
    return render(request, 'dashboard_admin/gdpr_anonymization.html', context)

@login_required
@admin_required
def search_email_for_anonymization(request):
    """
    AJAX endpoint to search for emails (for dropdown).
    Returns both active users and cached emails from deleted users.
    """
    query = request.GET.get('q', '').strip().lower()
    
    from dashboard_user.models import Task, ProjectStageNote, ProjectStageNoteComment
    from accounts.models import CustomUser
    
    emails = set()
    
    # Search in active users
    if query:
        active_emails = CustomUser.objects.filter(email__icontains=query).values_list('email', flat=True)
        emails.update(active_emails)
        
        # Search in cached emails
        task_emails = Task.objects.filter(author_email__icontains=query).exclude(author_email='').values_list('author_email', flat=True).distinct()
        note_emails = ProjectStageNote.objects.filter(author_email__icontains=query).exclude(author_email='').values_list('author_email', flat=True).distinct()
        comment_emails = ProjectStageNoteComment.objects.filter(author_email__icontains=query).exclude(author_email='').values_list('author_email', flat=True).distinct()
        
        emails.update(task_emails)
        emails.update(note_emails)
        emails.update(comment_emails)
    else:
        # Return all emails if no query
        active_emails = CustomUser.objects.values_list('email', flat=True)
        task_emails = Task.objects.exclude(author_email='').values_list('author_email', flat=True).distinct()
        note_emails = ProjectStageNote.objects.exclude(author_email='').values_list('author_email', flat=True).distinct()
        comment_emails = ProjectStageNoteComment.objects.exclude(author_email='').values_list('author_email', flat=True).distinct()
        
        emails.update(active_emails)
        emails.update(task_emails)
        emails.update(note_emails)
        emails.update(comment_emails)
    
    return JsonResponse({
        'success': True,
        'emails': sorted(list(emails))[:50]  # Limit to 50 results
    })

@login_required
@admin_required
@require_POST
def anonymize_user_data(request):
    """
    Anonymize all cached data for a user by email.
    This is an irreversible action for GDPR compliance.
    """
    email = request.POST.get('email', '').strip()
    
    if not email:
        return JsonResponse({'success': False, 'error': 'Email is required'}, status=400)
    
    from dashboard_user.models import Task, ProjectStageNote, ProjectStageNoteComment
    
    # Get counts before anonymization (for preview/results)
    tasks_count = Task.objects.filter(author_email=email).count()
    notes_count = ProjectStageNote.objects.filter(author_email=email).count()
    comments_count = ProjectStageNoteComment.objects.filter(author_email=email).count()
    
    # Anonymize tasks
    tasks_updated = Task.objects.filter(author_email=email).update(
        author_name='[Anonymized]',
        author_email='',
        author_role=''
    )
    
    # Anonymize stage notes
    notes_updated = ProjectStageNote.objects.filter(author_email=email).update(
        author_name='[Anonymized]',
        author_email='',
        author_role=''
    )
    
    # Anonymize note comments
    comments_updated = ProjectStageNoteComment.objects.filter(author_email=email).update(
        author_name='[Anonymized]',
        author_email='',
        author_role=''
    )
    
    return JsonResponse({
        'success': True,
        'message': f'Successfully anonymized data for {email}',
        'stats': {
            'tasks': tasks_updated,
            'notes': notes_updated,
            'comments': comments_updated,
            'total': tasks_updated + notes_updated + comments_updated
        }
    })
```

**File:** `dashboard_admin/templates/dashboard_admin/gdpr_anonymization.html`

**Features:**
- Email search/select dropdown (searchable, includes cached emails from deleted users)
- Display preview stats (how many tasks, notes, comments will be anonymized)
- Confirmation modal before anonymization with warning
- Results display after anonymization (counts of anonymized items)
- Search functionality to find users by email (from both active users and cached data)

**UI Components:**
- Email selector dropdown with search
- Preview section showing affected items count
- "Anonymize" button (triggers confirmation modal)
- Results section (shown after anonymization)
- Warning messages about irreversible action

**URL Pattern:**
- `path('gdpr/anonymization/', views.gdpr_anonymization, name='gdpr_anonymization')`
- `path('gdpr/anonymize/', views.anonymize_user_data, name='anonymize_user_data')`
- `path('gdpr/search-email/', views.search_email_for_anonymization, name='search_email_anonymization')` (optional: AJAX endpoint)

**Menu Item:**
- Add to admin sidebar: "GDPR Anonymization" with shield/lock icon (`fa-shield-alt` or `fa-lock`)
- Position: After "Billing" or at the end of the menu

**Email Source:**
- Emails are cached in `author_email` fields in:
  - `Task.author_email`
  - `ProjectStageNote.author_email`
  - `ProjectStageNoteComment.author_email`
- Also includes active users from `CustomUser.email`
- Allows finding users even after account deletion

---

## AI Integration Preparation

### Service Structure

**File:** `dashboard_user/services.py`

```python
class ProjectAIService:
    """
    Service for AI-powered project stage and task generation.
    
    TODO: Replace with actual AI API integration
    
    Expected API Structure:
    - generate_stages(project_id, questionnaire_answers) -> List[StageSuggestion]
    - generate_tasks(stage_id, stage_context) -> List[TaskSuggestion]
    """
    
    @staticmethod
    def generate_stages(project_id, questionnaire_answers):
        """
        Expected response structure:
        [
            {
                'title': str,
                'description': str,
                'suggested_order': int,
                'target_date_offset': int,
                'dependencies': List[int],
                'confidence': float (0-1),
                'reasoning': str
            },
            ...
        ]
        """
        return []
    
    @staticmethod
    def generate_tasks(stage_id, stage_context):
        """
        Expected response structure:
        [
            {
                'title': str,
                'description': str,
                'priority': str,
                'estimated_duration': int,
                'due_date_offset': int,
                'dependencies': List[int],
                'confidence': float (0-1),
                'reasoning': str
            },
            ...
        ]
        """
        return []
```

### API Endpoints

**Generate Stages:**
- `POST /dashboard/mentor/projects/<id>/generate-stages/`
- Request: `{questionnaire_answers: {...}}`
- Response: `{success: true, suggestions: [...]}`

**Generate Tasks:**
- `POST /dashboard/mentor/stages/<stage_id>/generate-tasks/`
- Request: `{stage_context: {...}}`
- Response: `{success: true, suggestions: [...]}`

### UI Flow

1. After questionnaire completion, show "Generate Stages with AI" button
2. Display suggestions as cards with:
   - Title, description
   - Confidence score
   - Reasoning
   - "Accept" / "Reject" buttons
3. Accepted suggestions create stages
4. Similar flow for task generation from stage view

---

## Implementation Checklist

### Phase 1: Database Foundation
- [ ] Update Project model
- [ ] Create ProjectModule model
- [ ] Create ProjectModuleInstance model
- [ ] Create ProjectQuestionnaire model
- [ ] Create ProjectQuestionnaireAnswer model
- [ ] Create ProjectStage model
- [ ] Create ProjectStageTemplate model
- [ ] Create ProjectStageNote model
- [ ] Create ProjectStageNoteAttachment model
- [ ] Create ProjectStageNoteComment model
- [ ] Create Task model
- [ ] Update ProjectTemplate model
- [ ] Create migrations
- [ ] Run migrations
- [ ] Test models

### Phase 2: Project Assignment Flow
- [ ] Update create_project view
- [ ] Create assign_project_to_client view
- [ ] Create accept_project_assignment_secure view (secure link handler)
- [ ] Create accept_project_assignment view (after auth)
- [ ] Create reject_project_assignment view
- [ ] Create email template with secure link
- [ ] Add email service method with uidb64/token generation
- [ ] Add URL patterns for assignment flow
- [ ] Add "Projects" button to user sidebar menu
- [ ] Add pending assignments badge to Projects menu item
- [ ] Create context processor for pending count
- [ ] Create user projects_list view
- [ ] Create user projects_list template
- [ ] Display pending assignments section
- [ ] Add accept/reject functionality
- [ ] Test secure link workflow
- [ ] Test assignment workflow

### Phase 3: Questionnaire System
- [ ] Create default questions
- [ ] Create questionnaire form view
- [ ] Create questionnaire display view
- [ ] Update project detail page
- [ ] Add validation
- [ ] Test flow

### Phase 4: Module System
- [ ] Seed ProjectModule data
- [ ] Update create project modal
- [ ] Create module selection UI
- [ ] Create manage modules view
- [ ] Display modules on detail page
- [ ] Test module system

### Phase 5: Stage Templates
- [ ] Create stage templates
- [ ] Create copy function
- [ ] Auto-create on project creation
- [ ] Test template copying

### Phase 6: Stage Management
- [ ] Create stage CRUD views
- [ ] Implement reordering
- [ ] Create dependencies UI
- [ ] Create waterfall visualization
- [ ] Test stage management

### Phase 7: Stage Notes & Comments
- [ ] Create note CRUD views
- [ ] Implement image upload
- [ ] Create comment system
- [ ] Display notes/comments
- [ ] Test notes system

### Phase 8: Task Management
- [ ] Create task CRUD views
- [ ] Implement task assignment logic (assign from stage to client)
- [ ] Implement task completion logic (assigned vs active backlog)
- [ ] Create stage backlog UI
- [ ] Create client active backlog UI
- [ ] Create mentor backlog UI
- [ ] Implement reordering within backlogs
- [ ] Display assignment status
- [ ] Add mentor backlog to mentor dashboard
- [ ] Test task system

### Phase 9: AI Integration
- [ ] Create ProjectAIService
- [ ] Create AI endpoints
- [ ] Document API structure
- [ ] Create suggestion UI
- [ ] Test AI flow

### Phase 10: UI/UX
- [ ] Update projects list page
- [ ] Update project detail page
- [ ] Create questionnaire UI
- [ ] Create stages visualization
- [ ] Create module UI
- [ ] Create task UI
- [ ] Add loading/error states
- [ ] Test complete flow

### Phase 11: GDPR Compliance
- [ ] Create signal handler
- [ ] Update models on deletion
- [ ] Cache author info
- [ ] Update UI display
- [ ] Create admin anonymization page
- [ ] Add anonymization view
- [ ] Create anonymization template
- [ ] Add menu item to admin sidebar
- [ ] Implement email search/select
- [ ] Add confirmation modal
- [ ] Test GDPR compliance

---

## Notes & Considerations

### Order Field Strategy

Using `DecimalField` for order allows insertion between items:
- New items get `order = last_order + 1.0`
- Insertion: `new_order = (before + after) / 2`
- Allows infinite insertions without reordering all items

### Stage Dependencies

- Many-to-Many relationship between stages
- UI should show dependency graph
- Validation: prevent circular dependencies
- Completion check: ensure dependencies are completed

### Task Assignment Logic

**Key Principles:**
- Tasks do NOT move between backlogs - they remain in their original location
- Tasks can be created in: stage backlog, client active backlog, or mentor backlog
- Stage tasks can be assigned to client's active backlog (assigned=True, assigned_to set)
- When assigned task is completed by client:
  - Task is unassigned (assigned=False)
  - Task is marked as completed in stage backlog
  - Assignment history is preserved (assigned_to remains for tracking)
- When active backlog task is completed:
  - Task stays in active backlog
  - Task is marked as completed

**Task Locations:**
- `stage`: Task belongs to a project stage
- `user_active_backlog`: Task belongs to client's active backlog
- `mentor_backlog`: Task belongs to mentor's personal backlog

**Assignment Fields:**
- `assigned`: Boolean indicating if task is currently assigned to a client
- `assigned_to`: UserProfile reference to track which client it was assigned to (for future multi-client projects)

### Module System

- Modules are optional and can be added/removed anytime
- Each module has its own data structure (JSONField)
- Module-specific UI components can be added later
- Modules are independent of stages

### AI Integration

- Mock functions return empty lists for now
- Structure is ready for API integration
- Comments document expected API format
- UI can be built to accept suggestions

---

## Future Enhancements (Not in Current Scope)

1. **Progress Calculation**: Overall project progress based on completed stages
2. **Notifications**: Reminders for stage deadlines
3. **Client Visibility**: What clients can see vs. mentor-only
4. **Task History**: Track task movements and changes
5. **Stage Attachments**: Files per stage (beyond note attachments)
6. **Project Templates Marketplace**: Shareable templates
7. **Collaboration Features**: Multiple mentors per project
8. **Analytics**: Project completion rates, time tracking

---

**Document Status:** Active Planning  
**Next Review:** After Phase 1 completion
