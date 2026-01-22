# Django Admin Cleanup Checklist

## ⚠️ IMPORTANT: Delete These Records Before Implementation

Before we proceed with the refactoring implementation, you need to manually delete the following records in Django Admin. These will be replaced by the new model structure.

### Step 1: Delete All Questionnaire Answers

**Location**: Django Admin → Dashboard User → **Project Questionnaire Answers**

- **Action**: Select all records and delete them
- **Count**: Check how many records exist (you can see the count at the top)
- **Reason**: These will be replaced by the new `QuestionnaireResponse` model which stores answers as JSON
- **Impact**: ⚠️ All existing questionnaire answers will be permanently lost

**How to delete**:
1. Go to Django Admin
2. Navigate to "Dashboard User" → "Project Questionnaire Answers"
3. Select all items (use the checkbox at the top to select all)
4. Choose "Delete selected" from the action dropdown
5. Confirm deletion

---

### Step 2: Delete All Questionnaire Questions

**Location**: Django Admin → Dashboard User → **Project Questionnaires**

- **Action**: Select all records and delete them
- **Count**: Check how many records exist
- **Reason**: The current `ProjectQuestionnaire` model represents individual questions. This will be replaced by the new `Question` model which belongs to a `Questionnaire`
- **Impact**: ⚠️ All existing questions will be permanently lost and will need to be recreated in the new structure

**How to delete**:
1. Go to Django Admin
2. Navigate to "Dashboard User" → "Project Questionnaires"
3. Select all items (use the checkbox at the top to select all)
4. Choose "Delete selected" from the action dropdown
5. Confirm deletion

---

### Step 3: Verify Deletion

After deletion, verify that:

- [ ] **Project Questionnaire Answers** shows 0 records
- [ ] **Project Questionnaires** shows 0 records

---

## What Will NOT Be Deleted

These will remain and be modified:

- ✅ **Project Templates** - Will be kept, but `category` and `has_default_questions` fields will be removed
- ✅ **Projects** - Will be kept, `questionnaire_completed` fields will remain
- ✅ All other models remain unchanged

---

## After Cleanup

Once you've confirmed all deletions are complete, let me know and we'll proceed with:

1. Creating the new models (Questionnaire, Question, QuestionnaireResponse)
2. Creating migrations
3. Updating views and templates
4. Implementing the new UI for question management

---

## Questions?

If you're unsure about any step or want to verify what will be deleted, check the records in Django Admin first before proceeding with deletion.
