# Reviews System Implementation Plan

## Overview
This document outlines the implementation plan for the reviews system that allows clients to review mentors after completing their first session.

## Models

### Review Model
- `mentor` (ForeignKey to MentorProfile)
- `client` (ForeignKey to UserProfile)
- `rating` (IntegerField, 1-5 stars)
- `text` (TextField)
- `status` (CharField: 'draft', 'published')
- `published_at` (DateTimeField, nullable)
- `created_at` (DateTimeField)
- `updated_at` (DateTimeField)
- Unique constraint: one review per mentor-client pair

### ReviewReply Model
- `review` (OneToOneField to Review)
- `text` (TextField)
- `created_at` (DateTimeField)
- `updated_at` (DateTimeField)

### MentorClientRelationship Updates
- `review_requested_at` (DateTimeField, nullable) - tracks when mentor last requested review
- `review_provided` (BooleanField) - tracks if review has been provided

## Pages to Create

### 1. Mentor Client Detail Page
- URL: `/dashboard/mentor/clients/<client_id>/`
- Shows:
  - Client basic info (name, email)
  - Relationship info
  - All sessions between mentor and client
  - Review section:
    - If no review: button to request review (with loading spinner)
    - If review exists: show review with reply section
    - Mentor can write/edit reply

### 2. User Mentor Detail Page
- URL: `/dashboard/user/mentors/<mentor_id>/`
- Shows:
  - Mentor basic info (name, email)
  - Link to public mentor page
  - Relationship info
  - Review section:
    - Write/edit/publish/delete review
    - Only one review allowed
    - Star rating system

### 3. Mentor Reviews Management Page
- URL: `/dashboard/mentor/profile/reviews`
- Shows:
  - Paginated list of all reviews
  - For each review: client name, rating, text, reply section
  - Mentor can write/edit reply for each review

### 4. User Review Writing Page
- URL: `/dashboard/user/review/<mentor_id>/<token>/`
- Accessible via email link
- Logs out current user if different user is logged in
- Shows form to write review for specific mentor
- Star rating system

## Features

### Review Request Flow
1. Mentor clicks "Request Review" button on client detail page
2. Check if first session is completed
3. Check rate limit (once per day)
4. Send email to client with link
5. Email link logs out current user and redirects to review page
6. Client writes and publishes review
7. Email and notification sent to mentor

### Review Publishing Flow
1. Client writes review (draft status)
2. Client can edit before publishing
3. When published:
   - Set `published_at` timestamp
   - Send email to mentor
   - Create notification for mentor
   - Update relationship `review_provided` to True

### Review Display
- Public mentor page: show all published reviews with stars and average rating
- Mentor profile: show last 3 reviews in sidebar
- Average rating calculated from published reviews only

## Email Templates Needed
1. `review_request.html` - Email sent when mentor requests review
2. `review_published.html` - Email sent to mentor when review is published

## URL Routes

### Mentor Routes
- `/dashboard/mentor/clients/<client_id>/` - Client detail
- `/dashboard/mentor/profile/reviews/` - Reviews management
- `/dashboard/mentor/clients/<client_id>/request-review/` - AJAX endpoint
- `/dashboard/mentor/reviews/<review_id>/reply/` - AJAX endpoint for reply

### User Routes
- `/dashboard/user/mentors/<mentor_id>/` - Mentor detail
- `/dashboard/user/review/<mentor_id>/<token>/` - Review writing page
- `/dashboard/user/reviews/<review_id>/` - AJAX endpoints for create/edit/publish/delete

## Business Rules
1. Only one review per client-mentor pair
2. Review can only be requested if:
   - First session is scheduled (`first_session_scheduled = True`)
   - At least one session has status 'completed'
   - Rate limit: once per day
3. Review can only be published if:
   - At least one session is completed
4. Mentor can write one reply per review
5. Average rating calculated from published reviews only
