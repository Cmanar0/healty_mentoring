# Session: pouze mentors a attendees (pole), notifikace při zrušení / odhlášení

## Model

- **Session** má jen dvě „pole“ stran:
  - **`mentors`** – M2M z `MentorProfile.sessions` (related_name="mentors") → queryset `MentorProfile`.
  - **`attendees`** – M2M na `CustomUser` (klienti) → related_name="attended_sessions".

- **`created_by`** je deprecated (nullable), nepoužívá se; zdrojem pravdy jsou `session.mentors` a `session.attendees`.

## Vytváření session

Vždy po `Session.objects.create(...)` (bez created_by):

1. **`mentor_profile.sessions.add(session)`** – aby session měl mentora v `session.mentors`.
2. **`session.attendees.add(user)`** nebo **`session.attendees.set([...])`** – klienti.

Dělá se v: book_session (user), save_availability (mentor), invite (mentor), admin clone.

## Zrušení / odhlášení

### Mentor zruší (dashboard mentor – upcoming session, my-sessions)

- **Jen jeden mentor** (`session.mentors.count() == 1`): session se **smaže**, všem v `session.attendees` přijde e-mail „Session cancelled“.
- **Více mentorů** (`session.mentors.count() > 1`): frontend zobrazí **modal** – výběr:
  - **Odhlásit se ze session** (už se nechci účastnit) → `POST` s **`leave_only: true`**: tento mentor se odebere z `session.mentors`, všem attendees a ostatním mentorům přijde e-mail „Mentor X is no longer participating“. Pokud po odebrání nezůstane žádný mentor, session se smaže.
  - **Zrušit session pro všechny** → `POST` s **`leave_only: false`**: session se smaže, všem attendees přijde „Session cancelled“.

### Klient zruší (dashboard user – my-sessions)

- **Jen jeden attendee** (`session.attendees.count() == 1`): session se **zruší** (status=cancelled), všem v `session.mentors` přijde e-mail „Session cancelled by client“.
- **Více účastníků** (`session.attendees.count() > 1`): frontend zobrazí **modal** – potvrzení „Chci se odhlásit ze session“. Po potvrzení se pošle **`leave_only: true`**: tento klient se odebere z `session.attendees`, mentorům a ostatním attendees přijde e-mail „Client X has left the session“. Session se neruší.

## API

- **Mentor cancel**  
  `POST /dashboard/mentor/my-sessions/session/<id>/cancel/`  
  Body (JSON): `{}` nebo `{ "leave_only": true }` / `{ "leave_only": false }`.  
  Při více mentorech je nutné poslat `leave_only` (true = jen se odhlásit, false = zrušit pro všechny).

- **Client cancel**  
  `POST /dashboard/user/my-sessions/session/<id>/cancel/`  
  Body (JSON): `{}` (jeden attendee = zrušení session) nebo `{ "leave_only": true }` (více účastníků = jen odhlášení).  
  Při více účastnících bez `leave_only: true` vrací backend 400 a `require_leave_confirm: true` – frontend má zobrazit modal a znovu poslat s `leave_only: true`.

## E-maily

- Session zrušena (mentor smazal / jediný klient zrušil): `session_deleted_notification`, `session_cancelled_by_client_notification`.
- Mentor se odhlásil (více mentorů): `session_mentor_left_notification`.
- Klient se odhlásil (více účastníků): `session_client_left_notification`.
