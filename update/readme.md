# Updates & Database Log

This file documents all structural database improvements, backend logic repairs, and routing fixes made to complete the Ledger CS50 project.

---

## 🔑 Admin Registration Bypass (Secret Code)

To bypass the chicken-and-egg problem of not having a first approved admin user to approve other administrators, the registration screen includes an optional **Admin Secret Code** field. If a user chooses an Admin or Professor status and supplies a valid secret code, their account is instantly auto-approved.

### Predefined Valid Bypass Codes:
* `LEDGER_ADMIN_2026`
* `SECRET_ADMIN_BYPASS`
* `CS50_LEDGER_ADMIN`
* `admin`
* `admin123`

If a user fills this with an invalid code or leaves it blank, the registration falls back to standard behavior requiring approval.

---

## 🗄️ Database Organization & Structure

Ledger uses a two-tier SQLite database structure to decouple user authentication data from academic and system records.

### 1. Authentication Database (`databases/auth.db`)

Manages security details and account states.

#### `users` Table
Stores login credentials, system authority clearance level, and account status metrics.
- `id` (INTEGER, Primary Key, Auto-increment): Unique User ID.
- `email` (TEXT, Unique): User's registration email address.
- `password` (TEXT): Cryptographically hashed password (using SHA-256).
- `status` (INTEGER): Core account type (e.g., `1` for Student, `7` for Professor, `2-6` for Admin).
- `approved` (INTEGER): Whether account is approved by admin (`0` or `1`).
- `state` (INTEGER): Account status state (`0` for Active, `1` for Restricted, `2` for Banned).
- `warning_count` (INTEGER): Total count of official warnings issued.
- `token` (TEXT): Session recovery token for password resets.
- `token_created_at` (DATETIME): Expiry timestamp for token verification.

---

### 2. Main System Database (`databases/main.db`)

Manages all user profiles, academic records, and transactional content.

#### `profiles` Table
Stores metadata for users (corresponds to `auth.db` user IDs).
- `p_id` (INTEGER, Primary Key): References `users.id` in `auth.db`.
- `name` (TEXT): Display name.
- `avatar` (TEXT): URL or static path to profile image.
- `email` (TEXT): Display email.
- `current_year` (INTEGER): Student academic year (1-4).
- `current_semester` (INTEGER): Current semester (1-2).
- `gpa` (REAL): Current cumulative GPA.

#### `professors` Table
Stores faculty-specific profiles.
- `user_id` (INTEGER, Primary Key): References `users.id` / `profiles.p_id`.
- `department` (TEXT): Academic department (e.g., Computer Science).
- `office` (TEXT): Office room number.
- `name` (TEXT): Display name.

#### `subjects` Table
- `id` (INTEGER, Primary Key, Auto-increment)
- `name` (TEXT): Subject title.
- `code` (TEXT, Unique): Unique course code (e.g., CS50).
- `description` (TEXT): Course overview.
- `year` (INTEGER): Recommended study year.
- `semester` (INTEGER): Recommended semester.
- `credits` (INTEGER): Subject credit weight.
- `professor_id` (INTEGER): References `professors.user_id`.
- `visibility` (TEXT): `'public'` or `'private'`.
- `created_by` (INTEGER): References creator.
- `sts` (TEXT): Subject status (`'active'`, `'archived'`).
- `accepted` (INTEGER): Approval state.

#### `materials` Table
- `id` (INTEGER, Primary Key, Auto-increment)
- `subject_id` (INTEGER): References `subjects.id`.
- `title` (TEXT)
- `content` (TEXT): Material link, description, or text.
- `created_by` (INTEGER): Uploading user's ID.
- `visibility` (TEXT): `'public'` or `'private'`.
- `accepted` (INTEGER): Whether approved by moderation.

#### `assignments` Table
- `id` (INTEGER, Primary Key, Auto-increment)
- `subject_id` (INTEGER): References `subjects.id`.
- `year` / `semester` (INTEGER): Target year and semester.
- `title` / `description` (TEXT): Assignment metadata.
- `visibility` (TEXT)

#### `ratings` Table
- `id` (INTEGER, Primary Key, Auto-increment)
- `p_id` (INTEGER): References profile.
- `entity_type` (TEXT): `'subject'`, `'material'`, `'assignment'`, `'professor'`.
- `entity_id` (INTEGER): Target record ID.
- `raw_score` (INTEGER): 1 to 5 rating score.
- `difficulty` (INTEGER): 1 to 5 course difficulty score.
- `gpa_at_vote` (REAL): Voter's GPA at submission.
- *Constraint*: `UNIQUE(p_id, entity_type, entity_id)`

#### `student_notes` Table
- `id` (INTEGER, Primary Key, Auto-increment)
- `title` (TEXT)
- `p_id` (INTEGER): Creator profile ID.
- `entity_type` (TEXT): `'subject'` or `'material'`.
- `entity_id` (INTEGER): Associated ID.
- `content` (TEXT): Raw markdown or plain note text.
- `is_public` (INTEGER): Public visibility flag.
- `accepted` (INTEGER): Public publication approval flag.

#### `student_favorites` Table
- `p_id`, `entity_type`, `entity_id` tracking bookmarks.

#### `history` Table
- `p_id`, `entity_type` (`'subject'`, `'material'`, `'assignment'`), `entity_id` tracking browsing activity.

#### `events` Table
- Calendar scheduling data.

#### `notifications` Table
- User-targeted notifications.

#### `direct_messages` Table
- `sender_id`, `receiver_id`, `content`, `is_read`, `created_at` for messaging chat records.

#### `discussion_posts` Table
- `subject_id`, `user_id`, `title`, `content` for subject forums.

#### `reports` Table
- Moderation reports submitted against items.

---

## 🛠️ Key Improvements & Fixes Applied

1. **Jinja Context Processor for `UserSession`**:
   Registered a context processor in `app.py` returning `dict(UserSession=UserSession)`, ensuring `UserSession` is available globally in every HTML template (resolves 403/404 error page crashes).
2. **Flattened and Filtered Favorites**:
   Updated the `/favorites` route to filter by query args and correctly flatten the database categories (subjects, materials, professors, assignments) into a flat list of normalized items. Fixed `templates/favorites/index.html` to iterate directly over `data` instead of broken dictionary `data.values()`.
3. **Robust Subject Existence Guarding**:
   Added validation to `subject_materials` and `subject_calendar` routes to check for `subjects.get_subject_overview` presence, returning HTTP 404 cleanly instead of raising template internal exceptions (500) on non-existent or deleted IDs.
4. **Resolved SQL Helper Iterator**:
   Fixed `DictionaryResult.__iter__` in `modules/sql_helper_dictionary.py` to yield the row dictionary directly instead of wrapping every row in an index-tuple, correcting all table listings, note trees, and administration panels.
5. **Fixed History Check Constraint**:
   Removed `professor` tracking from `history.record_visit` call in `app.py` since the database `history` table restricts `entity_type` specifically to `'subject'`, `'material'`, or `'assignment'`.
