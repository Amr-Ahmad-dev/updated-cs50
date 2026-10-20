import modules.sql_helper_dictionary as sql_h

def check_moderation_permission(actor_id, target_id, action="ban"):
    """
    Checks if actor can perform moderation action on target based on hierarchy:
    - Actor status:
      - < 2: Student/Guest (denied)
      - 2 or 3: Can warn only, cannot ban anyone.
      - 4: Level 3 admin. Can ban students, and can ban other admins only if they have >= 3 warnings.
      - >= 5: Level 4/5 admin. Can ban any user below them (actor_status > target_status).
    - Target status:
      - 7 (Professor): Immune from moderation.
    """
    try:
        with sql_h.get_db("auth.db") as conn:
            c = conn.cursor()
            c.execute("SELECT status, state, warning_count FROM users WHERE id = ?", (actor_id,))
            actor = c.fetchone()
            c.execute("SELECT status, state, warning_count FROM users WHERE id = ?", (target_id,))
            target = c.fetchone()

        if not actor or not target:
            return False, "User not found."

        act_status = int(actor["status"] or 1)
        tgt_status = int(target["status"] or 1)
        tgt_warnings = int(target["warning_count"] or 0)

        if act_status < 2:
            return False, "Unauthorized."

        if tgt_status == 7:
            return False, "Professors are immune to moderation."

        if action == "warn":
            # Can warn if actor status > target status
            if act_status > tgt_status:
                return True, None
            return False, "You can only warn users with a lower authority level than yours."

        if action == "ban" or action == "disauthorize":
            # L1 & L2 cannot ban anyone
            if act_status in (2, 3):
                return False, f"Admin Level {act_status - 1} cannot ban or disauthorize users."

            # Any admin can ban/disauthorize anyone below them
            if act_status > tgt_status:
                return True, None

            # L3 Admin (status 4) can ban admins of equal/higher level ONLY if they have >= 3 warnings
            if act_status == 4 and tgt_status >= 4 and tgt_status < 7:
                if tgt_warnings >= 3:
                    return True, None
                return False, "Level 3 admin can only ban other admins if they have at least 3 warnings."

            return False, "You can only ban or disauthorize users with a lower authority level than yours."

        return False, "Invalid action."
    except Exception as e:
        return False, str(e)

def warn_user(user_id, actor_id, reason=""):
    """Issues an official warning to a user, increments warning counter, and records the audit log."""
    try:
        ok, err = check_moderation_permission(actor_id, user_id, action="warn")
        if not ok:
            return False, err

        with sql_h.get_db("auth.db") as auth_conn:
            c = auth_conn.cursor()
            c.execute("SELECT state, warning_count FROM users WHERE id = ?", (user_id,))
            user = c.fetchone()
            
            new_warn_count = (user["warning_count"] or 0) + 1
            new_state = 1 if user["state"] != 2 else 2
            c.execute("UPDATE users SET warning_count = ?, state = ? WHERE id = ?", (new_warn_count, new_state, user_id))
            auth_conn.commit()

        with sql_h.get_db("main.db") as main_conn:
            c = main_conn.cursor()
            c.execute("""
                INSERT INTO moderation_log (actor_p_id, target_p_id, action, reason)
                VALUES (?, ?, 'warn', ?)
            """, (actor_id, user_id, reason or "Violation of platform rules"))

            c.execute("""
                INSERT INTO notifications (p_id, type, message, send_to_year, send_to_semester)
                VALUES (?, 'moderation', ?, 0, 0)
            """, (user_id, f"Official Warning: {reason or 'Please review the community guidelines.'} (Warning count: {new_warn_count})"))
            main_conn.commit()

        return True, None
    except Exception as e:
        print(f"Error warning user: {e}")
        return False, str(e)

def ban_user(user_id, actor_id, reason=""):
    """Bans a user account, preventing subsequent logins."""
    try:
        ok, err = check_moderation_permission(actor_id, user_id, action="ban")
        if not ok:
            return False, err

        with sql_h.get_db("auth.db") as auth_conn:
            c = auth_conn.cursor()
            c.execute("UPDATE users SET state = 2 WHERE id = ?", (user_id,))
            auth_conn.commit()

        with sql_h.get_db("main.db") as main_conn:
            c = main_conn.cursor()
            c.execute("""
                INSERT INTO moderation_log (actor_p_id, target_p_id, action, reason)
                VALUES (?, ?, 'ban', ?)
            """, (actor_id, user_id, reason or "Account suspended by administration"))

            c.execute("""
                INSERT INTO notifications (p_id, type, message, send_to_year, send_to_semester)
                VALUES (?, 'moderation', ?, 0, 0)
            """, (user_id, f"Account Suspended: {reason or 'Your account has been banned by an administrator.'}"))
            main_conn.commit()

        return True, None
    except Exception as e:
        print(f"Error banning user: {e}")
        return False, str(e)

def disauthorize_user(user_id, actor_id):
    """Demotes an admin user to a student (status 1) and revokes approval status."""
    try:
        ok, err = check_moderation_permission(actor_id, user_id, action="disauthorize")
        if not ok:
            return False, err

        with sql_h.get_db("auth.db") as auth_conn:
            c = auth_conn.cursor()
            c.execute("UPDATE users SET status = 1, approved = 1 WHERE id = ?", (user_id,))
            auth_conn.commit()

        with sql_h.get_db("main.db") as main_conn:
            c = main_conn.cursor()
            c.execute("""
                INSERT INTO moderation_log (actor_p_id, target_p_id, action, reason)
                VALUES (?, ?, 'restrict', 'Account disauthorized and demoted to student')
            """, (actor_id, user_id))
            c.execute("""
                INSERT INTO notifications (p_id, type, message, send_to_year, send_to_semester)
                VALUES (?, 'moderation', 'Your administrative privileges have been revoked.', 0, 0)
            """, (user_id,))
            main_conn.commit()
        return True, None
    except Exception as e:
        print(f"Error disauthorizing user: {e}")
        return False, str(e)

def unban_user(user_id, actor_id):
    """Restores a banned user account back to active standing."""
    try:
        with sql_h.get_db("auth.db") as auth_conn:
            c = auth_conn.cursor()
            c.execute("UPDATE users SET state = 0 WHERE id = ?", (user_id,))
            auth_conn.commit()

        with sql_h.get_db("main.db") as main_conn:
            c = main_conn.cursor()
            c.execute("""
                INSERT INTO moderation_log (actor_p_id, target_p_id, action, reason)
                VALUES (?, ?, 'unban', 'Account restored by administrator')
            """, (actor_id, user_id))

            c.execute("""
                INSERT INTO notifications (p_id, type, message, send_to_year, send_to_semester)
                VALUES (?, 'moderation', 'Your account has been unbanned and restored.', 0, 0)
            """, (user_id,))
            main_conn.commit()

        return True, None
    except Exception as e:
        print(f"Error unbanning user: {e}")
        return False, str(e)
