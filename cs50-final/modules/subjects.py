import modules.sql_helper_dictionary as sql_helper
import modules.favorites as favorites
def list_subjects(user_id, filters=None):
    try:
        with sql_helper.get_db("main.db") as conn:
            cursor = conn.cursor()
            params = {"user_id": user_id}
            
            # Using LEFT JOIN to handle professor filtering cleanly
            query = """
                SELECT s.* FROM subjects s 
                LEFT JOIN professors p ON s.professor_id = p.user_id 
                LEFT JOIN users u ON p.user_id = u.id
                WHERE 1=1 AND (s.visibility = 'public' AND s.accepted = 1 OR s.created_by = :user_id)
            """

            if filters:
                if filters.get("subject_name"):
                    query += " AND s.name LIKE :subject_name"
                    params["subject_name"] = f"%{filters['subject_name']}%"
                if filters.get("professor_name"):
                    query += " AND u.name LIKE :professor_name"
                    params["professor_name"] = f"%{filters['professor_name']}%"
                if filters.get("subject_code"):
                    query += " AND s.code LIKE :subject_code"
                    params["subject_code"] = f"%{filters['subject_code']}%"
                if filters.get("year"):
                    query += " AND s.year = :year"
                    params["year"] = filters["year"]
                if filters.get("semester"):
                    query += " AND s.semester = :semester"
                    params["semester"] = filters["semester"]
                query += " ORDER BY s.created_at DESC"
            else:
                # Default behavior
                query = "SELECT * FROM student_subjects WHERE P_id = :user_id"
            params["user_id"] = user_id
            cursor.execute(query, params)
            subjects = dict(cursor.fetchall())
            return subjects
    except Exception as e:
        print(f"Error occurred while listing subjects: {e}")
        return []
#shoud add rating to the join but must imblemnt a function to calculate the rating of the subject based on the reviews and ratings given by the students, and then join that with the subjects table to get the average rating of each subject.
## hence it is not a data but a recurd nedet to  be calculated and then joined with the subjects table to get the average rating of each subject.
def get_subject_overview(subject_id,user_id):
    try:
        with sql_helper.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*
                FROM subjects s    
                WHERE s.id = :subject_id
            """, {"subject_id": subject_id})
            subject = dict(cursor.fetchone())
        check_favorite = favorites.is_favorite(user_id, subject_id=subject_id, favorite_type='subject')
        if check_favorite:
            subject['is_favorite'] = True
            return subject
        else:
            subject['is_favorite'] = False
            print(f"Subject Overview for subject_id {subject_id}: {subject}")  # Debugging line
            return subject
    except Exception as e:
        print(f"Error occurred while fetching subject overview: {e}")
        return None

def create_subject(subject_data, user_authority, user_id):
    try:
        with sql_helper.get_db("main.db") as conn:
            cursor = conn.cursor()
            
            # Data Validation
            s_name = subject_data.get("subject_name")
            s_code = subject_data.get("subject_code")
            if not s_name or not s_code or not subject_data.get("year") or not subject_data.get("semester"):
                raise ValueError("Missing required subject fields.")

            status = "active" if user_authority > 3 else "archived"
            acceptance_status = "1" if user_authority > 3 else "0"
            # Create Subject
            insert_query = """
                INSERT INTO subjects (name, code, year, semester, credits, professor_id, visibility, created_by, sts, accepted)
                VALUES (:name, :code, :year, :semester, :credits, :p_id, :vis, :created_by, :sts, :accepted)
            """
            cursor.execute(insert_query, {
                "name": s_name, 
                "code": s_code, 
                "year": subject_data.get("year"),
                "semester": subject_data.get("semester"),
                "credits": subject_data.get("credits", 0),
                "p_id": subject_data.get("professor_id"),
                "vis": subject_data.get("visibility", "public"),
                "created_by": user_id,
                "sts": status,
                "accepted": acceptance_status
            })
            
            # CAPTURE ID HERE (Immediately after insert)
            subject_id = cursor.lastrowid 
            
            # Notifications
            if status == "active":
                cursor.execute("INSERT INTO notifications (message, send_to_user_type,send_to_year,send_to_semester,type) VALUES (?, ?,?,?,?)",
                               (f"New subject '{s_name}' has been added.", 0,0,0,"notification"))
            else:
                # Notify User
                cursor.execute("INSERT INTO notifications (p_id, message, send_to_user_type,send_to_year,send_to_semester,type) VALUES (?, ?, ?,?,?,?)",
                               (user_id, f"New subject '{s_name}' is awaiting approval.", 1,0,0,"notification"))
                # Notify Admin
                cursor.execute("INSERT INTO notifications (message, send_to_user_type,send_to_year,send_to_semester,type) VALUES (?, ?,?,?,?)",
                               (f"New subject '{s_name}' is awaiting approval.", 3,0,0,"notification"))

            conn.commit()
            return True, None, subject_id

    except Exception as e:
        print(f"Error occurred while adding a new subject: {e}")
        return False, e, None