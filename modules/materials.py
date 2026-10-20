import modules.sql_helper_dictionary as sql_h

def list_materials(subject_id: int, filters: dict = None, user_id: int = None, authority: int = 1):
    """Lists materials for a subject with permission and filter handling."""
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            query = """
                SELECT m.*, p.name as uploader_name, p.avatar as uploader_avatar,
                       (SELECT AVG(raw_score) FROM ratings WHERE entity_type = 'material' AND entity_id = m.id) as avg_rating
                FROM materials m
                LEFT JOIN profiles p ON m.uploaded_by = p.p_id
                WHERE m.subject_id = :subject_id
            """
            params = {"subject_id": subject_id}

            # Visibility & Approval restrictions for regular students
            if authority < 2:
                if user_id is not None:
                    query += " AND (m.accepted = 1 OR m.uploaded_by = :user_id)"
                    params["user_id"] = user_id
                else:
                    query += " AND m.accepted = 1"

            if filters:
                if filters.get("search"):
                    query += " AND (m.title LIKE :search OR m.description LIKE :search)"
                    params["search"] = f"%{filters['search']}%"
                if filters.get("material_type"):
                    query += " AND m.material_type = :material_type"
                    params["material_type"] = filters["material_type"]
                if filters.get("content_type"):
                    query += " AND m.content_type = :content_type"
                    params["content_type"] = filters["content_type"]

            query += " ORDER BY m.created_at DESC"
            cursor.execute(query, params)
            materials = [dict(r) for r in cursor.fetchall()]
            return materials
    except Exception as e:
        print(f"Error occurred while listing materials: {e}")
        return []


def upload_material(subject_id: int, data: dict, user_id: int = None, authority: int = 1):
    """Uploads a new learning material."""
    try:
        title = data.get("title") or data.get("material_title")
        if not title:
            return False, "Material title is required.", None

        mat_type = data.get("material_type") or data.get("type") or "document"
        content_type = data.get("content_type") or data.get("category") or "official"
        description = data.get("description") or data.get("sub_category") or ""
        file_path = data.get("file_path") or data.get("links") or ""
        visibility = data.get("visibility", "public")

        is_auto_approved = 1 if (authority and authority >= 2) else 0

        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO materials (subject_id, uploaded_by, title, description, file_path, material_type, content_type, visibility, accepted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (subject_id, user_id, title, description, file_path, mat_type, content_type, visibility, is_auto_approved))
            
            material_id = cursor.lastrowid
            conn.commit()
            return True, None, material_id
    except Exception as e:
        print(f"Error occurred while uploading material: {e}")
        return False, str(e), None


def get_material(material_id: int):
    """Retrieves full details of a single material."""
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.*, s.name as subject_name, s.code as subject_code, p.name as uploader_name
                FROM materials m
                JOIN subjects s ON m.subject_id = s.id
                LEFT JOIN profiles p ON m.uploaded_by = p.p_id
                WHERE m.id = ?
            """, (material_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"Error occurred while fetching material: {e}")
        return None


def edit_material(material_id: int, data: dict):
    """Edits an existing material's title, description, links, and type."""
    try:
        title = data.get("title") or data.get("material_title")
        description = data.get("description") or data.get("sub_category") or ""
        material_type = data.get("material_type") or data.get("type") or "document"
        content_type = data.get("content_type") or data.get("category") or "official"
        file_path = data.get("file_path") or data.get("links") or ""
        visibility = data.get("visibility", "public")

        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE materials 
                SET title = ?, description = ?, material_type = ?, content_type = ?, file_path = ?, visibility = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (title, description, material_type, content_type, file_path, visibility, material_id))
            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error editing material: {e}")
        return False, str(e)


def delete_material(material_id: int):
    """Deletes a material from the database."""
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error deleting material: {e}")
        return False, str(e)