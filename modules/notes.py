import modules.sql_helper_dictionary as sql_h

def create_note(content="", subject_id=None, entity_type="subject", entity_id=None, title="", authority=1, user_id=None):
    """Creates a new student note attached to a subject or material."""
    try:
        if not user_id:
            return False, "User ID is required."

        final_title = (title or "").strip()
        final_content = (content or "").strip()

        if not final_content and not final_title:
            return False, "Note content cannot be empty."

        if not final_title:
            final_title = final_content[:40] + ("..." if len(final_content) > 40 else "")

        target_id = entity_id or subject_id

        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO student_notes (title, p_id, entity_type, entity_id, content, is_public, accepted)
                VALUES (?, ?, ?, ?, ?, 0, 0)
            """, (final_title, user_id, entity_type or "subject", target_id, final_content))
            conn.commit()
            return True, cursor.lastrowid
    except Exception as e:
        print(f"Error creating note: {e}")
        return False, str(e)


def get_my_notes_tree(p_id, authority=1, entity_type="subject"):
    """Fetches notes for a user organized in categorized trees."""
    try:
        tree = {}
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT n.*, s.name as subject_name, s.code as subject_code
                FROM student_notes n
                LEFT JOIN subjects s ON (n.entity_type = 'subject' AND n.entity_id = s.id)
                WHERE n.p_id = ?
                ORDER BY n.updated_at DESC
            """, (p_id,))
            notes_rows = [dict(r) for r in cursor.fetchall()]

            for note in notes_rows:
                # Group label
                if note.get("subject_name"):
                    group_name = f"{note['subject_code']} - {note['subject_name']}"
                elif note.get("entity_type") == "material":
                    group_name = "Material Notes"
                else:
                    group_name = "General Notes"

                if group_name not in tree:
                    tree[group_name] = []
                tree[group_name].append(note)

        return tree
    except Exception as e:
        print(f"Error fetching notes tree: {e}")
        return {}


def get_public_notes(subject_id: int):
    """Retrieves all admin-approved public notes for a subject."""
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT n.*, p.name as author_name, p.avatar as author_avatar
                FROM student_notes n
                LEFT JOIN profiles p ON n.p_id = p.p_id
                WHERE n.entity_type = 'subject' AND n.entity_id = ? AND n.is_public = 1 AND n.accepted = 1
                ORDER BY n.created_at DESC
            """, (subject_id,))
            return [dict(r) for r in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting public notes: {e}")
        return []


def request_publication(note_id: int, user_id: int):
    """Requests that a private note be published publicly (sent to admin queue)."""
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM student_notes WHERE id = ? AND p_id = ?", (note_id, user_id))
            note = cursor.fetchone()
            if not note:
                return False, "Note not found or access denied."

            cursor.execute("""
                UPDATE student_notes 
                SET is_public = 1, accepted = 0, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (note_id,))

            # Send admin notification
            cursor.execute("""
                INSERT INTO notifications (message, type, send_to_user_type, send_to_year, send_to_semester)
                VALUES (?, 'approval_request', 3, 0, 0)
            """, (f"New student note '{note['title'] or 'Note #' + str(note_id)}' submitted for public approval.",))

            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error requesting note publication: {e}")
        return False, str(e)


def edit_note(note_id: int, p_id: int, content: str, authority: int = 1, title: str = None):
    """Edits note content and title if owned by the user."""
    try:
        if not content or not content.strip():
            return False, "Content cannot be empty."

        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM student_notes WHERE id = ?", (note_id,))
            note = cursor.fetchone()
            if not note:
                return False, "Note not found."

            if note["p_id"] != p_id:
                return False, "Unauthorized access. Only the author can edit this note."

            cursor.execute("""
                UPDATE student_notes 
                SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (title or note["title"], content.strip(), note_id))
            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error editing note: {e}")
        return False, str(e)


def delete_note(note_id: int, p_id: int, authority: int = 1):
    """Deletes a note if author or admin."""
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM student_notes WHERE id = ?", (note_id,))
            note = cursor.fetchone()
            if not note:
                return False, "Note not found."

            is_author = (note["p_id"] == p_id)
            is_admin = (authority and authority >= 2)

            if not is_author and not is_admin:
                return False, "Unauthorized: Permission denied to delete this note."

            cursor.execute("DELETE FROM student_notes WHERE id = ?", (note_id,))
            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error deleting note: {e}")
        return False, str(e)