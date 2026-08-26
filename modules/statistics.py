import modules.sql_helper_dictionary as sql_h

def get_subject_stats(subject_id: int):
    """Calculates comprehensive subject statistics: GPA, grade distribution, hours studied, and pass rates."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            
            # Fetch grades data for this subject
            c.execute("""
                SELECT letter, grade, hours_studied
                FROM student_grades
                WHERE subject_id = ?
            """, (subject_id,))
            grades = [dict(r) for r in c.fetchall()]

            total_grades = len(grades)
            avg_gpa = round(sum(g["grade"] for g in grades) / total_grades, 2) if total_grades > 0 else None
            
            valid_hours = [g["hours_studied"] for g in grades if g.get("hours_studied") is not None]
            avg_hours = round(sum(valid_hours) / len(valid_hours), 1) if valid_hours else None

            # Letter distributions
            letter_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
            passing_count = 0
            for g in grades:
                let = (g.get("letter") or "").upper()
                if let in letter_counts:
                    letter_counts[let] += 1
                if let in ["A", "B", "C", "D"] or (g.get("grade") and g["grade"] >= 1.0):
                    passing_count += 1

            pass_rate = round((passing_count / total_grades) * 100, 1) if total_grades > 0 else None

            distribution = []
            for letter in ["A", "B", "C", "D", "F"]:
                count = letter_counts[letter]
                pct = round((count / total_grades) * 100, 1) if total_grades > 0 else 0
                distribution.append({
                    "letter": letter,
                    "count": count,
                    "percentage": pct
                })

            return {
                "subject_id": subject_id,
                "total_students": total_grades,
                "average_gpa": avg_gpa,
                "average_hours_studied": avg_hours,
                "pass_rate": pass_rate,
                "grade_distribution": distribution
            }
    except Exception as e:
        print(f"Error calculating subject statistics: {e}")
        return {
            "subject_id": subject_id,
            "total_students": 0,
            "average_gpa": None,
            "average_hours_studied": None,
            "pass_rate": None,
            "grade_distribution": []
        }


def get_student_stats(p_id: int):
    """Calculates student academic performance metrics."""
    try:
        with sql_h.get_db("main.db") as conn:
            c = conn.cursor()
            c.execute("""
                SELECT sg.*, s.name as subject_name, s.code as subject_code, s.credits
                FROM student_grades sg
                JOIN subjects s ON sg.subject_id = s.id
                WHERE sg.p_id = ?
                ORDER BY sg.year ASC, sg.semester ASC
            """, (p_id,))
            grades = [dict(r) for r in c.fetchall()]

            total_courses = len(grades)
            total_credits = sum(g.get("credits", 3) for g in grades)
            total_points = sum(g["grade"] * g.get("credits", 3) for g in grades)
            gpa = round(total_points / total_credits, 2) if total_credits > 0 else 0.0

            return {
                "p_id": p_id,
                "gpa": gpa,
                "total_credits": total_credits,
                "total_courses": total_courses,
                "course_grades": grades
            }
    except Exception as e:
        print(f"Error calculating student statistics: {e}")
        return {"p_id": p_id, "gpa": 0.0, "total_credits": 0, "total_courses": 0, "course_grades": []}
