import modules.sql_helper_dictionary as sql_helper
def list_materials(subject_id: int, filters: dict = None, user_id: int = None, authority: int = 1):
    try:
        with sql_helper.get_db("main.db") as conn:
            cursor = conn.cursor()
            querry = "SELECT * FROM materials m WHERE 1=1 AND m.subject_id = :subject_id"
            params = {"subject_id": subject_id}
            if filters:
                params.update(filters)
            if user_id is not None:
                params["user_id"] = user_id
                querry+=("""
                                AND (m.accepted = 1 OR m.uploaded_by = :user_id)""")
            querry+=("""
                AND (visibility = 'public' OR m.uploaded_by = :user_id)
            """)
            if authority>  2:
                querry=("""
                SELECT * FROM materials m WHERE 1=1
                AND m.subject_id = :subject_id
            """)
            if filters:
                if filters.get("search"):
                    querry += " AND m.title LIKE :material_name"
                    params["material_name"] = f"%{filters['search']}%"
                if filters.get("material_type"):
                    querry += " AND m.material_type = :material_type"
                    params["material_type"] = filters["material_type"]
                if filters.get("content_type"):
                    querry += " AND m.content_type = :content_type"
                    params["content_type"] = filters["content_type"]
            querry += " ORDER BY m.created_at DESC"
            cursor.execute(querry, params)
            materials = dict(cursor.fetchall())
            print(f"Materials listed for subject_id {subject_id} with filters {filters}: {materials}")
            return materials
    except Exception as e:
        print(f"Error occurred while listing materials: {e}")
        return []
def upload_material(subject_id: int, data:dict, user_id: int = None, authority: int = 1):
    try:
        data_use=(data)
        data_use={k: v for k, v in data_use.items() if v is not None}
        with sql_helper.get_db("main.db") as conn:
            cursor = conn.cursor()
            querry = """
                INSERT INTO materials (subject_id, title, material_type, content_type, description, file_path, uploaded_by, accepted, visibility)
                VALUES (:subject_id, :title, :material_type, :content_type, :description, :file_path, :uploaded_by, :accepted, :visibility)
            """
            print(f"Uploading material with data: {data_use}")
            params = {
                "subject_id": subject_id,
                "title": data_use.get("material_title"),
                "material_type": data_use.get("type"),
                "content_type": data_use.get('category'),
                "description": data_use.get("sub_category"),
                "file_path": data_use.get("links"),
                "uploaded_by": user_id,
                "accepted": 0 if authority < 3 else 1,
                "visibility": data_use.get("visibility", "public")
            }
            cursor.execute(querry, params)
            conn.commit()
            return True, None, cursor.lastrowid
    except Exception as e:
        print(f"Error occurred while uploading material: {e}")
        return False, f"An error occurred while uploading the material: {e}", None