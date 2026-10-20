import modules.sql_helper_dictionary as sql_h

def list_assignments(subject_id):
    """Lists all assignments for a given subject."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                SELECT a.*, s.name as subject_name, s.code as subject_code
                FROM assignments a
                JOIN subjects s ON a.subject_id = s.id
                WHERE a.subject_id = ?
                ORDER BY a.created_at DESC
            """, (subject_id,))
            return [dict(row) for row in c.fetchall()]
    except Exception as e:
        print(f"Error listing assignments: {e}")
        return []


def get_assignment(assignment_id):
    """Retrieves full details for a single assignment."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                SELECT a.*, s.name as subject_name, s.code as subject_code
                FROM assignments a
                JOIN subjects s ON a.subject_id = s.id
                WHERE a.id = ?
            """, (assignment_id,))
            row = c.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"Error getting assignment: {e}")
        return None
