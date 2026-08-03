

import modules.sql_helper_dictionary as sql_h
import modules.profile as profile

def list_events(user_id, limit=None,status=1):
    conn1 = None
    try:
        with sql_h.get_db("main.db") as conn1:
            grade = None
            semester = None
            cursor1 = conn1.cursor()
            if limit is not None:
                cursor1.execute("SELECT * FROM events WHERE p_id=? AND status=? ORDER BY id DESC LIMIT ?", (user_id, status, limit))
            else:    
                cursor1.execute("SELECT * FROM events WHERE p_id=? AND status=? ORDER BY id DESC", (user_id, status))
            user_events = cursor1.fetchall()
            profile_data = profile.get_profile(user_id)
            if profile_data is not None:
                grade = profile_data.get("grade")
                semester = profile_data.get("semester")
            cursor1.execute("""
                SELECT *
                FROM events
                WHERE p_id IS NULL
                AND (status = ? OR status IS NULL)
                AND (grade = ? OR grade IS NULL)
                AND (semester = ? OR semester IS NULL)
                AND (subject_id IN (SELECT subject_id FROM student_subjects WHERE p_id = ?) OR subject_id IS NULL)
            """, (status, grade, semester, user_id))
            global_events = cursor1.fetchall()
            all_events = user_events + global_events
            return all_events
    except Exception as e:
        print(f"Error occurred while listing events: {e}")
        return []

                    