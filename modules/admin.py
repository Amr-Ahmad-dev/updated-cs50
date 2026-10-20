import sqlite3
import modules.sql_helper_dictionary as sql_h

def get_dashboard_stats():
    """Returns overview metrics for the admin dashboard."""
    stats = {
        "total_users": 0,
        "active_students": 0,
        "professors": 0,
        "admins": 0,
        "warned_users": 0,
        "banned_users": 0,
        "total_subjects": 0,
        "pending_subjects": 0,
        "total_materials": 0,
        "pending_materials": 0,
        "pending_notes": 0,
        "total_events": 0,
        "total_reports": 0,
    }
    try:
        with sql_h.get_db("auth.db") as auth_conn:
            c = auth_conn.cursor()
            c.execute("SELECT COUNT(*) as c FROM users")
            row = c.fetchone()
            stats["total_users"] = row["c"] if row else 0

            c.execute("SELECT COUNT(*) as c FROM users WHERE status = 1 AND state = 0")
            row = c.fetchone()
            stats["active_students"] = row["c"] if row else 0

            c.execute("SELECT COUNT(*) as c FROM users WHERE status = 7")
            row = c.fetchone()
            stats["professors"] = row["c"] if row else 0

            c.execute("SELECT COUNT(*) as c FROM users WHERE status >= 2 AND status <= 6")
            row = c.fetchone()
            stats["admins"] = row["c"] if row else 0

            c.execute("SELECT COUNT(*) as c FROM users WHERE state = 1")
            row = c.fetchone()
            stats["warned_users"] = row["c"] if row else 0

            c.execute("SELECT COUNT(*) as c FROM users WHERE state = 2")
            row = c.fetchone()
            stats["banned_users"] = row["c"] if row else 0

        with sql_h.get_db("main.db") as main_conn:
            c = main_conn.cursor()
            c.execute("SELECT COUNT(*) as c FROM subjects")
            row = c.fetchone()
            stats["total_subjects"] = row["c"] if row else 0

            c.execute("SELECT COUNT(*) as c FROM subjects WHERE accepted = 0")
            row = c.fetchone()
            stats["pending_subjects"] = row["c"] if row else 0

            c.execute("SELECT COUNT(*) as c FROM materials")
            row = c.fetchone()
            stats["total_materials"] = row["c"] if row else 0

            c.execute("SELECT COUNT(*) as c FROM materials WHERE accepted = 0")
            row = c.fetchone()
            stats["pending_materials"] = row["c"] if row else 0

            c.execute("SELECT COUNT(*) as c FROM student_notes WHERE is_public = 1 AND accepted = 0")
            row = c.fetchone()
            stats["pending_notes"] = row["c"] if row else 0

            c.execute("SELECT COUNT(*) as c FROM events")
            row = c.fetchone()
            stats["total_events"] = row["c"] if row else 0

            c.execute("SELECT COUNT(*) as c FROM reports WHERE status = 'pending'")
            row = c.fetchone()
            stats["total_reports"] = row["c"] if row else 0

    except Exception as e:
        print(f"Error fetching dashboard stats: {e}")
    return stats


def list_users(query_filters=None):
    """Lists users combined with profile data, filtered by authority/state if requested."""
    try:
        users = []
        with sql_h.get_db("auth.db") as auth_conn:
            c = auth_conn.cursor()
            query = "SELECT id, email, status, approved, state, warning_count FROM users WHERE 1=1"
            params = []
            if query_filters:
                if query_filters.get("authority"):
                    query += " AND status = ?"
                    params.append(int(query_filters["authority"]))
                if query_filters.get("state") is not None and query_filters.get("state") != "":
                    query += " AND state = ?"
                    params.append(int(query_filters["state"]))
            query += " ORDER BY id ASC"
            c.execute(query, tuple(params))
            auth_users = [dict(u) for u in c.fetchall()]

        # Attach profile info
        with sql_h.get_db("main.db") as main_conn:
            c = main_conn.cursor()
            for u in auth_users:
                c.execute("SELECT * FROM profiles WHERE p_id = ?", (u["id"],))
                prof = c.fetchone()
                if prof:
                    u["name"] = prof["name"] or u["email"].split("@")[0]
                    u["avatar"] = prof["avatar"] or ""
                    u["current_year"] = prof["current_year"]
                    u["current_semester"] = prof["current_semester"]
                    u["average_gpa"] = prof["average_gpa"]
                else:
                    u["name"] = u["email"].split("@")[0]
                    u["avatar"] = ""
                    u["current_year"] = None
                    u["current_semester"] = None
                    u["average_gpa"] = None
                users.append(u)
        return users
    except Exception as e:
        print(f"Error listing users: {e}")
        return []


def get_user(user_id):
    """Retrieves full details for an individual user, including moderation history."""
    try:
        user = None
        with sql_h.get_db("auth.db") as auth_conn:
            c = auth_conn.cursor()
            c.execute("SELECT id, email, status, approved, state, warning_count FROM users WHERE id = ?", (user_id,))
            row = c.fetchone()
            if not row:
                return None
            user = dict(row)
            user["authority"] = user["status"]

        with sql_h.get_db("main.db") as main_conn:
            c = main_conn.cursor()
            c.execute("SELECT * FROM profiles WHERE p_id = ?", (user_id,))
            prof = c.fetchone()
            if prof:
                user["profile"] = dict(prof)
                user["name"] = prof["name"] or user["email"].split("@")[0]
                user["avatar"] = prof["avatar"] or ""
            else:
                user["profile"] = {}
                user["name"] = user["email"].split("@")[0]
                user["avatar"] = ""

            # Moderation logs targeting this user
            c.execute("""
                SELECT m.*, p.name as actor_name, p.email as actor_email
                FROM moderation_log m
                LEFT JOIN profiles p ON m.actor_p_id = p.p_id
                WHERE m.target_p_id = ?
                ORDER BY m.created_at DESC
            """, (user_id,))
            user["logs"] = [dict(log) for log in c.fetchall()]

        return user
    except Exception as e:
        print(f"Error getting user detail: {e}")
        return None


def list_pending_subjects():
    """Lists all subjects submitted by students/professors waiting for admin approval."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                SELECT s.*, p.name as creator_name, p.email as creator_email
                FROM subjects s
                LEFT JOIN profiles p ON s.created_by = p.p_id
                WHERE s.accepted = 0
                ORDER BY s.created_at ASC
            """)
            return [dict(row) for row in c.fetchall()]
    except Exception as e:
        print(f"Error listing pending subjects: {e}")
        return []


def approve_subject(subject_id, admin_user_id):
    """Approves a pending subject and activates it."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
            subject = c.fetchone()
            if not subject:
                return False, "Subject not found."

            c.execute("""
                UPDATE subjects 
                SET accepted = 1, sts = 'active', updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (subject_id,))

            c.execute("""
                INSERT INTO content_moderation_log (actor_p_id, entity_type, entity_id, action, reason)
                VALUES (?, 'subject', ?, 'accept', 'Subject approved by administrator')
            """, (admin_user_id, subject_id))

            if subject["created_by"]:
                c.execute("""
                    INSERT INTO notifications (p_id, type, message, send_to_year, send_to_semester)
                    VALUES (?, 'approval', ?, 0, 0)
                """, (subject["created_by"], f"Your subject '{subject['name']}' has been approved and published!"))

            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error approving subject: {e}")
        return False, str(e)


def list_pending_materials():
    """Lists materials uploaded by students waiting for admin approval."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                SELECT m.*, s.name as subject_name, s.code as subject_code, p.name as uploader_name, p.email as uploader_email
                FROM materials m
                LEFT JOIN subjects s ON m.subject_id = s.id
                LEFT JOIN profiles p ON m.uploaded_by = p.p_id
                WHERE m.accepted = 0
                ORDER BY m.created_at ASC
            """)
            return [dict(row) for row in c.fetchall()]
    except Exception as e:
        print(f"Error listing pending materials: {e}")
        return []


def approve_material(material_id, admin_user_id):
    """Approves an uploaded material."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
            mat = c.fetchone()
            if not mat:
                return False, "Material not found."

            c.execute("""
                UPDATE materials 
                SET accepted = 1, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (material_id,))

            c.execute("""
                INSERT INTO content_moderation_log (actor_p_id, entity_type, entity_id, action, reason)
                VALUES (?, 'material', ?, 'accept', 'Material approved by administrator')
            """, (admin_user_id, material_id))

            if mat["uploaded_by"]:
                c.execute("""
                    INSERT INTO notifications (p_id, type, message, send_to_year, send_to_semester)
                    VALUES (?, 'approval', ?, 0, 0)
                """, (mat["uploaded_by"], f"Your material '{mat['title']}' has been approved and is now live!"))

            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error approving material: {e}")
        return False, str(e)


def list_pending_notes():
    """Lists notes submitted for publication waiting for admin approval."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                SELECT n.*, p.name as author_name, p.email as author_email,
                       CASE WHEN n.entity_type = 'subject' THEN s.name ELSE m.title END as entity_name
                FROM student_notes n
                LEFT JOIN profiles p ON n.p_id = p.p_id
                LEFT JOIN subjects s ON (n.entity_type = 'subject' AND n.entity_id = s.id)
                LEFT JOIN materials m ON (n.entity_type = 'material' AND n.entity_id = m.id)
                WHERE n.is_public = 1 AND n.accepted = 0
                ORDER BY n.created_at ASC
            """)
            return [dict(row) for row in c.fetchall()]
    except Exception as e:
        print(f"Error listing pending notes: {e}")
        return []


def approve_note(note_id, admin_user_id):
    """Approves a public note."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM student_notes WHERE id = ?", (note_id,))
            note = c.fetchone()
            if not note:
                return False, "Note not found."

            c.execute("""
                UPDATE student_notes 
                SET accepted = 1, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (note_id,))

            c.execute("""
                INSERT INTO content_moderation_log (actor_p_id, entity_type, entity_id, action, reason)
                VALUES (?, 'note', ?, 'accept', 'Note approved for public view')
            """, (admin_user_id, note_id))

            c.execute("""
                INSERT INTO notifications (p_id, type, message, send_to_year, send_to_semester)
                VALUES (?, 'approval', ?, 0, 0)
            """, (note["p_id"], f"Your note '{note['title'] or 'Note'}' was approved and is now public!"))

            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error approving note: {e}")
        return False, str(e)


def list_reports():
    """Lists student reports / flagged items."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                SELECT r.*, p.name as reporter_name, p.email as reporter_email
                FROM reports r
                LEFT JOIN profiles p ON r.reporter_id = p.p_id
                ORDER BY r.created_at DESC
            """)
            return [dict(row) for row in c.fetchall()]
    except Exception as e:
        print(f"Error listing reports: {e}")
        return []


def list_logs():
    """Lists audit logs combining user moderation and content moderation."""
    logs = []
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                SELECT m.id, m.action, m.reason, m.created_at, 'user' as log_type,
                       p1.name as actor_name, p1.email as actor_email,
                       p2.name as target_name, p2.email as target_email
                FROM moderation_log m
                LEFT JOIN profiles p1 ON m.actor_p_id = p1.p_id
                LEFT JOIN profiles p2 ON m.target_p_id = p2.p_id
                ORDER BY m.created_at DESC LIMIT 100
            """)
            user_logs = [dict(r) for r in c.fetchall()]

            c.execute("""
                SELECT c.id, c.action, c.reason, c.created_at, c.entity_type as log_type,
                       p.name as actor_name, p.email as actor_email,
                       ('Entity #' || c.entity_id) as target_name, '' as target_email
                FROM content_moderation_log c
                LEFT JOIN profiles p ON c.actor_p_id = p.p_id
                ORDER BY c.created_at DESC LIMIT 100
            """)
            content_logs = [dict(r) for r in c.fetchall()]

            logs = sorted(user_logs + content_logs, key=lambda x: x["created_at"], reverse=True)
    except Exception as e:
        print(f"Error listing logs: {e}")
    return logs
