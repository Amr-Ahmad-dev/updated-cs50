import modules.sql_helper_dictionary as sql_h

def search_subjects(query: str):
    """Searches subjects by name, code, or description."""
    if not query or not query.strip():
        return []
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            term = f"%{query.strip()}%"
            c.execute("""
                SELECT s.*, p.name as professor_name,
                       (SELECT AVG(raw_score) FROM ratings WHERE entity_type = 'subject' AND entity_id = s.id) as avg_rating
                FROM subjects s
                LEFT JOIN profiles p ON s.professor_id = p.p_id
                WHERE (s.name LIKE ? OR s.code LIKE ? OR s.description LIKE ?) AND s.accepted = 1
                ORDER BY s.year ASC, s.name ASC
            """, (term, term, term))
            return [dict(r) for r in c.fetchall()]
    except Exception as e:
        print(f"Error searching subjects: {e}")
        return []


def search_materials(query: str, subject_id: int = None):
    """Searches materials by title or description, optionally scoped to a subject."""
    if not query or not query.strip():
        return []
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            term = f"%{query.strip()}%"
            if subject_id:
                c.execute("""
                    SELECT m.*, s.name as subject_name, s.code as subject_code
                    FROM materials m
                    JOIN subjects s ON m.subject_id = s.id
                    WHERE (m.title LIKE ? OR m.description LIKE ?) AND m.subject_id = ? AND m.accepted = 1
                    ORDER BY m.created_at DESC
                """, (term, term, subject_id))
            else:
                c.execute("""
                    SELECT m.*, s.name as subject_name, s.code as subject_code
                    FROM materials m
                    JOIN subjects s ON m.subject_id = s.id
                    WHERE (m.title LIKE ? OR m.description LIKE ?) AND m.accepted = 1
                    ORDER BY m.created_at DESC
                """, (term, term))
            return [dict(r) for r in c.fetchall()]
    except Exception as e:
        print(f"Error searching materials: {e}")
        return []


def search_professors(query: str):
    """Searches professors by name, email, department, or office."""
    if not query or not query.strip():
        return []
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            term = f"%{query.strip()}%"
            c.execute("""
                SELECT p.*, prof.department, prof.office, prof.bio as prof_bio
                FROM profiles p
                JOIN users u ON p.p_id = u.id
                LEFT JOIN professors prof ON p.p_id = prof.user_id
                WHERE u.status = 7 AND (p.name LIKE ? OR p.email LIKE ? OR prof.department LIKE ? OR prof.office LIKE ?)
                ORDER BY p.name ASC
            """, (term, term, term, term))
            return [dict(r) for r in c.fetchall()]
    except Exception as e:
        print(f"Error searching professors: {e}")
        return []


def search_students(query: str, subject_id: int = None):
    """Searches students by name or email."""
    if not query or not query.strip():
        return []
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            term = f"%{query.strip()}%"
            if subject_id:
                c.execute("""
                    SELECT p.* 
                    FROM profiles p
                    JOIN student_subjects ss ON p.p_id = ss.p_id
                    WHERE ss.sub_id = ? AND (p.name LIKE ? OR p.email LIKE ?)
                """, (subject_id, term, term))
            else:
                c.execute("""
                    SELECT p.* 
                    FROM profiles p
                    JOIN users u ON p.p_id = u.id
                    WHERE u.status = 1 AND (p.name LIKE ? OR p.email LIKE ?)
                """, (term, term))
            return [dict(r) for r in c.fetchall()]
    except Exception as e:
        print(f"Error searching students: {e}")
        return []


def search_assignments(query: str, subject_id: int = None):
    """Searches assignments by title or description."""
    if not query or not query.strip():
        return []
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            term = f"%{query.strip()}%"
            if subject_id:
                c.execute("""
                    SELECT a.*, s.name as subject_name, s.code as subject_code
                    FROM assignments a
                    JOIN subjects s ON a.subject_id = s.id
                    WHERE a.subject_id = ? AND (a.title LIKE ? OR a.description LIKE ?)
                    ORDER BY a.created_at DESC
                """, (subject_id, term, term))
            else:
                c.execute("""
                    SELECT a.*, s.name as subject_name, s.code as subject_code
                    FROM assignments a
                    JOIN subjects s ON a.subject_id = s.id
                    WHERE (a.title LIKE ? OR a.description LIKE ?)
                    ORDER BY a.created_at DESC
                """, (term, term))
            return [dict(r) for r in c.fetchall()]
    except Exception as e:
        print(f"Error searching assignments: {e}")
        return []


def search_all(query: str):
    """Performs global search across subjects, materials, professors, and assignments."""
    if not query or not query.strip():
        return {
            "query": "",
            "subjects": [],
            "materials": [],
            "professors": [],
            "assignments": [],
            "total_results": 0
        }

    sub_res = search_subjects(query)
    mat_res = search_materials(query)
    prof_res = search_professors(query)
    assign_res = search_assignments(query)

    return {
        "query": query,
        "subjects": sub_res,
        "materials": mat_res,
        "professors": prof_res,
        "assignments": assign_res,
        "total_results": len(sub_res) + len(mat_res) + len(prof_res) + len(assign_res)
    }
