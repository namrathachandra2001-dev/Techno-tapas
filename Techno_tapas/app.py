from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import random
import os
import csv
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "techno_tapas_secret"

DB_NAME = "database.db"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "techno123"

# -----------------------------
# DATABASE SETUP
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        chit_number TEXT PRIMARY KEY,
        username TEXT,
        college TEXT,
        topic TEXT,
        scrambled TEXT,
        user_answer TEXT,
        used INTEGER DEFAULT 0,
        login_time TEXT,
        unlocked_time TEXT,
        status TEXT,
        marks INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()


def seed_data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    topics = {
"101": "BIOMETRIC SECURITY",
"102": "CYBER SECURITY",
"103": "WOMEN IN TECHNOLOGY",
"104": "SMART CITY INFRASTRUCTURE",
"105": "AI SMART CAMPUS",
"106": "BLOCKCHAIN TECHNOLOGY",
"107": "INTERNET OF THINGS",
"108": "METAVERSE WORLD",
"109": "QUANTUM COMPUTING",
"110": "GREEN TECHNOLOGY",
"111": "CLOUD COMPUTING",
"112": "BIG DATA ANALYTICS POWER",
"113": "EDGE COMPUTING",
"114": "SMART HEALTHCARE SYSTEM",
"115": "VIRTUAL REALITY",
"116": "AUGMENTED REALITY",
"117": "ETHICAL HACKING",
"118": "DIGITAL FORENSICS",
"119": "MACHINE LEARNING IN AGRICULTURE",
"120": "FINTECH INNOVATION 2035",
"121": "AI SMART CITY",
"122": "ARTIFICIAL INTELLIGENCE ",
"123": "DATA PRIVACY",
"124": "INDUSTRY 5.0",
"125": "ROBOTICS"
}

    for chit, topic in topics.items():
        c.execute(
            "INSERT OR IGNORE INTO participants (chit_number, topic) VALUES (?, ?)",
            (chit, topic)
        )

    conn.commit()
    conn.close()


def tough_scramble(word):
    letters = list(word.replace(" ", ""))
    random.shuffle(letters)
    return " ".join(letters)

# -----------------------------
# PARTICIPANT ROUTES
# -----------------------------

@app.route("/", methods=["GET", "POST"])
def welcome():

    if request.method == "POST":

        username = request.form["username"]
        college = request.form["college"]
        chit = request.form["chit"]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute("SELECT topic, used FROM participants WHERE chit_number=?", (chit,))
        data = c.fetchone()

        if not data:
            conn.close()
            return render_template("welcome.html", error="Invalid Chit Number")

        if data[1] == 1:
            conn.close()
            return render_template("welcome.html", error="This Chit Number is already used.")

        topic = data[0]
        scramble_word = tough_scramble(topic)

        login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute("""
        UPDATE participants
        SET username=?, college=?, scrambled=?, login_time=?
        WHERE chit_number=?
        """, (username, college, scramble_word, login_time, chit))

        conn.commit()
        conn.close()

        session["chit"] = chit
        session["topic"] = topic
        session["scramble"] = scramble_word
        session["login_time"] = login_time

        return redirect(url_for("scramble"))

    return render_template("welcome.html")


@app.route("/scramble", methods=["GET", "POST"])
def scramble():

    if "chit" not in session:
        return redirect(url_for("welcome"))

    login_time = datetime.strptime(session["login_time"], "%Y-%m-%d %H:%M:%S")

    elapsed = datetime.now() - login_time
    remaining_seconds = 300 - int(elapsed.total_seconds())

    if remaining_seconds <= 0:

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute("""
        UPDATE participants
        SET status='Failed', marks=-5, used=1
        WHERE chit_number=?
        """, (session["chit"],))

        conn.commit()
        conn.close()

        return render_template("timeout.html", topic=session["topic"])

    if request.method == "POST":

        user_input = request.form.get("answer", "").strip().upper().replace(" ", "")
        correct_answer = session["topic"].upper().replace(" ", "")

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        if user_input == correct_answer:

            c.execute("""
            UPDATE participants
            SET user_answer=?, status='Success', marks=5, unlocked_time=?, used=1
            WHERE chit_number=?
            """, (
                user_input,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                session["chit"]
            ))

            conn.commit()
            conn.close()

            return redirect(url_for("success"))

        else:
            conn.close()

            return render_template(
                "scramble.html",
                scramble=session["scramble"],
                remaining=remaining_seconds,
                error="Incorrect! Try again."
            )

    return render_template(
        "scramble.html",
        scramble=session["scramble"],
        remaining=remaining_seconds
    )


@app.route("/success")
def success():
    return render_template("success.html", topic=session["topic"])


# -----------------------------
# ADMIN ROUTES
# -----------------------------

@app.route("/admin", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        if request.form["username"] == ADMIN_USERNAME and request.form["password"] == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))

        return render_template("admin_login.html", error="Invalid Credentials")

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def admin_dashboard():

    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # All participants
    c.execute("SELECT * FROM participants")
    data = c.fetchall()

    # Leaderboard
    c.execute("""
    SELECT username, college, marks
    FROM participants
    WHERE marks > 0
    ORDER BY marks DESC
    LIMIT 5
    """)
    leaderboard = c.fetchall()

    # Active participants (currently solving)
    c.execute("""
    SELECT username, college
    FROM participants
    WHERE used = 0 AND login_time IS NOT NULL
    """)
    active_users = c.fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        data=data,
        leaderboard=leaderboard,
        active_users=active_users
    )


# -----------------------------
# RESET PARTICIPANT
# -----------------------------

@app.route("/admin/reset/<chit>")
def reset_chit(chit):

    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    UPDATE participants
    SET username=NULL,
        college=NULL,
        scrambled=NULL,
        user_answer=NULL,
        used=0,
        login_time=NULL,
        unlocked_time=NULL,
        status=NULL,
        marks=0
    WHERE chit_number=?
    """, (chit,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


# -----------------------------
# EXPORT CSV
# -----------------------------

@app.route("/admin/export")
def export_csv():

    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM participants")
    rows = c.fetchall()

    conn.close()

    file_path = "results.csv"

    with open(file_path, "w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow([
            "Chit",
            "Name",
            "College",
            "Topic",
            "Scrambled",
            "Answer",
            "Used",
            "LoginTime",
            "UnlockTime",
            "Status",
            "Marks"
        ])

        writer.writerows(rows)

    return "CSV file saved successfully in project folder!"


# -----------------------------
# ADMIN LOGOUT
# -----------------------------

@app.route("/admin/logout")
def admin_logout():

    session.pop("admin", None)

    return redirect(url_for("admin_login"))


# -----------------------------
# MAIN
# -----------------------------

if __name__ == "__main__":
    init_db()
    seed_data()
    app.run(host="0.0.0.0", port=5000)