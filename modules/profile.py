import modules.sql_helper_dictionary as sql_h

def get_profile(id):
    """Retrieves profile from main.db for a given user ID."""
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profiles WHERE p_id = ?", (id,))
            profile = cursor.fetchone()
            if profile is None:
                return None
            profile_dict = dict(profile)

            # Check if professor
            cursor.execute("SELECT * FROM professors WHERE user_id = ?", (id,))
            prof_meta = cursor.fetchone()
            if prof_meta:
                profile_dict["professor_meta"] = dict(prof_meta)
                profile_dict["department"] = prof_meta["department"]
                profile_dict["office"] = prof_meta["office"]

            return profile_dict
    except Exception as e:
        print(f"Error occurred while fetching profile: {e}")
        return None


def update_profile(id, data):
    """Updates user profile and professor metadata if applicable."""
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            
            # Fetch existing profile
            cursor.execute("SELECT * FROM profiles WHERE p_id = ?", (id,))
            current = cursor.fetchone()
            if not current:
                # Create profile row if it somehow didn't exist
                cursor.execute("INSERT INTO profiles (p_id, email, name) VALUES (?, ?, ?)", (id, data.get("email", ""), data.get("name", "")))
                current = {"name": "", "current_year": 1, "current_semester": 1, "avatar": "", "bio": "", "age": None}
            else:
                current = dict(current)

            name = data.get("name", current.get("name", ""))
            current_year = data.get("current_year", current.get("current_year", 1))
            current_semester = data.get("current_semester", current.get("current_semester", 1))
            avatar = data.get("avatar", current.get("avatar", ""))
            bio = data.get("bio", current.get("bio", ""))
            age = data.get("age", current.get("age"))

            cursor.execute("""
                UPDATE profiles
                SET name = ?, current_year = ?, current_semester = ?, avatar = ?, bio = ?, age = ?
                WHERE p_id = ?
            """, (name, current_year, current_semester, avatar, bio, age, id))

            # If professor details provided
            if data.get("department") or data.get("office"):
                cursor.execute("""
                    INSERT INTO professors (user_id, department, office, bio)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        department = COALESCE(excluded.department, professors.department),
                        office = COALESCE(excluded.office, professors.office),
                        bio = COALESCE(excluded.bio, professors.bio)
                """, (id, data.get("department", "General Faculty"), data.get("office", "Faculty Office"), bio))

            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error occurred while updating profile: {e}")
        return False, str(e)