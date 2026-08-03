import modules.sql_helper_dictionary as sql_helper
def list_messages(id,unread_only=False):
    """
    List messages for a user.

    Args:
        p_id (int): The ID of the user.
    """
    try:
        with sql_helper.get_db("main.db") as conn:
            type_m="messages."
            
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notifications WHERE p_id = ? AND type = ? AND is_read = ? ORDER BY created_at DESC", (id, type_m, unread_only))
            notifications = dict(cursor.fetchall())or[]
            print(notifications)
        return notifications
    except Exception as e:
        print(f"Error occurred while listing notifications: {e}")
        return []