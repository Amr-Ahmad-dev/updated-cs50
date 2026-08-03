import modules.sql_helper_dictionary as sql_h


def list_favorites(user_id,entity_type="subject"):
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            q=("SELECT entity_id FROM student_favorites WHERE p_id=? AND entity_type=?")
            p=[user_id,entity_type]
            print(p,q)
            cursor.execute(q,p)
            favorites = dict(cursor.fetchall())
            print(f"Fetched favorites for user_id {user_id}: {favorites}")  # Debugging line
            subject_names = []
            
            if entity_type=="subject":
                name='id'
            else:
                name='id'
            entity_type=entity_type+'s'
            q=(f"SELECT * FROM {entity_type} WHERE {name}=?")
            for favorite in favorites.values():
                print(q,favorite)
                cursor.execute(q,(favorite.get('entity_id'),))

                subject_name = cursor.fetchone()
                if subject_name:
                    subject_names.append(subject_name['name'])
                else:
                    subject_names.append(None)
            all_f={}
            all_f['avorites']=favorite
            all_f['subject']=subject_name
        print(f"Returning favorites for user_id {user_id}: {favorites}")  # Debugging line
        return favorites
    except Exception as e:
        print(f"Error occurred while listing favorites: {e}")
        return []


def add_favorite(user_id, subject_id, favorite_type):
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO student_favorites (p_id, entity_id, entity_type) VALUES (?, ?, ?)", (user_id, subject_id, favorite_type))
            conn.commit()
        return True, None
    except Exception as e:
        print(f"Error occurred while adding favorite: {e}")
        return False, "Error occurred while adding favorite."

def remove_favorite(user_id, subject_id, favorite_type):
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM student_favorites WHERE p_id=? AND entity_id=? AND entity_type=?", (user_id, subject_id, favorite_type))
            conn.commit()
        return True, None
    except Exception as e:
        print(f"Error occurred while removing favorite: {e}")
        return False, "Error occurred while removing favorite."

def is_favorite(user_id, subject_id, favorite_type):
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM student_favorites WHERE p_id=? AND entity_id=? AND entity_type=?", (user_id, subject_id, favorite_type))
            result = cursor.fetchone()
            print(f"Checked favorite status for user_id {user_id}, subject_id {subject_id}, favorite_type {favorite_type}: {'is favorite' if result else 'not favorite'}")  # Debugging line
        return result is not None
    except Exception as e:
        print(f"Error occurred while checking favorite: {e}")
        return False