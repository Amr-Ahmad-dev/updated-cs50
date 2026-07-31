

##commpleat###
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
import modules.sql_helper_dictionary as sql_h
from flask import current_app as app
import smtplib
import modules.profile 
from email.message import EmailMessage

def authenticate(email, password):
    try:
        # Get user from auth.db
        with sql_h.get_db("auth.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
        if user is None:
            print("Invalid credentials.")
            return None
        user = dict(user)
        # Verify password
        if not check_password_hash(user["password"], password):
            print("Invalid credentials.")
            return None
         # Get profile from main.db
        profile = modules.profile.get_profile(user["id"])
        if profile is None:
            print("Profile not found.")
            return None
        user["profile"] = profile
        return user

    except Exception as e:
        print(f"Error occurred while authenticating user: {e}")
        return None
    
def register(data):
    try:
        the_data = data
        with sql_h.get_db("auth.db") as conn, sql_h.get_db("main.db") as conn2:
            cursor = conn.cursor()
            cursor2 = conn2.cursor()
            check_query = cursor.execute("SELECT * FROM users WHERE email=?", (the_data['email'],)).fetchone()
            if check_query:
                print("User already exists.")
                return False,"User already exists."
            if the_data.get("status") == "admin":
                approved = False
            else:
                approved = True
            password = the_data['password']
            password_hash = generate_password_hash(password)
            cursor.execute("INSERT INTO users (email, password, approved , status) VALUES (?, ?, ?, ?)", (the_data['email'], password_hash, approved, the_data.get('status') or 1))
            id = cursor.lastrowid
            cursor2.execute("INSERT INTO users (email,id,p_id) VALUES (?,?,?)", (the_data['email'],id ,id))
            id = cursor.lastrowid
            cursor2.execute("""
                    INSERT INTO profiles (
                        p_id,
                        email,
                        name,
                        age,
                        bio,
                        avatar,
                        average_gpa,
                        current_year,
                        current_semester
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ? ,?)
                """, (
                    id,
                    data.get("email"),
                    data.get("name"),
                    data.get("age"),
                    data.get("bio"),
                    data.get("avatar"),
                    data.get("average_gpa"),
                    data.get("current_year"),
                    data.get("current_semester"),
                ))
            conn.commit()
            conn2.commit()
            return True,None
    except Exception as e:
            print(f"Error occurred while registering user: {e}")
            return False,"Error occurred while registering user."




def request_password_reset(email, application_location_url):####
    try:
        with sql_h.get_db("auth.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email=?", (email,))
            user = cursor.fetchone()
            if not user:
                print("User not found.")
                return False,"User not found."
            token = secrets.token_urlsafe(16)
            cursor.execute("UPDATE users SET token=?, token_created_at=datetime('now') WHERE email=?", (token, email))
            conn.commit()
            reset_link = f"{application_location_url}/reset_password/{token}"

            msg = EmailMessage()
            msg["Subject"] = "Password Reset Request"
            msg["From"] = app.config["EMAIL_ADDRESS"]
            msg["To"] = email

            msg.set_content(
                f"Click the following link to reset your password:\n\n{reset_link}"
            )

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.set_debuglevel(1)
                server.starttls()

                server.login(
                    app.config["EMAIL_ADDRESS"],
                    app.config["EMAIL_PASSWORD"]
                )
                server.send_message(msg)
            print("Password reset requested.")
            return True,None
    except Exception as e:
        print(f"Error occurred while requesting password reset: {e}")
        return False,"Error occurred while requesting password reset."  




def reset_password(token, new_password):
    try:
        with sql_h.get_db("auth.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE token=?", (token,))
            user = cursor.fetchone()
            if not user:
                print("Invalid token.")
                return False,"Invalid token."
            new_password_hash = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password=?, token=NULL, token_created_at=NULL WHERE token=?", (new_password_hash, token))
            conn.commit()
            print("Password reset successful.")
            return True,None
    except Exception as e:
        print(f"Error occurred while resetting password: {e}")
        return False,"Error occurred while resetting password."