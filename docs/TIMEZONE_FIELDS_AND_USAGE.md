# Timezone fields and usage

## Profile timezone fields (UserProfile, MentorProfile, AdminProfile)

All three profile types have the same timezone-related fields in `accounts/models.py`:

| Field | Purpose |
|-------|--------|
| **`selected_timezone`** | User's chosen/preferred timezone (e.g. from settings or timezone modal). **This is the single source of truth for display.** |
| `detected_timezone` | Browser-detected timezone, updated on page load. |
| `confirmed_timezone_mismatch` | True if user confirmed they want to keep a timezone different from detected. |
| `time_zone` | Legacy field; kept in sync with `selected_timezone` for backward compatibility. |

**Preferred order for display:** `selected_timezone` → `detected_timezone` → `time_zone` → `'UTC'`.

---

## Where timezone is used

### User dashboard – upcoming sessions

- **Views:** `dashboard_user/views.py`  
  - `dashboard_user` (main dashboard, first 4 sessions)  
  - `my_sessions` (my-sessions page, first 10)  
  - `get_sessions_paginated` (infinite scroll API)
- **Profile used:** `request.user.profile` (for role "user" this is `UserProfile`).
- **Timezone used:** `selected_timezone or detected_timezone or time_zone or 'UTC'`.
- Session `start_datetime` / `end_datetime` are converted with `astimezone(user_tzinfo)` before sending to the template or JSON.

### Booking modal (user books a session with a mentor)

- **Template:** `dashboard_user/templates/dashboard_user/popups/booking_modal.html`
- **Logged-in user:**  
  - `userDisplayTimezone` = `selected_timezone` → `detected_timezone` → `time_zone` → `'UTC'` (same as dashboard).  
  - When the modal opens, slot display and recap use this value; hidden input `bookingTimezoneValue` is set from it so the email/payment step matches the dashboard.
- **Not logged in / not registered (guest booking):**  
  - No profile → `userDisplayTimezone` is `null`. We **do not** use profile timezone.  
  - When the guest clicks “Book this slot”, **email collection modal** opens (`openEmailCollectionModal(false)`).  
  - There, timezone is set from **browser-detected** timezone (`Intl.DateTimeFormat().resolvedOptions().timeZone`); we set `bookingTimezoneValue` to that and show the timezone section.  
  - Guest can change it via “Change my time” (time correction modal / timezone select).  
  - Session recap and submitted booking use the chosen/detected timezone. This workflow is unchanged by the timezone unification.

### Mentor dashboard – upcoming sessions

- **View:** `dashboard_mentor/views.py` – `my_sessions`, `get_sessions_paginated`
- **Timezone:** `mentor_profile.selected_timezone or mentor_profile.time_zone or 'UTC'` (sessions shown in mentor’s timezone).

---

## Consistency rule

**Upcoming sessions (user dashboard and my-sessions)** and **booking modal (slot display and session recap)** must use the same timezone for the logged-in user:

1. Use **`selected_timezone`** when set.
2. Otherwise use the same fallback as the dashboard: `detected_timezone` → `time_zone` → `'UTC'`, and ensure the booking modal’s hidden field and recap use that value (e.g. by initializing `bookingTimezoneValue` from the server with that fallback).
