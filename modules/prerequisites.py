import modules.sql_helper_dictionary as sql_h

def get_prerequisites(subject_id: int):
    """Retrieves prerequisites required for a subject and downstream subjects unlocked by it."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            
            # Target subject
            c.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
            subject_row = c.fetchone()
            if not subject_row:
                return {"subject": None, "prerequisites": [], "unlocks": []}

            # Prerequisites required by this subject
            c.execute("""
                SELECT s.* 
                FROM subjects s
                JOIN subject_prerequisites sp ON s.id = sp.prerequisite_subject_id
                WHERE sp.subject_id = ?
                ORDER BY s.year ASC, s.semester ASC
            """, (subject_id,))
            prereqs = [dict(r) for r in c.fetchall()]

            # Subjects that require this subject as a prerequisite
            c.execute("""
                SELECT s.* 
                FROM subjects s
                JOIN subject_prerequisites sp ON s.id = sp.subject_id
                WHERE sp.prerequisite_subject_id = ?
                ORDER BY s.year ASC, s.semester ASC
            """, (subject_id,))
            unlocks = [dict(r) for r in c.fetchall()]

            return {
                "subject": dict(subject_row),
                "prerequisites": prereqs,
                "unlocks": unlocks
            }
    except Exception as e:
        print(f"Error fetching prerequisites: {e}")
        return {"subject": None, "prerequisites": [], "unlocks": []}
