import modules.sql_helper_dictionary as sql_h

def list_favorites(user_id: int):
    """Lists all favorited items (subjects, materials, professors, assignments) for a user."""
    try:
        favorites = {"subjects": [], "materials": [], "professors": [], "assignments": []}
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            
            # Subjects
            cursor.execute("""
                SELECT s.*, f.created_at as favorited_at
                FROM student_favorites f
                JOIN subjects s ON f.entity_id = s.id
                WHERE f.p_id = ? AND f.entity_type = 'subject'
                ORDER BY f.created_at DESC
            """, (user_id,))
            favorites["subjects"] = [dict(r) for r in cursor.fetchall()]

            # Materials
            cursor.execute("""
                SELECT m.*, s.name as subject_name, s.code as subject_code, f.created_at as favorited_at
                FROM student_favorites f
                JOIN materials m ON f.entity_id = m.id
                JOIN subjects s ON m.subject_id = s.id
                WHERE f.p_id = ? AND f.entity_type = 'material'
                ORDER BY f.created_at DESC
            """, (user_id,))
            favorites["materials"] = [dict(r) for r in cursor.fetchall()]

            # Professors
            cursor.execute("""
                SELECT p.*, prof.department, prof.office, f.created_at as favorited_at
                FROM student_favorites f
                JOIN profiles p ON f.entity_id = p.p_id
                LEFT JOIN professors prof ON f.entity_id = prof.user_id
                WHERE f.p_id = ? AND f.entity_type = 'professor'
                ORDER BY f.created_at DESC
            """, (user_id,))
            favorites["professors"] = [dict(r) for r in cursor.fetchall()]

            # Assignments
            cursor.execute("""
                SELECT a.*, s.name as subject_name, s.code as subject_code, f.created_at as favorited_at
                FROM student_favorites f
                JOIN assignments a ON f.entity_id = a.id
                JOIN subjects s ON a.subject_id = s.id
                WHERE f.p_id = ? AND f.entity_type = 'assignment'
                ORDER BY f.created_at DESC
            """, (user_id,))
            favorites["assignments"] = [dict(r) for r in cursor.fetchall()]

        return favorites
    except Exception as e:
        print(f"Error listing favorites: {e}")
        return {"subjects": [], "materials": [], "professors": [], "assignments": []}


def is_favorite(user_id: int, entity_id: int, favorite_type: str = "subject") -> bool:
    """Checks if an item is currently favorited by a user."""
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM student_favorites 
                WHERE p_id = ? AND entity_id = ? AND entity_type = ?
            """, (user_id, entity_id, favorite_type))
            return cursor.fetchone() is not None
    except Exception as e:
        print(f"Error checking favorite: {e}")
        return False


def add_favorite(user_id: int, entity_id: int, favorite_type: str = "subject"):
    """Adds an entity to user favorites."""
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO student_favorites (p_id, entity_id, entity_type)
                VALUES (?, ?, ?)
            """, (user_id, entity_id, favorite_type))
            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error adding favorite: {e}")
        return False, str(e)


def remove_favorite(user_id: int, entity_id: int, favorite_type: str = "subject"):
    """Removes an entity from user favorites."""
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM student_favorites 
                WHERE p_id = ? AND entity_id = ? AND entity_type = ?
            """, (user_id, entity_id, favorite_type))
            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error removing favorite: {e}")
        return False, str(e)


def toggle_favorite(user_id: int, entity_id: int, favorite_type: str = "subject"):
    """Toggles favorite state for an entity and returns (ok, error, is_favorited)."""
    try:
        if is_favorite(user_id, entity_id, favorite_type):
            ok, err = remove_favorite(user_id, entity_id, favorite_type)
            return ok, err, False
        else:
            ok, err = add_favorite(user_id, entity_id, favorite_type)
            return ok, err, True
    except Exception as e:
        print(f"Error toggling favorite: {e}")
        return False, str(e), False