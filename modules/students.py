import modules.sql_helper_dictionary as sql_h

def list_students(query_filters=None):
    """Lists students with their academic year, GPA, and enrolled subjects count."""
    try:
        students = []
        with sql_h.get_db("auth.db") as auth_conn:
            c = auth_conn.cursor()
            c.execute("SELECT id, email, state FROM users WHERE status = 1")
            student_users = {r["id"]: dict(r) for r in c.fetchall()}

        with sql_h.get_db("main.db") as main_conn:
            c = main_conn.cursor()
            query = "SELECT * FROM profiles WHERE 1=1"
            params = []
            if query_filters:
                if query_filters.get("year"):
                    query += " AND current_year = ?"
                    params.append(int(query_filters["year"]))
                if query_filters.get("search"):
                    query += " AND (name LIKE ? OR email LIKE ?)"
                    term = f"%{query_filters['search']}%"
                    params.extend([term, term])

            query += " ORDER BY p_id ASC"
            c.execute(query, tuple(params))
            for p in c.fetchall():
                pid = p["p_id"]
                if pid in student_users:
                    # Get enrolled subjects count
                    c.execute("SELECT COUNT(*) as c FROM student_subjects WHERE p_id = ?", (pid,))
                    cnt = c.fetchone()["c"]

                    std = dict(p)
                    std["id"] = pid
                    std["status_info"] = student_users[pid]
                    std["enrolled_count"] = cnt
                    students.append(std)
        return students
    except Exception as e:
        print(f"Error listing students: {e}")
        return []


def get_student(student_id):
    """Retrieves full student overview including enrolled courses and published notes."""
    try:
        with sql_h.get_db("main.db") as main_conn:
            c = main_conn.cursor()
            c.execute("SELECT * FROM profiles WHERE p_id = ?", (student_id,))
            prof = c.fetchone()
            if not prof:
                return None

            student = dict(prof)
            student["id"] = student_id

            # Enrolled subjects
            c.execute("""
                SELECT s.* 
                FROM subjects s
                JOIN student_subjects ss ON s.id = ss.sub_id
                WHERE ss.p_id = ?
            """, (student_id,))
            student["enrolled_subjects"] = [dict(s) for s in c.fetchall()]

            # Public notes
            c.execute("""
                SELECT n.*, s.name as subject_name
                FROM student_notes n
                LEFT JOIN subjects s ON (n.entity_type = 'subject' AND n.entity_id = s.id)
                WHERE n.p_id = ? AND n.is_public = 1 AND n.accepted = 1
                ORDER BY n.created_at DESC
            """, (student_id,))
            student["public_notes"] = [dict(n) for n in c.fetchall()]

            return student
    except Exception as e:
        print(f"Error getting student detail: {e}")
        return None
