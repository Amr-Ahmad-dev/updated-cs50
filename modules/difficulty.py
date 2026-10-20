import modules.sql_helper_dictionary as sql_h

def get_difficulty(subject_id: int):
    """Calculates average difficulty and distribution (1: Very Easy to 5: Very Hard)."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                SELECT difficulty, COUNT(*) as count
                FROM ratings
                WHERE entity_type = 'subject' AND entity_id = ? AND difficulty IS NOT NULL
                GROUP BY difficulty
            """, (subject_id,))
            rows = c.fetchall()

            dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            total = 0
            total_sum = 0
            for r in rows:
                d = r["difficulty"]
                cnt = r["count"]
                if d in dist:
                    dist[d] = cnt
                    total += cnt
                    total_sum += d * cnt

            avg_difficulty = round(total_sum / total, 1) if total > 0 else 0

            # Labels
            labels = {
                1: "Very Easy",
                2: "Easy",
                3: "Moderate",
                4: "Challenging",
                5: "Very Hard"
            }

            breakdown = []
            for lvl in range(1, 6):
                count = dist[lvl]
                pct = round((count / total) * 100, 1) if total > 0 else 0
                breakdown.append({
                    "level": lvl,
                    "label": labels[lvl],
                    "count": count,
                    "percentage": pct
                })

            return {
                "subject_id": subject_id,
                "average_difficulty": avg_difficulty,
                "total_votes": total,
                "breakdown": breakdown
            }
    except Exception as e:
        print(f"Error calculating difficulty: {e}")
        return {"subject_id": subject_id, "average_difficulty": 0, "total_votes": 0, "breakdown": []}


def submit_difficulty(p_id: int, subject_id: int, difficulty_score: int):
    """Submits or updates a difficulty score for a subject."""
    try:
        score = max(1, min(5, int(difficulty_score)))
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO ratings (p_id, entity_type, entity_id, raw_score, difficulty)
                VALUES (?, 'subject', ?, 3, ?)
                ON CONFLICT(p_id, entity_type, entity_id) DO UPDATE SET
                    difficulty = excluded.difficulty,
                    created_at = CURRENT_TIMESTAMP
            """, (p_id, subject_id, score))
            conn.commit()
            return True, None
    except Exception as e:
        print(f"Error submitting difficulty: {e}")
        return False, str(e)
