import modules.sql_helper_dictionary as sql_helper




##WRONG IMPLIMIENTATION OF THE FUNCTION, NEED TO FIX IT LATER
##ADD ANOTHER TABLE USER_NOTIFICATTION TO MACK THE READ STATUS OF THE NOTIFICATION FOR EACH USER, SO THAT WE CAN TRACK THE READ STATUS OF EACH NOTIFICATION FOR EACH USER
def list_notification(unread_only="unread",id=None,status=None):
    """
    List notifications for a user.

    Args:
        unread_only (str): Whether to list only unread notifications.
        id (int): The ID of the notification to fetch.
    """
    try:
        with sql_helper.get_db("main.db") as conn:
            cursor = conn.cursor()
            notifications = []
            if id is not None:
                q=("""
                    SELECT n.*
                    FROM notifications n
                    LEFT JOIN profiles p ON p.p_id = :id
                    WHERE (n.p_id = :id OR n.p_id IS NULL)
                        AND (n.send_to_user_type= :status OR n.send_to_user_type= 1)
                        AND (n.send_to_year = p.current_year OR n.send_to_year =0)
                        AND (n.send_to_semester = p.current_semester OR n.send_to_semester =0)
                    """)
                print ("unread_only:", unread_only)
                if unread_only == "unread":
                    q += " AND n.is_read = 0"
                    print("unread_only is unread")
                elif unread_only == "read":
                    print("unread_only is read")
                    q += " AND n.is_read = 1"
                p={"id": id, "status": status}
                q += " ORDER BY n.created_at DESC"
                cursor.execute(q, p)
            else:
                q=("""
                    SELECT * FROM notifications wHERE p_id IS NULL
                    """)
                if unread_only == "unread":
                    q += " AND is_read = 0"
                elif unread_only == "read":
                    q += " AND is_read = 1"
                q += " ORDER BY created_at DESC"
                cursor.execute(q)
            
            notifications = dict(cursor.fetchall())
            print(notifications)
        return notifications
    except Exception as e:
        print(f"Error occurred while listing notifications: {e}")
        return []
def mark_as_read(notification_id , user_id):
    try:
        with sql_helper.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE notifications
                SET is_read = 1
                WHERE id = :notification_id 
            """, {"notification_id": notification_id})
            conn.commit()
            return True,None
    except Exception as e:
        print(f"Error occurred while marking notification as read: {e}")
        return False, str(e)