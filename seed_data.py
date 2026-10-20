"""
seed_data.py -- Idempotent sample data for Ledger.
Run once after data.py to populate with realistic educational data.
Safe to run multiple times (INSERT OR IGNORE).

Test accounts:
  admin@ledger.local     / admin123    (Admin L3, status=4)
  professor@ledger.local / prof123     (Professor, status=7)
  student@ledger.local   / student123  (Student, status=1)
"""
import os, sqlite3
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_DB = os.path.join(BASE_DIR, "databases", "auth.db")
MAIN_DB = os.path.join(BASE_DIR, "databases", "main.db")

def _ac():
    c = sqlite3.connect(AUTH_DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL;")
    return c

def _mc():
    c = sqlite3.connect(MAIN_DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON;")
    c.execute("PRAGMA journal_mode=WAL;")
    return c

SAMPLE_USERS = [
    ("admin@ledger.local",     "admin123",   4, 1, "Admin User",     "Platform administrator."),
    ("professor@ledger.local", "prof123",    7, 1, "Dr. Sarah Chen", "Professor of Computer Science."),
    ("student@ledger.local",   "student123", 1, 1, "Alex Johnson",   "Third-year CS student."),
    ("student2@ledger.local",  "student123", 1, 1, "Maya Patel",     "Second-year student."),
]

def seed_users():
    print("Seeding users...")
    with _ac() as a, _mc() as m:
        for email, pw, status, approved, name, bio in SAMPLE_USERS:
            row = a.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            if row:
                uid = row["id"]
                print(f"  {email} exists (id={uid})")
            else:
                pw_h = generate_password_hash(pw)
                a.execute("INSERT INTO users (email,password,status,approved,state,warning_count) VALUES (?,?,?,?,0,0)",
                          (email, pw_h, status, approved))
                a.commit()
                uid = a.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"]
                print(f"  Created {email} (id={uid})")
            if not m.execute("SELECT p_id FROM profiles WHERE p_id=?", (uid,)).fetchone():
                m.execute("INSERT INTO profiles (p_id,email,name,bio,avatar,current_year,current_semester) VALUES (?,?,?,?,'',1,1)",
                          (uid, email, name, bio))
                m.execute("INSERT OR IGNORE INTO users (id,email,p_id) VALUES (?,?,?)", (uid, email, uid))
                if status == 7:
                    m.execute("INSERT OR IGNORE INTO professors (user_id,office,department,bio) VALUES (?,?,?,?)",
                              (uid, "Room 301, CS Bldg", "Computer Science", bio))
                m.commit()
                print(f"  Profile: {name}")
    print("Users seeded.")

SAMPLE_SUBJECTS = [
    ("CS101","Introduction to Computer Science","Fundamental computing concepts using Python.",1,1,3,"professor@ledger.local"),
    ("CS102","Data Structures and Algorithms","Arrays, trees, graphs and sorting.",1,2,3,"professor@ledger.local"),
    ("MATH101","Calculus I","Limits, derivatives, integrals and applications.",1,1,4,None),
    ("MATH102","Discrete Mathematics","Sets, logic, proofs, combinatorics.",1,2,3,None),
    ("CS201","Object-Oriented Programming","Classes, inheritance, design patterns.",2,1,3,"professor@ledger.local"),
    ("CS202","Database Systems","SQL, normalization, transactions.",2,1,3,"professor@ledger.local"),
    ("CS203","Operating Systems","Processes, memory, file systems.",2,2,3,"professor@ledger.local"),
    ("CS301","Algorithms","Dynamic programming, greedy, NP-completeness.",3,1,3,"professor@ledger.local"),
    ("CS302","Computer Networks","TCP/IP, routing, security.",3,1,3,None),
    ("CS401","Machine Learning","Supervised and unsupervised learning.",4,1,3,None),
]

def seed_subjects():
    print("Seeding subjects...")
    with _mc() as m, _ac() as a:
        adm = a.execute("SELECT id FROM users WHERE email='admin@ledger.local'").fetchone()
        aid = adm["id"] if adm else 1
        for code,name,desc,year,sem,credits,prof_email in SAMPLE_SUBJECTS:
            if m.execute("SELECT id FROM subjects WHERE code=?", (code,)).fetchone():
                print(f"  {code} exists"); continue
            pid = None
            if prof_email:
                pr = a.execute("SELECT id FROM users WHERE email=?", (prof_email,)).fetchone()
                if pr: pid = pr["id"]
            m.execute("INSERT INTO subjects (code,name,description,year,semester,credits,professor_id,visibility,created_by,sts,accepted) VALUES (?,?,?,?,?,?,?,'public',?,'active',1)",
                      (code,name,desc,year,sem,credits,pid,aid))
            m.commit()
            print(f"  {code} - {name}")
    print("Subjects seeded.")

def seed_materials():
    print("Seeding materials...")
    with _mc() as m, _ac() as a:
        pr = a.execute("SELECT id FROM users WHERE email='professor@ledger.local'").fetchone()
        pid = pr["id"] if pr else 1
        for s in m.execute("SELECT id,code FROM subjects WHERE accepted=1").fetchall():
            if m.execute("SELECT COUNT(*) as c FROM materials WHERE subject_id=?", (s["id"],)).fetchone()["c"] > 0:
                continue
            for title,desc,mt,ct in [
                (s["code"]+" Course Syllabus","Course outline and schedule.","document","official"),
                (s["code"]+" Lecture Notes Wk1","Introduction lecture slides.","presentation","official"),
                (s["code"]+" Practice Problems","Self-study problem set.","document","non-official"),
            ]:
                m.execute("INSERT OR IGNORE INTO materials (subject_id,uploaded_by,title,description,file_path,material_type,content_type,visibility,accepted) VALUES (?,?,?,?,'',?,?,'public',1)",
                          (s["id"],pid,title,desc,mt,ct))
            m.commit()
            print(f"  Materials for {s['code']}")
    print("Materials seeded.")

def seed_assignments():
    print("Seeding assignments...")
    with _mc() as m:
        for s in m.execute("SELECT id,code,year,semester FROM subjects WHERE accepted=1").fetchall():
            if m.execute("SELECT COUNT(*) as c FROM assignments WHERE subject_id=?", (s["id"],)).fetchone()["c"] > 0:
                continue
            for title,desc,dd in [
                (s["code"]+" Assignment 1","Introductory exercises.","2026-12-01 23:59:00"),
                (s["code"]+" Midterm Project","Implementation project.","2026-12-15 23:59:00"),
                (s["code"]+" Final Exam Prep","Review problems.","2027-01-10 23:59:00"),
            ]:
                m.execute("INSERT OR IGNORE INTO assignments (subject_id,year,semester,title,description,due_date,visibility) VALUES (?,?,?,?,?,?,'public')",
                          (s["id"],s["year"],s["semester"],title,desc,dd))
            m.commit()
            print(f"  Assignments for {s['code']}")
    print("Assignments seeded.")

def seed_events():
    print("Seeding events...")
    with _mc() as m, _ac() as a:
        if m.execute("SELECT COUNT(*) as c FROM events").fetchone()["c"] > 0:
            print("  Events exist, skipping."); return
        adm = a.execute("SELECT id FROM users WHERE email='admin@ledger.local'").fetchone()
        aid = adm["id"] if adm else 1
        for title,desc,grade,sem,status,evdate in [
            ("Registration Deadline","Last day to register for next semester.",1,1,"upcoming","2026-11-30 23:59:00"),
            ("CS Open House","Meet professors and explore research.",1,1,"upcoming","2026-11-15 14:00:00"),
            ("Study Skills Workshop","Time management for final exams.",1,1,"upcoming","2026-11-20 10:00:00"),
            ("Midterm Exam Period","Check individual subject schedules.",1,1,"upcoming","2026-11-05 08:00:00"),
        ]:
            m.execute("INSERT INTO events (created_by,grade,semester,status,title,description,url,event_date) VALUES (?,?,?,?,?,?,'',?)",
                      (aid,grade,sem,status,title,desc,evdate))
        m.commit()
    print("Events seeded.")

def seed_notifications():
    print("Seeding notifications...")
    with _mc() as m:
        if m.execute("SELECT COUNT(*) as c FROM notifications").fetchone()["c"] > 0:
            print("  Notifications exist, skipping."); return
        for msg,ntype in [
            ("Welcome to Ledger! Explore the subject catalog to get started.","info"),
            ("New subjects added for the upcoming semester.","announcement"),
            ("Reminder: Registration deadline is approaching.","reminder"),
        ]:
            m.execute("INSERT INTO notifications (type,message,send_to_year,send_to_semester) VALUES (?,?,0,0)",(ntype,msg))
        m.commit()
    print("Notifications seeded.")

def seed_grades():
    print("Seeding grades...")
    with _mc() as m, _ac() as a:
        sr = a.execute("SELECT id FROM users WHERE email='student@ledger.local'").fetchone()
        if not sr: return
        sid = sr["id"]
        pool = [("A",4.0,8.5),("A",3.7,7.0),("B",3.0,6.5),("B",3.3,6.0)]
        for i,s in enumerate(m.execute("SELECT id,year,semester FROM subjects WHERE year=1 AND accepted=1").fetchall()):
            g = pool[i % len(pool)]
            if not m.execute("SELECT id FROM student_grades WHERE p_id=? AND subject_id=?",(sid,s["id"])).fetchone():
                m.execute("INSERT INTO student_grades (p_id,subject_id,year,semester,letter,grade,hours_studied) VALUES (?,?,?,?,?,?,?)",
                          (sid,s["id"],s["year"],s["semester"],g[0],g[1],g[2]))
        gs = m.execute("SELECT grade FROM student_grades WHERE p_id=?",(sid,)).fetchall()
        if gs:
            avg = sum(g["grade"] for g in gs) / len(gs)
            m.execute("UPDATE profiles SET average_gpa=?,current_year=2,current_semester=1 WHERE p_id=?",(round(avg,2),sid))
        m.commit()
        print(f"  Grades for student id={sid}")
    print("Grades seeded.")

def seed_prerequisites():
    print("Seeding prerequisites...")
    with _mc() as m:
        for sc,pc in [("CS102","CS101"),("CS201","CS102"),("CS202","MATH102"),
                      ("CS203","CS201"),("CS301","CS102"),("CS401","CS301")]:
            sr = m.execute("SELECT id FROM subjects WHERE code=?",(sc,)).fetchone()
            pr = m.execute("SELECT id FROM subjects WHERE code=?",(pc,)).fetchone()
            if sr and pr and not m.execute("SELECT 1 FROM subject_prerequisites WHERE subject_id=? AND prerequisite_subject_id=?",(sr["id"],pr["id"])).fetchone():
                m.execute("INSERT INTO subject_prerequisites (subject_id,prerequisite_subject_id) VALUES (?,?)",(sr["id"],pr["id"]))
        m.commit()
    print("Prerequisites seeded.")

if __name__ == "__main__":
    print("=" * 55)
    print("Ledger -- Seeding Sample Data")
    print("=" * 55)
    seed_users()
    seed_subjects()
    seed_materials()
    seed_assignments()
    seed_events()
    seed_notifications()
    seed_grades()
    seed_prerequisites()
    print("=" * 55)
    print("Complete! Test accounts:")
    print("  admin@ledger.local     / admin123   (Admin L3)")
    print("  professor@ledger.local / prof123    (Professor)")
    print("  student@ledger.local   / student123 (Student)")
    print("=" * 55)
