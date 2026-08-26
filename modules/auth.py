import secrets
import smtplib
from email.message import EmailMessage
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app as app
import modules.sql_helper_dictionary as sql_h
import modules.profile as profile_mod

def authenticate(email, password):
    """Authenticates a user against auth.db, retrieves main.db profile, and returns user dict."""
    try:
        if not email or not password:
            return None

        with sql_h.get_db("auth.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email.strip(),))
            user = cursor.fetchone()

        if user is None:
            return None

        user_dict = dict(user)

        # Verify password hash
        if not check_password_hash(user_dict["password"], password):
            return None

        # Fetch profile from main.db
        prof = profile_mod.get_profile(user_dict["id"])
        if prof is None:
            # Fallback: create empty profile if missing
            with sql_h.get_db("main.db") as conn2:
                c2 = conn2.cursor()
                c2.execute("""
                    INSERT OR IGNORE INTO profiles (p_id, email, name, current_year, current_semester)
                    VALUES (?, ?, ?, 1, 1)
                """, (user_dict["id"], user_dict["email"], user_dict["email"].split("@")[0]))
                c2.execute("""
                    INSERT OR IGNORE INTO users (id, email, p_id)
                    VALUES (?, ?, ?)
                """, (user_dict["id"], user_dict["email"], user_dict["id"]))
                conn2.commit()
            prof = profile_mod.get_profile(user_dict["id"]) or {
                "p_id": user_dict["id"], "name": user_dict["email"].split("@")[0], "avatar": ""
            }

        user_dict["profile"] = prof
        return user_dict

    except Exception as e:
        print(f"Error occurred while authenticating user: {e}")
        return None


def register(data):
    """Registers a new user into auth.db and creates corresponding main.db records."""
    try:
        email = (data.get("email") or "").strip()
        password = data.get("password") or ""
        confirm_password = data.get("confirm_password") or ""
        name = (data.get("name") or "").strip() or email.split("@")[0]

        if not email or not password:
            return False, "Email and password are required."

        if confirm_password and password != confirm_password:
            return False, "Passwords do not match."

        raw_status = data.get("status")
        try:
            status = int(raw_status) if raw_status is not None else 1
        except (ValueError, TypeError):
            status = 1

        # Non-students require admin approval unless already approved
        # Bypass approval if status >= 2 (Admin/Professor) and a valid admin code is provided
        admin_code = data.get("admin_code", "").strip()
        ADMIN_CODES = ["LEDGER_ADMIN_2026", "SECRET_ADMIN_BYPASS", "CS50_LEDGER_ADMIN", "admin", "admin123"]
        
        if status >= 2 and admin_code in ADMIN_CODES:
            approved = 1
        else:
            approved = 1 if status == 1 else 0
            
        password_hash = generate_password_hash(password)

        with sql_h.get_db("auth.db") as auth_conn:
            c1 = auth_conn.cursor()
            c1.execute("SELECT id FROM users WHERE email = ?", (email,))
            if c1.fetchone():
                return False, "An account with that email already exists."

            c1.execute("""
                INSERT INTO users (email, password, approved, status, state, warning_count)
                VALUES (?, ?, ?, ?, 0, 0)
            """, (email, password_hash, approved, status))
            user_id = c1.lastrowid
            auth_conn.commit()

        with sql_h.get_db("main.db") as main_conn:
            c2 = main_conn.cursor()
            c2.execute("""
                INSERT INTO profiles (p_id, email, name, age, bio, avatar, average_gpa, current_year, current_semester)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                email,
                name,
                data.get("age"),
                data.get("bio", ""),
                data.get("avatar", ""),
                data.get("average_gpa"),
                data.get("current_year", 1),
                data.get("current_semester", 1)
            ))

            c2.execute("""
                INSERT INTO users (id, email, p_id)
                VALUES (?, ?, ?)
            """, (user_id, email, user_id))

            if status == 7:
                # Professor profile initialization
                c2.execute("""
                    INSERT OR IGNORE INTO professors (user_id, office, department, bio)
                    VALUES (?, 'Faculty Office', 'General Department', '')
                """, (user_id,))

            main_conn.commit()

        return True, None
    except Exception as e:
        print(f"Error occurred while registering user: {e}")
        return False, str(e)


def request_password_reset(email, application_location_url):
    """Generates password reset token and sends email."""
    try:
        with sql_h.get_db("auth.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email.strip(),))
            user = cursor.fetchone()
            if not user:
                return True, None  # Obfuscate email existence

            token = secrets.token_urlsafe(24)
            cursor.execute("UPDATE users SET token = ?, token_created_at = datetime('now') WHERE email = ?", (token, email.strip()))
            conn.commit()

            try:
                reset_link = f"{application_location_url.rstrip('/')}/auth/reset-password/{token}"
                msg = EmailMessage()
                msg["Subject"] = "Password Reset Request — Ledger"
                msg["From"] = app.config.get("EMAIL_ADDRESS", "studentflowapp2026@gmail.com")
                msg["To"] = email.strip()
                msg.set_content(f"You requested a password reset for your Ledger account.\n\nClick the link below to reset your password:\n{reset_link}\n\nIf you did not request this, please ignore this email.")

                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login(app.config.get("EMAIL_ADDRESS", "studentflowapp2026@gmail.com"), app.config.get("EMAIL_PASSWORD", ""))
                    server.send_message(msg)
            except Exception as mail_err:
                print(f"Mail delivery notice (may be skipped in local test mode): {mail_err}")

            return True, None
    except Exception as e:
        print(f"Error requesting password reset: {e}")
        return False, str(e)


def reset_password(token, new_password):
    """Resets user password given a valid token."""
    try:
        with sql_h.get_db("auth.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE token = ?", (token,))
            user = cursor.fetchone()
            if not user:
                return False, "Invalid or expired reset token."

            new_password_hash = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password = ?, token = NULL, token_created_at = NULL WHERE token = ?", (new_password_hash, token))
            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error resetting password: {e}")
        return False, str(e)