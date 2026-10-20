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


def get_student_grades(p_id: int):
    """Retrieves all grade records for a student along with subject information."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                SELECT sg.*, s.name as subject_name, s.code as subject_code, s.credits
                FROM student_grades sg
                JOIN subjects s ON sg.subject_id = s.id
                WHERE sg.p_id = ?
                ORDER BY sg.year ASC, sg.semester ASC, s.name ASC
            """, (p_id,))
            grades = [dict(r) for r in c.fetchall()]
            
            total_credits = sum(g.get("credits") or 3 for g in grades)
            total_points = sum((g.get("grade") or 0.0) * (g.get("credits") or 3) for g in grades)
            cumulative_gpa = round(total_points / total_credits, 2) if total_credits > 0 else 0.0

            # Semester breakdown
            semesters = {}
            for g in grades:
                key = f"Year {g['year']}, Sem {g['semester']}"
                if key not in semesters:
                    semesters[key] = {"courses": [], "credits": 0, "points": 0.0, "gpa": 0.0}
                cred = g.get("credits") or 3
                semesters[key]["courses"].append(g)
                semesters[key]["credits"] += cred
                semesters[key]["points"] += (g.get("grade") or 0.0) * cred

            for key, sem in semesters.items():
                if sem["credits"] > 0:
                    sem["gpa"] = round(sem["points"] / sem["credits"], 2)

            return {
                "grades": grades,
                "cumulative_gpa": cumulative_gpa,
                "total_credits": total_credits,
                "semesters": semesters
            }
    except Exception as e:
        print(f"Error getting student grades: {e}")
        return {"grades": [], "cumulative_gpa": 0.0, "total_credits": 0, "semesters": {}}


def save_student_grade(p_id: int, subject_id: int, year: int, semester: int, grade: float, letter: str = None, hours_studied: float = 0.0):
    """Saves or updates a student grade and updates the student's profile average GPA."""
    try:
        # Determine letter from grade if not supplied
        if not letter:
            if grade >= 3.85: letter = "A"
            elif grade >= 2.85: letter = "B"
            elif grade >= 1.85: letter = "C"
            elif grade >= 0.85: letter = "D"
            else: letter = "F"

        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO student_grades (p_id, subject_id, year, semester, letter, grade, hours_studied)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(p_id, subject_id, year, semester) DO UPDATE SET
                    letter = excluded.letter,
                    grade = excluded.grade,
                    hours_studied = excluded.hours_studied
            """, (p_id, subject_id, int(year), int(semester), letter, float(grade), float(hours_studied or 0.0)))

            # Recalculate average GPA
            c.execute("""
                SELECT sg.grade, s.credits
                FROM student_grades sg
                JOIN subjects s ON sg.subject_id = s.id
                WHERE sg.p_id = ?
            """, (p_id,))
            all_grades = c.fetchall()
            if all_grades:
                tot_cred = sum(r["credits"] or 3 for r in all_grades)
                tot_pts = sum(r["grade"] * (r["credits"] or 3) for r in all_grades)
                new_avg = round(tot_pts / tot_cred, 2) if tot_cred > 0 else 0.0
                c.execute("UPDATE profiles SET average_gpa = ? WHERE p_id = ?", (new_avg, p_id))

            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error saving student grade: {e}")
        return False, str(e)


def delete_student_grade(p_id: int, grade_id: int):
    """Deletes a student grade entry and refreshes profile average GPA."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("DELETE FROM student_grades WHERE id = ? AND p_id = ?", (grade_id, p_id))

            # Recalculate average GPA
            c.execute("""
                SELECT sg.grade, s.credits
                FROM student_grades sg
                JOIN subjects s ON sg.subject_id = s.id
                WHERE sg.p_id = ?
            """, (p_id,))
            all_grades = c.fetchall()
            new_avg = None
            if all_grades:
                tot_cred = sum(r["credits"] or 3 for r in all_grades)
                tot_pts = sum(r["grade"] * (r["credits"] or 3) for r in all_grades)
                new_avg = round(tot_pts / tot_cred, 2) if tot_cred > 0 else 0.0
            c.execute("UPDATE profiles SET average_gpa = ? WHERE p_id = ?", (new_avg, p_id))

            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error deleting student grade: {e}")
        return False, str(e)

