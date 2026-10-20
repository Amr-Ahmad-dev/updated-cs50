import modules.sql_helper_dictionary as sql_h

def list_professors():
    """Lists all professors with their profiles, department, and subjects taught."""
    try:
        professors = []
        with sql_h.get_db("auth.db") as auth_conn:
            c = auth_conn.cursor()
            c.execute("SELECT id, email FROM users WHERE status = 7")
            prof_users = [dict(r) for r in c.fetchall()]

        with sql_h.get_db("main.db") as main_conn:
            c = main_conn.cursor()
            for pu in prof_users:
                pid = pu["id"]
                c.execute("SELECT * FROM profiles WHERE p_id = ?", (pid,))
                prof_data = c.fetchone()

                c.execute("SELECT * FROM professors WHERE user_id = ?", (pid,))
                prof_meta = c.fetchone()

                # Get subjects taught
                c.execute("""
                    SELECT id, code, name, year, semester, credits 
                    FROM subjects 
                    WHERE professor_id = ? OR id IN (SELECT subject_id FROM professor_subjects WHERE professor_id = ?)
                """, (pid, pid))
                subjects_taught = [dict(s) for s in c.fetchall()]

                # Calculate average rating
                c.execute("SELECT AVG(raw_score) as avg_rating, COUNT(*) as vote_count FROM ratings WHERE entity_type = 'professor' AND entity_id = ?", (pid,))
                rating_row = c.fetchone()
                avg_rating = round(rating_row["avg_rating"], 1) if rating_row and rating_row["avg_rating"] else None
                vote_count = rating_row["vote_count"] if rating_row else 0

                item = {
                    "id": pid,
                    "user_id": pid,
                    "email": pu["email"],
                    "name": (prof_data["name"] if prof_data and prof_data["name"] else pu["email"].split("@")[0]),
                    "avatar": (prof_data["avatar"] if prof_data and prof_data["avatar"] else ""),
                    "bio": (prof_meta["bio"] if prof_meta and prof_meta["bio"] else (prof_data["bio"] if prof_data else "")),
                    "department": (prof_meta["department"] if prof_meta and prof_meta["department"] else "General Faculty"),
                    "office": (prof_meta["office"] if prof_meta and prof_meta["office"] else "Faculty Office"),
                    "subjects": subjects_taught,
                    "subject_count": len(subjects_taught),
                    "rating": avg_rating,
                    "vote_count": vote_count
                }
                professors.append(item)
        return professors
    except Exception as e:
        print(f"Error listing professors: {e}")
        return []


def get_professor(professor_id):
    """Retrieves full details, taught subjects, and reviews for a single professor."""
    try:
        with sql_h.get_db("auth.db") as auth_conn:
            c = auth_conn.cursor()
            c.execute("SELECT id, email, status FROM users WHERE id = ?", (professor_id,))
            user_row = c.fetchone()
            if not user_row:
                return None

        with sql_h.get_db("main.db") as main_conn:
            c = main_conn.cursor()
            c.execute("SELECT * FROM profiles WHERE p_id = ?", (professor_id,))
            prof_data = c.fetchone()

            c.execute("SELECT * FROM professors WHERE user_id = ?", (professor_id,))
            prof_meta = c.fetchone()

            c.execute("""
                SELECT s.*, 
                       (SELECT AVG(raw_score) FROM ratings WHERE entity_type = 'subject' AND entity_id = s.id) as avg_rating
                FROM subjects s 
                WHERE s.professor_id = ? OR s.id IN (SELECT subject_id FROM professor_subjects WHERE professor_id = ?)
            """, (professor_id, professor_id))
            subjects = [dict(s) for s in c.fetchall()]

            c.execute("SELECT AVG(raw_score) as avg_rating, COUNT(*) as vote_count FROM ratings WHERE entity_type = 'professor' AND entity_id = ?", (professor_id,))
            rating_row = c.fetchone()
            avg_rating = round(rating_row["avg_rating"], 1) if rating_row and rating_row["avg_rating"] else None
            vote_count = rating_row["vote_count"] if rating_row else 0

            return {
                "id": professor_id,
                "user_id": professor_id,
                "email": user_row["email"],
                "name": (prof_data["name"] if prof_data and prof_data["name"] else user_row["email"].split("@")[0]),
                "avatar": (prof_data["avatar"] if prof_data and prof_data["avatar"] else ""),
                "bio": (prof_meta["bio"] if prof_meta and prof_meta["bio"] else (prof_data["bio"] if prof_data else "")),
                "department": (prof_meta["department"] if prof_meta and prof_meta["department"] else "General Faculty"),
                "office": (prof_meta["office"] if prof_meta and prof_meta["office"] else "Faculty Office"),
                "subjects": subjects,
                "rating": avg_rating,
                "vote_count": vote_count
            }
    except Exception as e:
        print(f"Error getting professor: {e}")
        return None
