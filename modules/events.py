import modules.sql_helper_dictionary as sql_h
import modules.profile as profile

def list_events(user_id: int = None, limit: int = None, status: str = None):
    """Lists calendar events targeted to user or global to all students."""
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            
            grade = 0
            semester = 0
            if user_id:
                prof = profile.get_profile(user_id)
                if prof:
                    grade = prof.get("current_year") or 0
                    semester = prof.get("current_semester") or 0

            query = """
                SELECT e.*, s.name as subject_name, s.code as subject_code, p.name as creator_name
                FROM events e
                LEFT JOIN subjects s ON e.subject_id = s.id
                LEFT JOIN profiles p ON e.created_by = p.p_id
                WHERE 1=1
            """
            params = []

            if status:
                query += " AND e.status = ?"
                params.append(status)

            if user_id:
                query += """
                    AND (
                        e.p_id = ? OR e.p_id IS NULL
                    )
                """
                params.append(user_id)

            query += " ORDER BY e.event_date ASC, e.created_at DESC"
            if limit:
                query += f" LIMIT {int(limit)}"

            cursor.execute(query, tuple(params))
            return [dict(r) for r in cursor.fetchall()]
    except Exception as e:
        print(f"Error occurred while listing events: {e}")
        return []


def create_event(user_id: int, form_data: dict):
    """Creates a new calendar event with date, title, description, and link."""
    try:
        title = (form_data.get("title") or "").strip()
        description = (form_data.get("description") or "").strip()
        url = (form_data.get("url") or "").strip()
        event_date = form_data.get("event_date") or None
        grade = form_data.get("grade") or 1
        semester = form_data.get("semester") or 1
        subject_id = form_data.get("subject_id")
        status = form_data.get("status") or "upcoming"

        if not title:
            return False, "Event title is required.", None

        if subject_id and str(subject_id).isdigit():
            subject_id = int(subject_id)
        else:
            subject_id = None

        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (title, description, url, event_date, grade, semester, subject_id, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, description, url, event_date, int(grade), int(semester), subject_id, status, user_id))
            
            event_id = cursor.lastrowid

            # Broadcast notification
            cursor.execute("""
                INSERT INTO notifications (message, type, send_to_year, send_to_semester)
                VALUES (?, 'event', ?, ?)
            """, (f"New Event: '{title}' on {event_date or 'upcoming schedule'}", int(grade), int(semester)))

            conn.commit()
            return True, None, event_id
    except Exception as e:
        print(f"Error creating event: {e}")
        return False, str(e), None


def get_event(event_id: int):
    """Retrieves full details for a single event."""
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.*, s.name as subject_name, s.code as subject_code, p.name as creator_name
                FROM events e
                LEFT JOIN subjects s ON e.subject_id = s.id
                LEFT JOIN profiles p ON e.created_by = p.p_id
                WHERE e.id = ?
            """, (event_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"Error fetching event: {e}")
        return None