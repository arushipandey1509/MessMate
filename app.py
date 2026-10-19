import json
import os
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("MESSMATE_DB_PATH", BASE_DIR / "messmate.db"))
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("MESSMATE_SECRET_KEY", "dev-only-change-this-secret-before-deployment")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("MESSMATE_HTTPS", "0") == "1"
ADMIN_USERNAME = os.environ.get("MESSMATE_ADMIN_USERNAME", "Arushi")
ADMIN_PASSWORD = os.environ.get("MESSMATE_ADMIN_PASSWORD", "Pandey@123")
MEALS = ("breakfast", "lunch", "dinner")
SLOTS = ("12:00–12:30", "12:30–1:00", "1:00–1:30")


def get_db():
    if "db" not in g:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS weekly_menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
            meal_type TEXT NOT NULL CHECK(meal_type IN ('breakfast','lunch','dinner')),
            items TEXT NOT NULL DEFAULT '',
            UNIQUE(weekday, meal_type)
        );
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS meal_selections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            meal_date TEXT NOT NULL,
            meal_type TEXT NOT NULL CHECK(meal_type IN ('breakfast','lunch','dinner')),
            slot TEXT NOT NULL,
            selected_items TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, meal_date, meal_type)
        );
    """)
    for weekday in range(7):
        for meal in MEALS:
            db.execute("INSERT OR IGNORE INTO weekly_menu (weekday, meal_type, items) VALUES (?, ?, ?)",
                       (weekday, meal, "Rice, Dal, Seasonal vegetable" if meal == "lunch" else ""))
    db.commit()


@app.before_request
def ensure_db():
    init_db()


def student_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "student":
            flash("Please log in with your student account first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Administrator access is required.", "warning")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


def menu_for_week(db):
    rows = db.execute("SELECT weekday, meal_type, items FROM weekly_menu ORDER BY weekday").fetchall()
    result = {i: {meal: "" for meal in MEALS} for i in range(7)}
    for row in rows:
        result[row["weekday"]][row["meal_type"]] = row["items"]
    return result


@app.template_filter("from_json")
def from_json_filter(raw):
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []


def parse_items(raw):
    return [part.strip() for part in raw.split(",") if part.strip()]


@app.route("/")
def index():
    db = get_db()
    notices = db.execute("SELECT * FROM notices ORDER BY id DESC LIMIT 5").fetchall()
    today_menu = db.execute("SELECT meal_type, items FROM weekly_menu WHERE weekday=? ORDER BY CASE meal_type WHEN 'breakfast' THEN 1 WHEN 'lunch' THEN 2 ELSE 3 END", (date.today().weekday(),)).fetchall()
    today_demand = db.execute("SELECT COUNT(*) AS total FROM meal_selections WHERE meal_date=?", (date.today().isoformat(),)).fetchone()["total"]
    return render_template("index.html", notices=notices, today_menu=today_menu, today_demand=today_demand)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not all((student_id, name, email, password)):
            flash("Please complete every field.", "error")
        elif len(password) < 8:
            flash("Use a password with at least 8 characters.", "error")
        else:
            try:
                db = get_db()
                db.execute("INSERT INTO students (student_id, name, email, password_hash) VALUES (?, ?, ?, ?)",
                           (student_id, name, email, generate_password_hash(password)))
                db.commit()
                flash("Account created. You can now log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That student ID or email is already registered.", "error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        student = get_db().execute("SELECT * FROM students WHERE student_id=? OR email=?", (identity, identity.lower())).fetchone()
        if student and check_password_hash(student["password_hash"], password):
            session.clear()
            session["role"] = "student"
            session["student_pk"] = student["id"]
            session["student_name"] = student["name"]
            return redirect(url_for("student_dashboard"))
        flash("The student ID/email or password is incorrect.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/student")
@student_required
def student_dashboard():
    db = get_db()
    today = date.today()
    weekday = today.weekday()
    menu = db.execute("SELECT meal_type, items FROM weekly_menu WHERE weekday=?", (weekday,)).fetchall()
    menu_map = {r["meal_type"]: parse_items(r["items"]) for r in menu}
    selections = db.execute("SELECT * FROM meal_selections WHERE student_id=? AND meal_date=?", (session["student_pk"], today.isoformat())).fetchall()
    selection_map = {r["meal_type"]: r for r in selections}
    notices = db.execute("SELECT * FROM notices ORDER BY id DESC LIMIT 8").fetchall()
    week_menu = menu_for_week(db)
    return render_template("student.html", today=today, meals=MEALS, menu_map=menu_map,
                           selection_map=selection_map, notices=notices, week_menu=week_menu, slots=SLOTS)


@app.route("/api/selections", methods=["POST"])
@student_required
def save_selection():
    payload = request.get_json(silent=True) or {}
    meal_type = payload.get("meal_type")
    slot = payload.get("slot")
    items = payload.get("items")
    if meal_type not in MEALS or slot not in SLOTS or not isinstance(items, list):
        return jsonify(error="Please choose a valid meal, slot, and food items."), 400
    db = get_db()
    allowed_row = db.execute("SELECT items FROM weekly_menu WHERE weekday=? AND meal_type=?", (date.today().weekday(), meal_type)).fetchone()
    allowed = parse_items(allowed_row["items"] if allowed_row else "")
    clean_items = list(dict.fromkeys(i for i in items if isinstance(i, str) and i in allowed))
    if not clean_items:
        return jsonify(error="Select at least one item from today's menu."), 400
    db.execute("""INSERT INTO meal_selections (student_id, meal_date, meal_type, slot, selected_items)
                  VALUES (?, ?, ?, ?, ?)
                  ON CONFLICT(student_id, meal_date, meal_type) DO UPDATE SET slot=excluded.slot, selected_items=excluded.selected_items""",
               (session["student_pk"], date.today().isoformat(), meal_type, slot, json.dumps(clean_items)))
    db.commit()
    return jsonify(message="Your meal selection has been saved.")


@app.route("/api/selections/<meal_type>", methods=["DELETE"])
@student_required
def delete_selection(meal_type):
    if meal_type not in MEALS:
        return jsonify(error="Invalid meal type."), 400
    db = get_db()
    db.execute("DELETE FROM meal_selections WHERE student_id=? AND meal_date=? AND meal_type=?",
               (session["student_pk"], date.today().isoformat(), meal_type))
    db.commit()
    return jsonify(message="Your selection has been cancelled.")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session["role"] = "admin"
            session["admin_name"] = username
            return redirect(url_for("admin_dashboard"))
        flash("Invalid administrator credentials.", "error")
    return render_template("admin_login.html")


@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    target_date = request.args.get("date", date.today().isoformat())
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        target_date = date.today().isoformat()
    selections = db.execute("SELECT ms.*, s.student_id AS student_code, s.name FROM meal_selections ms JOIN students s ON s.id=ms.student_id WHERE ms.meal_date=? ORDER BY ms.meal_type, ms.slot, s.name", (target_date,)).fetchall()
    item_counts = {}
    slot_counts = {meal: {slot: 0 for slot in SLOTS} for meal in MEALS}
    meal_counts = {meal: 0 for meal in MEALS}
    for row in selections:
        meal_counts[row["meal_type"]] += 1
        slot_counts[row["meal_type"]][row["slot"]] = slot_counts[row["meal_type"]].get(row["slot"], 0) + 1
        for item in json.loads(row["selected_items"]):
            item_counts[item] = item_counts.get(item, 0) + 1
    total_students = db.execute("SELECT COUNT(*) AS n FROM students").fetchone()["n"]
    notices = db.execute("SELECT * FROM notices ORDER BY id DESC LIMIT 10").fetchall()
    week_menu = menu_for_week(db)
    return render_template("admin.html", target_date=target_date, selections=selections, item_counts=item_counts,
                           slot_counts=slot_counts, meal_counts=meal_counts, total_students=total_students,
                           notices=notices, week_menu=week_menu, weekdays=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], meals=MEALS, slots=SLOTS)


@app.route("/admin/menu", methods=["POST"])
@admin_required
def update_menu():
    db = get_db()
    for weekday in range(7):
        for meal in MEALS:
            raw = request.form.get(f"menu_{weekday}_{meal}", "")
            # Store a normalized comma-separated list; no HTML is rendered from it unescaped.
            items = ", ".join(dict.fromkeys(part.strip() for part in raw.split(",") if part.strip()))
            db.execute("INSERT INTO weekly_menu (weekday, meal_type, items) VALUES (?, ?, ?) ON CONFLICT(weekday, meal_type) DO UPDATE SET items=excluded.items", (weekday, meal, items))
    db.commit()
    flash("Weekly menu updated for students and administrators.", "success")
    return redirect(url_for("admin_dashboard") + "#weekly-menu")


@app.route("/admin/notices", methods=["POST"])
@admin_required
def post_notice():
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not title or not body:
        flash("Notice title and message are both required.", "error")
    elif len(title) > 120 or len(body) > 1500:
        flash("The title or message is too long.", "error")
    else:
        db = get_db()
        db.execute("INSERT INTO notices (title, body) VALUES (?, ?)", (title, body))
        db.commit()
        flash("Notice published.", "success")
    return redirect(url_for("admin_dashboard") + "#notices")


@app.route("/admin/notices/<int:notice_id>/delete", methods=["POST"])
@admin_required
def delete_notice(notice_id):
    db = get_db()
    db.execute("DELETE FROM notices WHERE id=?", (notice_id,))
    db.commit()
    flash("Notice deleted.", "success")
    return redirect(url_for("admin_dashboard") + "#notices")


if __name__ == "__main__":
    app.run(debug=os.environ.get("MESSMATE_DEBUG", "0") == "1")
