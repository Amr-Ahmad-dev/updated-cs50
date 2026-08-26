import modules.sql_helper_dictionary as sql_h

def list_posts(subject_id: int):
    """Lists discussion forum posts for a subject with author details."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                SELECT dp.*, p.name as author_name, p.avatar as author_avatar, p.email as author_email
                FROM discussion_posts dp
                LEFT JOIN profiles p ON dp.user_id = p.p_id
                WHERE dp.subject_id = ?
                ORDER BY dp.created_at DESC
            """, (subject_id,))
            return [dict(r) for r in c.fetchall()]
    except Exception as e:
        print(f"Error listing discussion posts: {e}")
        return []


def create_post(subject_id: int, user_id: int, form_data: dict):
    """Creates a new post on the subject discussion board."""
    try:
        title = (form_data.get("title") or "").strip()
        content = (form_data.get("content") or "").strip()

        if not content:
            return False, "Post content cannot be empty."
        if not title:
            title = content[:50] + ("..." if len(content) > 50 else "")

        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO discussion_posts (subject_id, user_id, title, content)
                VALUES (?, ?, ?, ?)
            """, (subject_id, user_id, title, content))
            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error creating discussion post: {e}")
        return False, str(e)
