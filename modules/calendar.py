import modules.sql_helper_dictionary as sql_h

def get_subject_calendar(subject_id: int):
    """Retrieves scheduled events, assignment deadlines, and milestones for a subject."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            
            c.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
            sub = c.fetchone()
            if not sub:
                return {"subject": None, "events": [], "assignments": []}

            # Events
            c.execute("""
                SELECT * FROM events 
                WHERE subject_id = ? 
                ORDER BY event_date ASC, created_at ASC
            """, (subject_id,))
            events = [dict(r) for r in c.fetchall()]

            # Assignments
            c.execute("""
                SELECT * FROM assignments 
                WHERE subject_id = ? 
                ORDER BY created_at ASC
            """, (subject_id,))
            assignments = [dict(r) for r in c.fetchall()]

            return {
                "subject": dict(sub),
                "events": events,
                "assignments": assignments
            }
    except Exception as e:
        print(f"Error fetching subject calendar: {e}")
        return {"subject": None, "events": [], "assignments": []}
