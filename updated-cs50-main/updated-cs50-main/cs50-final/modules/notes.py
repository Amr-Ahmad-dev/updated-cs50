import modules.sql_helper_dictionary as sql_h

def create_note( content="",subject_id=None, entity_type="subject", entity_id=1, title="", authority=1,user_id=None):
    try:
        if not user_id:
            print("User ID is required.")
            return False, "User ID is required."

        if not content and not title:
            print("Note content cannot be empty.")
            return False, "Note content cannot be empty."

        # Fallback if title was sent instead of content
        final_content = content.strip() if content.strip() else title.strip()

        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO student_notes (p_id, entity_type, entity_id, content) VALUES (?, ?, ?, ?)",
                (user_id, entity_type, entity_id, final_content)
            )
            conn.commit()
            return True, cursor.lastrowid

    except Exception as e:
        print(f"Error occurred while creating note: {e}")
        return False, "Error occurred while creating note."


def get_my_notes_tree(p_id, authority=1, entity_type="subject"):
    raw_notes = {}
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            
            # Admins (3 to 6) can technically view any notes, but usually, this function 
            # fetches a specific user's tree. We fetch by p_id.
            cursor.execute(
                "SELECT * FROM student_notes WHERE p_id = ? AND entity_type = ? ORDER BY updated_at DESC", 
                (p_id, entity_type)
            )
            raw_notes[entity_type] = dict(cursor.fetchall()) if cursor.description else []
            print(f"Fetched raw notes for user_id {p_id} and entity_type '{entity_type}': {raw_notes[entity_type]}")  # Debugging line
            
        tree = {}
        
        # Depending on how sql_h returns fetchall() (list or dict), we iterate safely
        notes_iterable = raw_notes[entity_type] if isinstance(raw_notes[entity_type], list) else [raw_notes[entity_type]]

        for note in notes_iterable:
            note_dict = dict(note)
            
            # --- FIX FOR YOUR UI ---
            # Inject a virtual title so your HTML can display it properly
            content_text = (note_dict.get("content") or "").strip()
            if "title" not in note_dict or not note_dict["title"]:
                if content_text:
                    note_dict["title"] = content_text[:40] + ("..." if len(content_text) > 40 else "")
                else:
                    note_dict["title"] = f"Note #{note_dict.get('id')}"
            # -----------------------

            e_type = note_dict.get("entity_type", "subject").capitalize()
            group_name = f"{e_type} Notes"

            if group_name not in tree:
                tree[group_name] = []
            
            # Append to a list so Jinja loops over the notes, not integers!
            tree[group_name].append(note_dict)

        return tree

    except Exception as e:
        print(f"Error occurred while fetching notes tree: {e}")
        return {}


def edit_note(note_id, p_id, content, authority=1, title=None):
    try:
        if not content or not str(content).strip():
            print("Content cannot be empty.")
            return False, "Content cannot be empty."

        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM student_notes WHERE id = ?", (note_id,))
            note = cursor.fetchone()

            if not note:
                print("Note not found.")
                return False, "Note not found."
            parameters = []
            note = dict(note)
            q="UPDATE student_notes SET"
            if title is not None:
                q += " title = ?,"
                parameters.append(title)
            if content is not None:
                q += " content = ?,"
                parameters.append(content.strip())
            q += " updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            parameters.append(note_id)

            # RULE: Only the original author can EDIT. Admins cannot edit.
            if note["p_id"] != p_id:
                print("Unauthorized: Only the author can edit this note.")
                return False, "Unauthorized access. Only the author can edit this note."

            cursor.execute(
                q,
                tuple(parameters)
            )
            conn.commit()
            print("Note edited successfully.")
            return True, None

    except Exception as e:
        print(f"Error occurred while editing note: {e}")
        return False, "Error occurred while editing note."


def delete_note(note_id, p_id, authority=1):
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM student_notes WHERE id = ?", (note_id,))
            note = cursor.fetchone()

            if not note:
                print("Note not found.")
                return False, "Note not found."
            
            note = dict(note)

            # RULE: Author OR Admin (authority 3 to 6) can DELETE
            is_author = (note["p_id"] == p_id)
            is_admin = (3 <= authority <= 6)

            if not is_author and not is_admin:
                print("Unauthorized: Must be author or admin to delete.")
                return False, "Unauthorized access. You do not have permission to delete this note."

            cursor.execute("DELETE FROM student_notes WHERE id = ?", (note_id,))
            conn.commit()
            print("Note deleted successfully.")
            return True, None

    except Exception as e:
        print(f"Error occurred while deleting note: {e}")
        return False, "Error occurred while deleting note."