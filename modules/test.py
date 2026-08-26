import smtplib
from email.message import EmailMessage
import sql_helper_dictionary as sql_helper
EMAIL = "studentflowapp2026@gmail.com"
PASSWORD = "fapj zqss msrq qupf"

msg = EmailMessage()
msg["Subject"] = "Test"
msg["From"] = EMAIL
msg["To"] = "01100898136a@gmail.com"

msg.set_content("Hello from Python!")

with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.starttls()
    server.login(EMAIL, PASSWORD)
    server.send_message(msg)
with sql_helper.get_db("main.db") as conn:
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(subjects);")
    subjects = cursor.fetchall()
    print(subjects)
print("Done")
