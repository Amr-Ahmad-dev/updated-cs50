import modules.sql_helper_dictionary as sql_h

def get_ratings(entity_type: str, entity_id: int):
    """Calculates average rating, total votes, and star distribution."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                SELECT raw_score, difficulty, gpa_at_vote, created_at,
                       p.name as voter_name, p.avatar as voter_avatar
                FROM ratings r
                LEFT JOIN profiles p ON r.p_id = p.p_id
                WHERE r.entity_type = ? AND r.entity_id = ?
                ORDER BY r.created_at DESC
            """, (entity_type, entity_id))
            reviews = [dict(r) for r in c.fetchall()]

            total_votes = len(reviews)
            avg_score = round(sum(r["raw_score"] for r in reviews) / total_votes, 1) if total_votes > 0 else 0
            
            # Star counts
            distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for r in reviews:
                distribution[r["raw_score"]] = distribution.get(r["raw_score"], 0) + 1

            return {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "average_score": avg_score,
                "total_votes": total_votes,
                "distribution": distribution,
                "reviews": reviews
            }
    except Exception as e:
        print(f"Error getting ratings: {e}")
        return {"average_score": 0, "total_votes": 0, "distribution": {1:0, 2:0, 3:0, 4:0, 5:0}, "reviews": []}


def add_rating(p_id: int, entity_type: str, entity_id: int, raw_score: int, difficulty: int = None, gpa: float = None):
    """Submits or updates a rating for an entity (subject, material, professor, assignment)."""
    try:
        score = max(1, min(5, int(raw_score)))
        diff = max(1, min(5, int(difficulty))) if difficulty is not None else None

        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO ratings (p_id, entity_type, entity_id, raw_score, difficulty, gpa_at_vote)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(p_id, entity_type, entity_id) DO UPDATE SET
                    raw_score = excluded.raw_score,
                    difficulty = COALESCE(excluded.difficulty, ratings.difficulty),
                    gpa_at_vote = COALESCE(excluded.gpa_at_vote, ratings.gpa_at_vote),
                    created_at = CURRENT_TIMESTAMP
            """, (p_id, entity_type, entity_id, score, diff, gpa))
            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error adding rating: {e}")
        return False, str(e)


def get_user_rating(p_id: int, entity_type: str, entity_id: int):
    """Gets the rating submitted by a specific user for an entity."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                SELECT * FROM ratings 
                WHERE p_id = ? AND entity_type = ? AND entity_id = ?
            """, (p_id, entity_type, entity_id))
            row = c.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"Error getting user rating: {e}")
        return None
