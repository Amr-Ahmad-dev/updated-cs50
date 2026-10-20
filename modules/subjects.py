import modules.sql_helper_dictionary as sql_helper
import modules.favorites as favorites

def list_subjects(user_id=None, filters=None):
    """Lists subjects with filters, average ratings, and professor details."""
    try:
        with sql_helper.get_db("main.db") as conn:
            cursor = conn.cursor()
            query = """
                SELECT s.*, 
                       p.name as professor_name,
                       (SELECT AVG(raw_score) FROM ratings WHERE entity_type = 'subject' AND entity_id = s.id) as avg_rating,
                       (SELECT COUNT(*) FROM materials WHERE subject_id = s.id AND accepted = 1) as material_count,
                       (SELECT COUNT(*) FROM assignments WHERE subject_id = s.id) as assignment_count
                FROM subjects s
                LEFT JOIN profiles p ON s.professor_id = p.p_id
                WHERE 1=1
            """
            params = {}

            if filters:
                if filters.get("professor_profile_id"):
                    query += " AND s.professor_id = :prof_id"
                    params["prof_id"] = filters["professor_profile_id"]
                if filters.get("subject_name"):
                    query += " AND s.name LIKE :subject_name"
                    params["subject_name"] = f"%{filters['subject_name']}%"
                if filters.get("professor_name"):
                    query += " AND p.name LIKE :professor_name"
                    params["professor_name"] = f"%{filters['professor_name']}%"
                if filters.get("subject_code"):
                    query += " AND s.code LIKE :subject_code"
                    params["subject_code"] = f"%{filters['subject_code']}%"
                if filters.get("year") and str(filters.get("year")).isdigit():
                    query += " AND s.year = :year"
                    params["year"] = int(filters["year"])
                if filters.get("semester") and str(filters.get("semester")).isdigit():
                    query += " AND s.semester = :semester"
                    params["semester"] = int(filters["semester"])

            # Default: show public and accepted subjects, or subjects created by user
            if user_id:
                query += " AND (s.accepted = 1 OR s.created_by = :user_id)"
                params["user_id"] = user_id
            else:
                query += " AND s.accepted = 1"

            query += " ORDER BY s.year ASC, s.semester ASC, s.name ASC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error occurred while listing subjects: {e}")
        return []


def get_subject_overview(subject_id, user_id=None):
    """Retrieves full overview information for a subject."""
    try:
        with sql_helper.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, 
                       p.name as professor_name, p.avatar as professor_avatar, p.email as professor_email,
                       (SELECT AVG(raw_score) FROM ratings WHERE entity_type = 'subject' AND entity_id = s.id) as avg_rating,
                       (SELECT AVG(difficulty) FROM ratings WHERE entity_type = 'subject' AND entity_id = s.id) as avg_difficulty,
                       (SELECT COUNT(*) FROM ratings WHERE entity_type = 'subject' AND entity_id = s.id) as rating_count,
                       (SELECT COUNT(*) FROM materials WHERE subject_id = s.id AND accepted = 1) as material_count,
                       (SELECT COUNT(*) FROM assignments WHERE subject_id = s.id) as assignment_count,
                       (SELECT COUNT(*) FROM subject_prerequisites WHERE subject_id = s.id) as prerequisite_count,
                       (SELECT COUNT(*) FROM student_notes WHERE entity_type = 'subject' AND entity_id = s.id AND is_public = 1 AND accepted = 1) as public_notes_count
                FROM subjects s
                LEFT JOIN profiles p ON s.professor_id = p.p_id
                WHERE s.id = :subject_id
            """, {"subject_id": subject_id})
            row = cursor.fetchone()
            if not row:
                return None
            subject = dict(row)
            
            # Format averages
            if subject.get("avg_rating"):
                subject["avg_rating"] = round(subject["avg_rating"], 1)
            if subject.get("avg_difficulty"):
                subject["avg_difficulty"] = round(subject["avg_difficulty"], 1)

            # Check favorite
            subject["is_favorite"] = False
            if user_id:
                subject["is_favorite"] = favorites.is_favorite(user_id, subject_id, "subject")

            # Get recent preview materials & assignments
            cursor.execute("""
                SELECT * FROM materials 
                WHERE subject_id = ? AND accepted = 1 
                ORDER BY created_at DESC LIMIT 3
            """, (subject_id,))
            subject["preview_materials"] = [dict(r) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT * FROM assignments 
                WHERE subject_id = ? 
                ORDER BY created_at DESC LIMIT 3
            """, (subject_id,))
            subject["preview_assignments"] = [dict(r) for r in cursor.fetchall()]

            return subject
    except Exception as e:
        print(f"Error occurred while fetching subject overview: {e}")
        return None


def create_subject(subject_data, user_authority, user_id):
    """Creates a new subject with validation and notifications."""
    try:
        s_name = (subject_data.get("subject_name") or subject_data.get("name") or "").strip()
        s_code = (subject_data.get("subject_code") or subject_data.get("code") or "").strip().upper()
        year = subject_data.get("year")
        semester = subject_data.get("semester")
        credits = subject_data.get("credits") or 3
        description = subject_data.get("description", "")
        professor_id = subject_data.get("professor_id")
        if professor_id and str(professor_id).isdigit():
            professor_id = int(professor_id)
        else:
            professor_id = None

        if not s_name or not s_code or not year or not semester:
            return False, "Name, code, year, and semester are required fields.", None

        is_admin_or_prof = user_authority and int(user_authority) >= 2
        status = "active" if is_admin_or_prof else "archived"
        accepted = 1 if is_admin_or_prof else 0

        with sql_helper.get_db("main.db") as conn:
            cursor = conn.cursor()
            
            # Check unique code
            cursor.execute("SELECT id FROM subjects WHERE code = ?", (s_code,))
            if cursor.fetchone():
                return False, f"Subject code '{s_code}' already exists.", None

            cursor.execute("""
                INSERT INTO subjects (name, code, description, year, semester, credits, professor_id, visibility, created_by, sts, accepted)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'public', ?, ?, ?)
            """, (s_name, s_code, description, int(year), int(semester), int(credits), professor_id, user_id, status, accepted))

            subject_id = cursor.lastrowid

            if accepted == 1:
                cursor.execute("""
                    INSERT INTO notifications (message, type, send_to_year, send_to_semester)
                    VALUES (?, 'announcement', 0, 0)
                """, (f"New course offering: '{s_code} - {s_name}' is now active!",))
            else:
                cursor.execute("""
                    INSERT INTO notifications (p_id, message, type, send_to_year, send_to_semester)
                    VALUES (?, ?, 'notification', 0, 0)
                """, (user_id, f"Subject submission '{s_name}' has been received and is waiting for admin approval."))

            conn.commit()
            return True, None, subject_id
    except Exception as e:
        print(f"Error creating subject: {e}")
        return False, str(e), None


def edit_subject(subject_id, form_data):
    """Updates subject information."""
    try:
        s_name = (form_data.get("name") or form_data.get("subject_name") or "").strip()
        s_code = (form_data.get("code") or form_data.get("subject_code") or "").strip().upper()
        description = form_data.get("description", "").strip()
        year = form_data.get("year")
        semester = form_data.get("semester")
        credits = form_data.get("credits") or 3
        professor_id = form_data.get("professor_id")
        links = form_data.get("links", "")
        conditions = form_data.get("conditions_for_enrollment", "")

        if professor_id and str(professor_id).isdigit():
            professor_id = int(professor_id)
        else:
            professor_id = None

        with sql_helper.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE subjects 
                SET name = ?, code = ?, description = ?, year = ?, semester = ?, credits = ?, 
                    professor_id = ?, links = ?, conditions_for_enrollment = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (s_name, s_code, description, int(year), int(semester), int(credits), professor_id, links, conditions, subject_id))
            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error editing subject: {e}")
        return False, str(e)


def delete_subject(subject_id):
    """Deletes a subject from the catalog."""
    try:
        with sql_helper.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error deleting subject: {e}")
        return False, str(e)