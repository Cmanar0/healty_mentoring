# Reviews System Implementation Summary

## ✅ Completed

### 1. Models Created
- **Review Model** (`general/models.py`):
  - Fields: mentor, client, rating (1-5 stars), text, status (draft/published), published_at, timestamps
  - Unique constraint: one review per mentor-client pair
  - Related name: `client_reviews` (to avoid conflict with existing `reviews` JSONField)
  
- **ReviewReply Model** (`general/models.py`):
  - Fields: review (OneToOne), text, timestamps
  - One reply per review

- **MentorClientRelationship Updates** (`accounts/models.py`):
  - Added `review_requested_at` (DateTimeField, nullable) - tracks when mentor last requested review
  - Added `review_provided` (BooleanField) - tracks if review has been provided

### 2. Migrations
- Created migration for Review and ReviewReply models
- Created migration for MentorClientRelationship updates
- Ready to run: `python manage.py migrate`

## 📋 Implementation Plan - Remaining Tasks

### Phase 1: Core Views and Pages

#### 1. Mentor Client Detail Page
**URL:** `/dashboard/mentor/clients/<client_id>/`
**View:** `dashboard_mentor/views.py` - `client_detail(request, client_id)`
**Template:** `dashboard_mentor/templates/dashboard_mentor/client_detail.html`

**Features:**
- Display client info (name, email)
- Display relationship info
- List all sessions between mentor and client
- Review section:
  - If no review exists and first session completed: "Request Review" button
  - If review exists: display review with reply section
  - Mentor can write/edit reply

**Logic:**
```python
# Check if can request review:
# 1. first_session_scheduled = True
# 2. At least one session with status='completed'
# 3. review_requested_at is None OR > 24 hours ago
# 4. review_provided = False
```

#### 2. User Mentor Detail Page
**URL:** `/dashboard/user/mentors/<mentor_id>/`
**View:** `dashboard_user/views.py` - `mentor_detail(request, mentor_id)`
**Template:** `dashboard_user/templates/dashboard_user/mentor_detail.html`

**Features:**
- Display mentor basic info (name, email)
- Link to public mentor page (`/mentor/<mentor_id>/`)
- Relationship info
- Review section:
  - Write/edit/publish/delete review
  - Star rating system (1-5)
  - Only one review allowed (check if exists, show edit form if it does)

#### 3. Mentor Reviews Management Page
**URL:** `/dashboard/mentor/profile/reviews/`
**View:** `dashboard_mentor/views.py` - `reviews_management(request)`
**Template:** `dashboard_mentor/templates/dashboard_mentor/reviews.html`

**Features:**
- Paginated list of all reviews (published and draft)
- For each review:
  - Client name
  - Rating (stars)
  - Review text
  - Published date
  - Reply section (write/edit)
- Pagination controls

#### 4. User Review Writing Page (from email link)
**URL:** `/dashboard/user/review/<mentor_id>/<token>/`
**View:** `dashboard_user/views.py` - `write_review(request, mentor_id, token)`
**Template:** `dashboard_user/templates/dashboard_user/write_review.html`

**Features:**
- Validate token
- Log out current user if different user is logged in
- Show form to write review for specific mentor
- Star rating system
- Save as draft or publish immediately

### Phase 2: AJAX Endpoints

#### 1. Request Review (Mentor)
**URL:** `/dashboard/mentor/clients/<client_id>/request-review/`
**Method:** POST
**View:** `dashboard_mentor/views.py` - `request_review(request, client_id)`

**Logic:**
- Check rate limit (once per day)
- Check if first session completed
- Generate token for review link
- Update `review_requested_at`
- Send email with link
- Return JSON response

#### 2. Create/Edit Review (User)
**URL:** `/dashboard/user/reviews/<review_id>/` (POST for create, PUT for edit)
**View:** `dashboard_user/views.py` - `create_edit_review(request, review_id=None)`

**Logic:**
- Validate mentor-client relationship
- Check if review already exists (for create)
- Save review (draft status)
- Return JSON response

#### 3. Publish Review (User)
**URL:** `/dashboard/user/reviews/<review_id>/publish/`
**Method:** POST
**View:** `dashboard_user/views.py` - `publish_review(request, review_id)`

**Logic:**
- Check if at least one session is completed
- Update review status to 'published'
- Set `published_at` timestamp
- Update relationship `review_provided = True`
- Send email to mentor
- Create notification for mentor
- Return JSON response

#### 4. Delete Review (User)
**URL:** `/dashboard/user/reviews/<review_id>/delete/`
**Method:** POST
**View:** `dashboard_user/views.py` - `delete_review(request, review_id)`

**Logic:**
- Check ownership
- Delete review (cascade deletes reply)
- Update relationship `review_provided = False`
- Return JSON response

#### 5. Write/Edit Reply (Mentor)
**URL:** `/dashboard/mentor/reviews/<review_id>/reply/`
**Method:** POST
**View:** `dashboard_mentor/views.py` - `review_reply(request, review_id)`

**Logic:**
- Check review exists and belongs to mentor
- Create or update reply
- Return JSON response

### Phase 3: Email Templates

#### 1. Review Request Email
**Template:** `general/templates/emails/review_request.html`
**Context:**
- `mentor_name`: Mentor's full name
- `client_name`: Client's first name
- `review_url`: Link to review page with token (logs out current user)
- `site_domain`: Site domain

**Email Link Format:**
`/dashboard/user/review/<mentor_id>/<token>/?logout=true`

**View Logic for Link:**
- If `logout=true` in query params, log out current user
- Validate token
- Redirect to review writing page

#### 2. Review Published Email
**Template:** `general/templates/emails/review_published.html`
**Context:**
- `mentor_name`: Mentor's full name
- `client_name`: Client's full name
- `rating`: Star rating (1-5)
- `review_text`: Review text
- `review_url`: Link to mentor's reviews page
- `site_domain`: Site domain

### Phase 4: Public Display Updates

#### 1. Public Mentor Profile Page
**File:** `web/templates/web/mentor_profile_detail.html`
**Updates:**
- Calculate average rating from published reviews
- Display average rating in header (decimal format, e.g., "4.5")
- Display all published reviews with:
  - Star rating (visual stars)
  - Review text
  - Client name (first name + last initial)
  - Published date
  - Mentor reply (if exists)

**View Logic:**
```python
# In web/views.py mentor_profile_detail()
from general.models import Review
reviews = Review.objects.filter(mentor=mentor_profile, status='published').select_related('client', 'client__user', 'reply').order_by('-published_at')
average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
```

#### 2. Mentor Profile Page (Dashboard)
**File:** `dashboard_mentor/templates/dashboard_mentor/profile.html`
**Updates:**
- In "Profile Credibility" sidebar:
  - Show last 3 published reviews
  - Show progress bar (at least 3 reviews)
  - "Manage Reviews" button → `/dashboard/mentor/profile/reviews/`

**View Logic:**
```python
# In dashboard_mentor/views.py profile()
from general.models import Review
last_3_reviews = Review.objects.filter(mentor=mentor_profile, status='published').select_related('client', 'reply').order_by('-published_at')[:3]
total_reviews = Review.objects.filter(mentor=mentor_profile, status='published').count()
has_3_reviews = total_reviews >= 3
```

### Phase 5: List Page Updates

#### 1. Clients List Page
**File:** `dashboard_mentor/templates/dashboard_mentor/clients.html`
**Update:** Make client rows clickable
- Add `onclick` or wrap in `<a>` tag
- Link to `/dashboard/mentor/clients/<client_id>/`

#### 2. Mentors List Page
**File:** `dashboard_user/templates/dashboard_user/mentors.html`
**Update:** Make mentor rows clickable
- Add `onclick` or wrap in `<a>` tag
- Link to `/dashboard/user/mentors/<mentor_id>/`

### Phase 6: URL Routes

#### Mentor Routes (`dashboard_mentor/urls.py`)
```python
path('clients/<int:client_id>/', views.client_detail, name='client_detail'),
path('clients/<int:client_id>/request-review/', views.request_review, name='request_review'),
path('profile/reviews/', views.reviews_management, name='reviews_management'),
path('reviews/<int:review_id>/reply/', views.review_reply, name='review_reply'),
```

#### User Routes (`dashboard_user/urls.py`)
```python
path('mentors/<int:mentor_id>/', views.mentor_detail, name='mentor_detail'),
path('review/<int:mentor_id>/<str:token>/', views.write_review, name='write_review'),
path('reviews/', views.create_edit_review, name='create_review'),
path('reviews/<int:review_id>/', views.create_edit_review, name='edit_review'),
path('reviews/<int:review_id>/publish/', views.publish_review, name='publish_review'),
path('reviews/<int:review_id>/delete/', views.delete_review, name='delete_review'),
```

## 🔑 Key Business Rules

1. **Review Eligibility:**
   - First session must be scheduled (`first_session_scheduled = True`)
   - At least one session must have status `'completed'`

2. **Rate Limiting:**
   - Mentor can request review once per day per client
   - Check: `review_requested_at` is None OR > 24 hours ago

3. **One Review Per Pair:**
   - Enforced by unique constraint on (mentor, client)
   - If review exists, show edit form instead of create form

4. **Review Publishing:**
   - Can only publish if at least one session is completed
   - When published: send email + notification to mentor
   - Update `review_provided = True` on relationship

5. **Average Rating:**
   - Calculated from published reviews only
   - Display as decimal (e.g., 4.5)

6. **Reply:**
   - One reply per review (OneToOne relationship)
   - Mentor can write/edit reply anytime after review is published

## 📝 Helper Functions Needed

### In `general/models.py` or utility file:
```python
def can_request_review(relationship):
    """Check if mentor can request review from client"""
    from general.models import Session
    # Check first session scheduled
    if not relationship.first_session_scheduled:
        return False, "First session not scheduled"
    
    # Check if at least one session is completed
    mentor = relationship.mentor
    client = relationship.client
    completed_sessions = Session.objects.filter(
        mentors=mentor,
        attendees=client.user,
        status='completed'
    ).exists()
    
    if not completed_sessions:
        return False, "No completed sessions"
    
    # Check rate limit
    if relationship.review_requested_at:
        from django.utils import timezone
        from datetime import timedelta
        if timezone.now() - relationship.review_requested_at < timedelta(days=1):
            return False, "Review already requested today"
    
    # Check if review already provided
    if relationship.review_provided:
        return False, "Review already provided"
    
    return True, None

def get_mentor_average_rating(mentor_profile):
    """Calculate average rating from published reviews"""
    from django.db.models import Avg
    from general.models import Review
    result = Review.objects.filter(
        mentor=mentor_profile,
        status='published'
    ).aggregate(avg_rating=Avg('rating'))
    return result['avg_rating'] or 0
```

## 🎨 UI/UX Considerations

1. **Star Rating Display:**
   - Use filled/empty star icons
   - Display as: ⭐⭐⭐⭐⭐ (5 stars max)
   - Show decimal average (e.g., 4.5)

2. **Loading States:**
   - Show spinner when requesting review
   - Disable button during request

3. **Review Form:**
   - Star selector (click to rate)
   - Textarea for review text
   - Save as draft / Publish buttons

4. **Review Display:**
   - Show client name (first name + last initial for privacy)
   - Show published date
   - Show mentor reply below review (if exists)

5. **Empty States:**
   - "No reviews yet" message
   - "Request review" button (if eligible)

## 🚀 Next Steps

1. Run migrations: `python manage.py migrate`
2. Implement views (Phase 1)
3. Create templates
4. Add AJAX endpoints (Phase 2)
5. Create email templates (Phase 3)
6. Update public/profile pages (Phase 4)
7. Update list pages (Phase 5)
8. Add URL routes (Phase 6)
9. Test complete flow
10. Add error handling and edge cases
