import modules.sql_helper_dictionary as sql_h
from flask import current_app as app
 
def get_profile(id):
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profiles WHERE p_id = ?", (id,))
            profile = cursor.fetchone()
            if profile is None:
                print("Profile not found.")

                return None
            print(f"Fetched profile for ID: {id}: {profile}")
            profile_dict = dict(profile)
            return profile_dict
    except Exception as e:
        print(f"Error occurred while fetching profile: {e}")
        return None
def update_profile(id, data):
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE profiles
                SET name = ?, current_year = ?, current_semester = ?, avatar = ?, bio = ?, age = ?
                WHERE p_id = ?
            """, (data['name'], data['current_year'], data['current_semester'], data['avatar'], data['bio'], data['age'], id))
            conn.commit()
            print(f"Updated profile for ID: {id} with data: {data}")
            return True, None
    except Exception as e:
        print(f"Error occurred while updating profile: {e}")
        return False, str(e)

  