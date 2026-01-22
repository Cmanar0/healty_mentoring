# Template & Questionnaire Refactoring Implementation Plan

## Overview

This document outlines the refactoring plan to separate Templates, Questionnaires, and Questions into distinct models with clear relationships. This will improve flexibility, reusability, and maintainability.

## Proposed Architecture

### Model Structure

```
ProjectTemplate (Template)
├── name
├── description
├── icon
├── author (FK to MentorProfile, nullable for premade templates)
├── is_custom (boolean)
└── questionnaire (OneToOne to Questionnaire) - created automatically

Questionnaire
├── template (OneToOne to ProjectTemplate)
├── title (default: "Onboarding Questionnaire")
└── questions (reverse FK from Question)

Question
├── questionnaire (FK to Questionnaire)
├── question_text
├── question_type
├── is_required
├── order
├── options (JSON)
└── help_text

QuestionnaireResponse (for client answers)
├── project (FK to Project)
├── questionnaire (FK to Questionnaire)
├── answers (JSON field storing all answers)
└── completed_at
```

## Benefits of This Approach

1. **Separation of Concerns**: Templates can have other relationships (modules, stages) without coupling to questionnaires
2. **Reusability**: Questionnaires can be used independently for other purposes
3. **Cleaner Data Model**: Clear hierarchy: Template → Questionnaire → Questions
4. **Simplified Answers**: Single JSON record per questionnaire response instead of multiple answer records
5. **Better Frontend Integration**: Fetching template.questionnaire.questions gives complete question set

## Data Cleanup Required (Django Admin)

Before implementing the new structure, you need to manually delete the following in Django Admin:

### 1. Delete All Questionnaire Answers
**Location**: Django Admin → Dashboard User → Project Questionnaire Answers
- **Action**: Delete ALL records
- **Reason**: Will be replaced with JSON-based QuestionnaireResponse model
- **Impact**: Existing questionnaire answers will be lost (this is expected for the refactor)

### 2. Delete All Questionnaire Questions
**Location**: Django Admin → Dashboard User → Project Questionnaires
- **Action**: Delete ALL records
- **Reason**: Current `ProjectQuestionnaire` model represents questions, will become `Question` model
- **Impact**: All existing questions will need to be recreated in the new structure

### 3. Field Removal (Will be handled in migration)
- `ProjectTemplate.category` - Remove category field
- `ProjectTemplate.has_default_questions` - No longer needed

## Implementation Steps

### Phase 1: Model Creation & Migration

#### Step 1.1: Create New Models
**File**: `dashboard_user/models.py`

1. **Create Questionnaire Model**
   ```python
   class Questionnaire(models.Model):
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
   ```

2. **Create Question Model**
   ```python
   class Question(models.Model):
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
   ```

3. **Create QuestionnaireResponse Model**
   ```python
   class QuestionnaireResponse(models.Model):
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
   ```

#### Step 1.2: Modify ProjectTemplate Model
**File**: `dashboard_user/models.py`

- Remove `category` field
- Remove `has_default_questions` field
- Keep `author` field (already exists)
- Keep `is_custom` field (already exists)

#### Step 1.3: Modify Project Model
**File**: `dashboard_user/models.py`

- Keep `questionnaire_completed` and `questionnaire_completed_at` fields
- These will reference the new `QuestionnaireResponse` model

#### Step 1.4: Create Migration
- Create migration to add new models
- Create migration to remove old fields
- Create migration to delete old models (ProjectQuestionnaire, ProjectQuestionnaireAnswer)

### Phase 2: Auto-Create Questionnaire on Template Creation

#### Step 2.1: Add Signal Handler
**File**: `dashboard_user/models.py` or `dashboard_user/signals.py`

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=ProjectTemplate)
def create_template_questionnaire(sender, instance, created, **kwargs):
    """Automatically create a questionnaire when a template is created"""
    if created:
        Questionnaire.objects.get_or_create(template=instance)
```

### Phase 3: Update Views

#### Step 3.1: Update Template Creation View
**File**: `dashboard_mentor/views.py` - `create_custom_template()`

- Remove category from form processing
- Questionnaire will be auto-created via signal
- Redirect to template detail page after creation

#### Step 3.2: Update Template Detail View
**File**: `dashboard_mentor/views.py` - `template_detail()`

- Change from `template.questions.all()` to `template.questionnaire.questions.all()`
- Add UI for creating questions manually
- Add AI generation button (similar to stage creation)

#### Step 3.3: Create Question Management Views
**File**: `dashboard_mentor/views.py`

1. **Create Question View** (AJAX)
   ```python
   @login_required
   def create_question(request, template_id):
       """Create a new question for template's questionnaire"""
       # Validate mentor owns template
       # Create question
       # Return JSON response
   ```

2. **Update Question View** (AJAX)
   ```python
   @login_required
   def update_question(request, question_id):
       """Update an existing question"""
       # Validate mentor owns template
       # Update question
       # Return JSON response
   ```

3. **Delete Question View** (AJAX)
   ```python
   @login_required
   def delete_question(request, question_id):
       """Delete a question"""
       # Validate mentor owns template
       # Delete question
       # Return JSON response
   ```

4. **Reorder Questions View** (AJAX)
   ```python
   @login_required
   def reorder_questions(request, template_id):
       """Reorder questions via drag-and-drop"""
       # Validate mentor owns template
       # Update question orders
       # Return JSON response
   ```

5. **AI Generate Questions View** (AJAX)
   ```python
   @login_required
   def generate_questions_ai(request, template_id):
       """Generate questions using AI"""
       # Similar to existing generate_questions_ai but for new Question model
       # Return JSON with generated questions
   ```

#### Step 3.4: Update Questionnaire Submission View
**File**: `dashboard_user/views.py` - `submit_questionnaire()`

- Change to use `QuestionnaireResponse` model
- Store answers as JSON: `{question_id: answer_text}`
- Update `questionnaire_completed` flag on Project

#### Step 3.5: Update Project Detail View
**File**: `dashboard_user/views.py` - `project_detail()`

- Fetch questions from `project.template.questionnaire.questions.all()`
- Display existing answers from `QuestionnaireResponse` if exists

### Phase 4: Update Templates

#### Step 4.1: Update Create Template Modal
**File**: `general/templates/general/modals/create_template_modal.html`

- Remove category field
- Keep: name, description, icon
- After creation, redirect to template detail page

#### Step 4.2: Create Template Detail Page
**File**: `dashboard_mentor/templates/dashboard_mentor/templates/template_detail.html`

- Display template info (name, description, icon)
- Add "Onboarding Questionnaire" section
- List existing questions with edit/delete/reorder
- Add "Add Question" button (manual creation)
- Add "Generate with AI" button (similar to stage generation)
- Question form modal for creating/editing questions

#### Step 4.3: Update Templates List Page
**File**: `dashboard_mentor/templates/dashboard_mentor/templates_list.html`

- Show two sections: "Premade Templates" and "Custom Templates"
- Filter by `is_custom=False` for premade
- Filter by `is_custom=True` and `author=mentor` for custom

#### Step 4.4: Update Project Questionnaire Form
**File**: `dashboard_user/templates/dashboard_user/projects/project_detail.html`

- Update to fetch questions from `template.questionnaire.questions`
- Update form submission to create/update `QuestionnaireResponse`
- Display answers from JSON if questionnaire already completed

### Phase 5: Update Admin

#### Step 5.1: Register New Models
**File**: `dashboard_user/admin.py`

```python
@admin.register(Questionnaire)
class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = ('template', 'title', 'created_at')
    list_filter = ('template__is_custom',)
    search_fields = ('template__name', 'title')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'questionnaire', 'question_type', 'is_required', 'order')
    list_filter = ('question_type', 'is_required', 'questionnaire__template')
    search_fields = ('question_text',)
    ordering = ('questionnaire', 'order')

@admin.register(QuestionnaireResponse)
class QuestionnaireResponseAdmin(admin.ModelAdmin):
    list_display = ('project', 'questionnaire', 'completed_at')
    list_filter = ('questionnaire__template', 'completed_at')
    search_fields = ('project__title', 'questionnaire__title')
    readonly_fields = ('completed_at', 'updated_at')
```

#### Step 5.2: Update ProjectTemplateAdmin
**File**: `dashboard_user/admin.py`

- Remove category from fieldsets
- Remove has_default_questions from fieldsets
- Add inline for Questionnaire (optional, for admin convenience)

### Phase 6: URL Configuration

#### Step 6.1: Update Mentor URLs
**File**: `dashboard_mentor/urls.py`

```python
path('templates/<int:template_id>/questions/create/', views.create_question, name='create_question'),
path('templates/<int:template_id>/questions/generate-ai/', views.generate_questions_ai, name='generate_questions_ai'),
path('questions/<int:question_id>/update/', views.update_question, name='update_question'),
path('questions/<int:question_id>/delete/', views.delete_question, name='delete_question'),
path('templates/<int:template_id>/questions/reorder/', views.reorder_questions, name='reorder_questions'),
```

### Phase 7: Frontend JavaScript

#### Step 7.1: Question Management AJAX
**File**: Create or update `static/js/template_questions.js`

- Functions for:
  - Creating question (show modal, submit via AJAX)
  - Editing question (populate modal, submit via AJAX)
  - Deleting question (confirm, submit via AJAX)
  - Reordering questions (drag-and-drop, submit via AJAX)
  - AI generation (show loading, display generated questions for review)

#### Step 7.2: Update Questionnaire Form Submission
**File**: Update existing questionnaire form JavaScript

- Update to submit answers as JSON object
- Map question IDs to answers
- Handle QuestionnaireResponse creation/update

### Phase 8: Data Migration (Optional)

If you want to preserve existing data:

1. Create a data migration script to:
   - Create Questionnaire for each existing ProjectTemplate
   - Convert existing ProjectQuestionnaire records to Question records
   - Convert existing ProjectQuestionnaireAnswer records to QuestionnaireResponse JSON

**Note**: Since you're deleting existing data manually, this step may not be necessary.

## Testing Checklist

- [ ] Create premade template (no author) - questionnaire auto-created
- [ ] Create custom template (with author) - questionnaire auto-created
- [ ] Add question manually to questionnaire
- [ ] Edit question
- [ ] Delete question
- [ ] Reorder questions
- [ ] Generate questions with AI
- [ ] Client submits questionnaire - answers stored as JSON
- [ ] View completed questionnaire answers
- [ ] Templates list shows premade and custom separately
- [ ] Template detail page displays questionnaire correctly
- [ ] Django admin shows all new models correctly

## Migration Order

1. Create new models (Questionnaire, Question, QuestionnaireResponse)
2. Add signal to auto-create questionnaire
3. Remove old models (ProjectQuestionnaire, ProjectQuestionnaireAnswer)
4. Remove old fields (category, has_default_questions)
5. Update all views and templates
6. Test thoroughly

## Rollback Plan

If issues arise:
1. Keep old models temporarily (don't delete immediately)
2. Use feature flags to switch between old and new system
3. Have data export script ready before migration

## Notes

- The `ProjectTemplate.author` field already exists and works for custom templates
- The `ProjectTemplate.is_custom` field already exists
- Answers stored as JSON: `{question_id: answer_text}` format
- Questionnaire is automatically created when template is created (via signal)
- All questions must belong to a questionnaire (no standalone questions)
