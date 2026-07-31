import modules.sql_helper_dictionary as sql_h
def get_history(user_id, limit=None):
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            if limit is not None:
                cursor.execute("SELECT * FROM history WHERE p_id=? ORDER BY visited_at  DESC LIMIT ?", (user_id, limit))
            else:
                cursor.execute("SELECT * FROM history WHERE p_id=? ORDER BY visited_at DESC", (user_id,))
            history = cursor.fetchall()
        conn.close()
        return history
    except Exception as e:
        print(f"Error occurred while fetching history: {e}")
        return []