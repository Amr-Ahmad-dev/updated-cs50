import sqlite3
import os

os.makedirs("databases", exist_ok=True)

# ── Auth Database ─────────────────────────────────────────────
# Only auth-scoped tables live here. moderation_log stays out of this
# file (see main.db below) because it targets profiles(p_id), and
# profiles lives in main.db — SQLite can't enforce a FOREIGN KEY across
# two separate database files/connections.
#
# CHANGES this pass:
#   - added `approved`: gates login for admin/professor signups that
#     are pending approval (status > 1). Students default to approved.
#   - replaced the old ambiguous `state` default with an explicit
#     0/1/2 meaning: 0 = active, 1 = warned, 2 = banned. Login must
#     check this before letting a session start.
#   - added `warning_count`: cached counter, kept in sync with
#     main.db.moderation_log by the same operation that logs a warn/ban
#     action, so login doesn't need a cross-database join on every
#     request just to show the warning banner.
with sqlite3.connect("databases/auth.db") as conn:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            email          TEXT    NOT NULL UNIQUE,
            password       TEXT    NOT NULL,
            status         INTEGER NOT NULL CHECK(status BETWEEN 1 AND 7),
            approved       INTEGER NOT NULL DEFAULT 1 CHECK(approved IN (0,1)),
            state          INTEGER NOT NULL DEFAULT 0 CHECK(state IN (0,1,2)),
            warning_count  INTEGER NOT NULL DEFAULT 0,
            token           TEXT,
            token_created_at DATETIME
        );

        CREATE INDEX IF NOT EXISTS idx_auth_users_state ON users(state);
    """)
    print("auth.db created successfully")


# ── Main Database ─────────────────────────────────────────────
# Tables are ordered so every REFERENCES target already exists, and
# every index is created after its table.
#
# CHANGES this pass:
#   - subjects: added `accepted`, the missing toggle for admin
#     accept/reject-subject workflows (materials already had this).
#   - student_grades: added optional `hours_studied`.
#   - student_notes: made polymorphic (entity_type/entity_id) instead
#     of subject-only, so a note can attach to a subject OR a material.
#   - new table `events`: admin-uploaded events with a clickable URL.
#   - new table `notifications`: backs the notification bar/page
#     (e.g. "your admin request is pending review").
#   - new table `content_moderation_log`: accept/reject/delete actions
#     on subjects/materials. Kept separate from moderation_log, which
#     targets a *person* (warn/ban/unban) — these are different kinds
#     of actions with different target shapes, and conflating them
#     would overload target_p_id with two unrelated meanings.


with sqlite3.connect("databases/main.db") as conn:
    # 1. Enable Foreign Key Enforcement
    conn.execute("PRAGMA foreign_keys = ON;")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
            p_id INTEGER PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            name TEXT,
            age INTEGER,
            bio TEXT,
            avatar TEXT,
            average_gpa REAL,
            current_year INTEGER,
            current_semester INTEGER
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            p_id INTEGER REFERENCES profiles(p_id) ON DELETE CASCADE,
            token TEXT,
            token_created_at DATETIME
        );

        CREATE TABLE IF NOT EXISTS professors (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            office TEXT,
            department TEXT,
            bio TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT,
            year INTEGER NOT NULL CHECK(year BETWEEN 1 AND 4),
            semester INTEGER NOT NULL CHECK(semester BETWEEN 1 AND 2),
            credits INTEGER NOT NULL CHECK(credits > 0),
            professor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            links TEXT,
            conditions_for_enrollment TEXT,
            visibility TEXT NOT NULL DEFAULT 'public' CHECK(visibility IN ('public','private')),
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            sts TEXT NOT NULL CHECK(sts IN ('active','inactive','archived')),
            accepted INTEGER NOT NULL DEFAULT 0 CHECK(accepted IN (0,1)),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS subject_prerequisites (
            subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            prerequisite_subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            PRIMARY KEY (subject_id, prerequisite_subject_id)
        );

        CREATE TABLE IF NOT EXISTS student_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            p_id INTEGER NOT NULL REFERENCES profiles(p_id) ON DELETE CASCADE,
            sub_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            UNIQUE(p_id, sub_id)
        );

        CREATE TABLE IF NOT EXISTS professor_subjects (
            professor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            PRIMARY KEY (professor_id, subject_id)
        );

        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            uploaded_by INTEGER NOT NULL REFERENCES users(id) on DELETE SET NULL,
            title TEXT NOT NULL,
            description TEXT,
            file_path TEXT NOT NULL DEFAULT '',
            material_type TEXT NOT NULL CHECK(material_type IN (
                'video', 'document', 'presentation', 'image', 'audio', 'other'
            )),
            content_type TEXT NOT NULL CHECK(content_type IN (
                'official', 'non-official', 'not_official' -- Accepts both naming conventions
            )),
            visibility TEXT NOT NULL DEFAULT 'public' CHECK(visibility IN ('public','private')),
            accepted INTEGER NOT NULL DEFAULT 0 CHECK(accepted IN (0,1)),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(subject_id, title)
        );

        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            year INTEGER NOT NULL CHECK(year BETWEEN 1 AND 4),
            semester INTEGER NOT NULL CHECK(semester BETWEEN 1 AND 2),
            title TEXT NOT NULL,
            description TEXT,
            visibility TEXT NOT NULL DEFAULT 'public' CHECK(visibility IN ('public','private')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS student_grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            p_id INTEGER NOT NULL REFERENCES profiles(p_id) ON DELETE CASCADE,
            subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            year INTEGER NOT NULL CHECK(year BETWEEN 1 AND 4),
            semester INTEGER NOT NULL CHECK(semester BETWEEN 1 AND 2),
            letter TEXT CHECK(letter IN ('A','B','C','D','F')),
            grade REAL NOT NULL CHECK(grade BETWEEN 0.0 AND 4.0),
            hours_studied REAL CHECK(hours_studied >= 0),
            UNIQUE(p_id, subject_id, year, semester)
        );

        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            p_id INTEGER NOT NULL REFERENCES profiles(p_id) ON DELETE CASCADE,
            entity_type TEXT NOT NULL CHECK(entity_type IN ('subject', 'material', 'assignment', 'professor')),
            entity_id INTEGER NOT NULL,
            raw_score INTEGER NOT NULL CHECK(raw_score BETWEEN 1 AND 5),
            difficulty INTEGER CHECK(difficulty BETWEEN 1 AND 5),
            gpa_at_vote REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(p_id, entity_type, entity_id)
        );

        CREATE TABLE IF NOT EXISTS student_material_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            p_id INTEGER NOT NULL REFERENCES profiles(p_id) ON DELETE CASCADE,
            material_id INTEGER NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
            progress TEXT,
            last_position INTEGER DEFAULT 0,
            last_visited DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(p_id, material_id)
        );

        CREATE TABLE IF NOT EXISTS student_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL DEFAULT '',
            p_id INTEGER NOT NULL REFERENCES profiles(p_id) ON DELETE CASCADE,
            entity_type TEXT NOT NULL CHECK(entity_type IN ('subject', 'material')),
            entity_id INTEGER,
            content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS student_favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            p_id INTEGER NOT NULL REFERENCES profiles(p_id) ON DELETE CASCADE,
            entity_type TEXT NOT NULL CHECK(entity_type IN ('subject', 'material', 'professor', 'assignment')),
            entity_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(p_id, entity_type, entity_id)
        );

        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            p_id INTEGER NOT NULL REFERENCES profiles(p_id) ON DELETE CASCADE,
            entity_type TEXT NOT NULL CHECK(entity_type IN ('subject', 'material', 'assignment')),
            entity_id INTEGER NOT NULL,
            visited_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS moderation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_p_id INTEGER NOT NULL REFERENCES profiles(p_id),
            target_p_id INTEGER NOT NULL REFERENCES profiles(p_id),
            action TEXT NOT NULL CHECK(action IN ('warn','restrict','ban','unban')),
            reason TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS content_moderation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_p_id INTEGER NOT NULL REFERENCES profiles(p_id),
            entity_type TEXT NOT NULL CHECK(entity_type IN ('subject', 'material')),
            entity_id INTEGER NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('accept','reject','delete')),
            reason TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            p_id INTEGER REFERENCES profiles(p_id) ON DELETE CASCADE,
            grade INTEGER NOT NULL CHECK(grade BETWEEN 1 AND 4),
            semester INTEGER NOT NULL CHECK(semester BETWEEN 1 AND 2),
            subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
            status TEXT NOT NULL CHECK(status IN ('upcoming','ongoing','completed')),
            user_type INTEGER CHECK(user_type IN (1,2,3,4,5,6,7)),
            title TEXT NOT NULL,
            description TEXT,
            url TEXT NOT NULL,
            event_date DATETIME,
            created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            s_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            send_to_year INTEGER NOT NULL CHECK(send_to_year BETWEEN 0 AND 4),
            send_to_semester INTEGER NOT NULL CHECK(send_to_semester BETWEEN 0 AND 2),
            send_to_user_type INTEGER CHECK(send_to_user_type IN (1,2,3,4,5,6,7)),
            p_id INTEGER REFERENCES profiles(p_id) ON DELETE CASCADE, -- Fixed to reference profiles
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0 CHECK(is_read IN (0,1)),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- INDEXES
        CREATE INDEX IF NOT EXISTS idx_student_subjects_pid ON student_subjects(p_id);
        CREATE INDEX IF NOT EXISTS idx_ratings_entity ON ratings(entity_type, entity_id);
        CREATE INDEX IF NOT EXISTS idx_materials_subject ON materials(subject_id);
        CREATE INDEX IF NOT EXISTS idx_materials_uploaded_by ON materials(uploaded_by);
        CREATE INDEX IF NOT EXISTS idx_grades_pid ON student_grades(p_id);
        CREATE INDEX IF NOT EXISTS idx_notes_entity ON student_notes(entity_type, entity_id);
        CREATE INDEX IF NOT EXISTS idx_favorites_pid ON student_favorites(p_id);
        CREATE INDEX IF NOT EXISTS idx_history_pid ON history(p_id);
        CREATE INDEX IF NOT EXISTS idx_moderation_target ON moderation_log(target_p_id);
        CREATE INDEX IF NOT EXISTS idx_content_moderation_entity ON content_moderation_log(entity_type, entity_id);
        CREATE INDEX IF NOT EXISTS idx_notifications_pid ON notifications(p_id, is_read);
        CREATE INDEX IF NOT EXISTS idx_subjects_accepted ON subjects(accepted);
    """)
    print("main.db schema created successfully")
print("All databases ready.")