import modules.sql_helper_dictionary as sql_h

def list_conversations(user_id: int):
    """Lists all active conversation threads for a user with latest message and unread counts."""
    try:
        conversations = []
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            
            # Find distinct interlocutors
            c.execute("""
                SELECT DISTINCT 
                    CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END as other_id
                FROM direct_messages
                WHERE sender_id = ? OR receiver_id = ?
            """, (user_id, user_id, user_id))
            other_ids = [r["other_id"] for r in c.fetchall()]

            for oid in other_ids:
                # Other user profile
                c.execute("SELECT * FROM profiles WHERE p_id = ?", (oid,))
                prof = c.fetchone()

                # Last message in thread
                c.execute("""
                    SELECT * FROM direct_messages 
                    WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
                    ORDER BY created_at DESC LIMIT 1
                """, (user_id, oid, oid, user_id))
                last_msg = c.fetchone()

                # Unread messages from them to user
                c.execute("""
                    SELECT COUNT(*) as unread FROM direct_messages 
                    WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
                """, (oid, user_id))
                unread_row = c.fetchone()
                unread_cnt = unread_row["unread"] if unread_row else 0

                other_user_data = {
                    "id": oid,
                    "name": (prof["name"] if prof and prof["name"] else f"User #{oid}"),
                    "avatar": (prof["avatar"] if prof and prof["avatar"] else ""),
                    "email": (prof["email"] if prof else "")
                }

                conversations.append({
                    "other_user": other_user_data,
                    "last_message": dict(last_msg) if last_msg else {},
                    "unread_count": unread_cnt
                })

        # Sort by most recent message
        conversations.sort(key=lambda x: x.get("last_message", {}).get("created_at", ""), reverse=True)
        return conversations
    except Exception as e:
        print(f"Error listing conversations: {e}")
        return []


def get_conversation(user_id: int, other_user_id: int):
    """Retrieves full message thread between two users and marks incoming messages as read."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            
            # Other user info
            c.execute("SELECT * FROM profiles WHERE p_id = ?", (other_user_id,))
            prof = c.fetchone()
            other_user = {
                "id": other_user_id,
                "name": (prof["name"] if prof and prof["name"] else f"User #{other_user_id}"),
                "avatar": (prof["avatar"] if prof and prof["avatar"] else ""),
                "email": (prof["email"] if prof else "")
            }

            # Mark unread messages from other user as read
            c.execute("""
                UPDATE direct_messages 
                SET is_read = 1 
                WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
            """, (other_user_id, user_id))
            conn.commit()

            # Fetch messages
            c.execute("""
                SELECT dm.*, 
                       (CASE WHEN dm.sender_id = ? THEN 1 ELSE 0 END) as is_mine
                FROM direct_messages dm
                WHERE (dm.sender_id = ? AND dm.receiver_id = ?)
                   OR (dm.sender_id = ? AND dm.receiver_id = ?)
                ORDER BY dm.created_at ASC
            """, (user_id, user_id, other_user_id, other_user_id, user_id))
            msgs = [dict(r) for r in c.fetchall()]

            return {
                "other_user": other_user,
                "messages": msgs
            }
    except Exception as e:
        print(f"Error getting conversation: {e}")
        return {"other_user": {"id": other_user_id, "name": f"User #{other_user_id}", "avatar": ""}, "messages": []}


def send_message(sender_id: int, receiver_id: int, form_data: dict):
    """Sends a direct message to another user."""
    try:
        content = (form_data.get("content") or form_data.get("message") or "").strip()
        if not content:
            return False, "Message content cannot be empty."

        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            
            # Sender name for notification
            c.execute("SELECT name FROM profiles WHERE p_id = ?", (sender_id,))
            prof = c.fetchone()
            sender_name = (prof["name"] if prof and prof["name"] else f"User #{sender_id}")

            c.execute("""
                INSERT INTO direct_messages (sender_id, receiver_id, content, is_read)
                VALUES (?, ?, ?, 0)
            """, (sender_id, receiver_id, content))

            # Send notification
            c.execute("""
                INSERT INTO notifications (p_id, type, message, send_to_year, send_to_semester)
                VALUES (?, 'message', ?, 0, 0)
            """, (receiver_id, f"New direct message from {sender_name}: {content[:60]}..."))

            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error sending message: {e}")
        return False, str(e)


def list_messages(user_id: int, unread_only=False):
    """Lists incoming direct messages for the user (for dashboard summaries)."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            query = """
                SELECT dm.*, p.name as sender_name, p.avatar as sender_avatar, p.email as sender_email
                FROM direct_messages dm
                LEFT JOIN profiles p ON dm.sender_id = p.p_id
                WHERE dm.receiver_id = ?
            """
            params = [user_id]
            if unread_only == "unread" or unread_only is True:
                query += " AND dm.is_read = 0"
            query += " ORDER BY dm.created_at DESC"
            c.execute(query, tuple(params))
            return [dict(r) for r in c.fetchall()]
    except Exception as e:
        print(f"Error listing messages: {e}")
        return []