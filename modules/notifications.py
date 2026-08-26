import modules.sql_helper_dictionary as sql_helper

def list_notification(unread_only="unread", id=None, status=None):
    """Lists notifications for a user, filtering by read/unread and target audience."""
    try:
        with sql_helper.get_db("main.db") as conn:
            cursor = conn.cursor()
            query = """
                SELECT n.*
                FROM notifications n
                LEFT JOIN profiles p ON p.p_id = :id
                WHERE (n.p_id = :id OR n.p_id IS NULL)
            """
            params = {"id": id}

            if unread_only == "unread" or unread_only is True:
                query += " AND n.is_read = 0"
            elif unread_only == "read":
                query += " AND n.is_read = 1"

            query += " ORDER BY n.created_at DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error occurred while listing notifications: {e}")
        return []


def mark_as_read(notification_id: int, user_id: int):
    """Marks a notification as read."""
    try:
        with sql_helper.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE notifications
                SET is_read = 1
                WHERE id = ? AND (p_id = ? OR p_id IS NULL)
            """, (notification_id, user_id))
            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error occurred while marking notification as read: {e}")
        return False, str(e)


def create_notification(message, notification_type="info", p_id=None, send_to_year=0, send_to_semester=0, send_to_user_type=None):
    """Creates and inserts a notification record into the main.db."""
    try:
        with sql_helper.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notifications (p_id, type, message, send_to_year, send_to_semester, send_to_user_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (p_id, notification_type, message, int(send_to_year or 0), int(send_to_semester or 0), send_to_user_type))
            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error creating notification: {e}")
        return False, str(e)