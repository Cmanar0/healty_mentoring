# Mentor Guides – IDs and action_id Query Parameters

Use these in app logic (e.g. scrolling to a section, marking a step complete, analytics).

---

## Query parameter

When a user opens a page from a guide subtask, the URL includes:

- **`action_id`** – identifies which guide/subtask they came from.

Example: `/dashboard/mentor/profile/?action_id=guide_setup_mentor_type`

---

## Guide 1: Setup Your Profile

| Subtask | action_id | Use in app |
|--------|-----------|------------|
| Complete at least 80% of your profile | `guide_setup_profile_80` | Scroll to profile completion section (top of profile page). |
| Set your Mentor Type | `guide_setup_mentor_type` | Scroll to Mentor Type field. |
| Set your Bio | `guide_setup_bio` | Scroll to Bio field. |
| Set your Languages | `guide_setup_languages` | Scroll to Languages section. |
| Set your Categories | `guide_setup_categories` | Scroll to Categories section. |
| Set pricing for your session | `guide_setup_pricing` | Scroll to Price per Hour / pricing section. |
| Set your Session Length | `guide_setup_session_length` | Scroll to Session Length field. |

**Guide-level (main)**  
- Main guide (for “claim” / completion): no step; progress is `(guide_id, guide_step=None)`.

---

## Other guides (one subtask each)

| Guide name | action_id |
|------------|-----------|
| Set Your Availability | `guide_availability` |
| Invite Your First Client | `guide_invite_client` |
| Create a Project Template | `guide_templates` |
| Schedule a Session | `guide_schedule_session` |
| Explore Your Dashboard | `guide_dashboard` |

---

## Profile page scroll targets (HTML id)

Map `action_id` to the element id used for scrolling:

| action_id | Element id on profile page |
|-----------|----------------------------|
| `guide_setup_profile_80` | `guide-section-profile-completion` |
| `guide_setup_mentor_type` | `guide-section-mentor-type` |
| `guide_setup_bio` | `guide-section-bio` |
| `guide_setup_languages` | `guide-section-languages` |
| `guide_setup_categories` | `guide-section-categories` |
| `guide_setup_pricing` | `guide-section-pricing` |
| `guide_setup_session_length` | `guide-section-session-length` |

---

## Marking subtasks complete

- **Model:** `MentorGuideProgress` – one row per completed (guide, guide_step).
- **Subtask completed:** `MentorGuideProgress(mentor_profile=..., guide=..., guide_step=step)`.
- **Main guide completed (claimed):** `MentorGuideProgress(mentor_profile=..., guide=..., guide_step=None)`.

For “Setup Your Profile”, mark a subtask complete when the profile form is saved and the related field(s) are filled (e.g. mentor_type non-empty for `guide_setup_mentor_type`). Map action_id to the GuideStep (e.g. by `GuideStep.objects.filter(guide=guide, action_id=action_id).first()`).
