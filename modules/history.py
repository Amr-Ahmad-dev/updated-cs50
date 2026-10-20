import modules.sql_helper_dictionary as sql_h

def get_history(user_id: int, limit: int = None):
    """Retrieves chronological browsing history for a user with resolved entity titles."""
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            query = """
                SELECT h.id, h.p_id, h.entity_type, h.entity_id, h.visited_at,
                       CASE 
                           WHEN h.entity_type = 'subject' THEN (SELECT name FROM subjects WHERE id = h.entity_id)
                           WHEN h.entity_type = 'material' THEN (SELECT title FROM materials WHERE id = h.entity_id)
                           WHEN h.entity_type = 'assignment' THEN (SELECT title FROM assignments WHERE id = h.entity_id)
                           WHEN h.entity_type = 'professor' THEN (SELECT name FROM profiles WHERE p_id = h.entity_id)
                           ELSE 'Unknown Item'
                       END as title,
                       CASE
                           WHEN h.entity_type = 'subject' THEN (SELECT code FROM subjects WHERE id = h.entity_id)
                           ELSE ''
                       END as code
                FROM history h
                WHERE h.p_id = ?
                ORDER BY h.visited_at DESC
            """
            if limit is not None:
                query += f" LIMIT {int(limit)}"
            
            cursor.execute(query, (user_id,))
            return [dict(r) for r in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []


def record_visit(user_id: int, entity_type: str, entity_id: int):
    """Logs a visit to an entity (subject, material, assignment, professor)."""
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO history (p_id, entity_type, entity_id, visited_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, entity_type, entity_id))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error recording visit history: {e}")
        return False