import os
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from io import StringIO
import csv

from flask import Flask, abort, flash, g, make_response, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "attendance.db"))
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    # Convenient for local development only. Set SECRET_KEY in production.
    SECRET_KEY = "dev-only-change-this-secret-before-deployment"

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,
)

STATUSES = ("Present", "Absent", "Leave")


def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DATABASE) or ".", exist_ok=True)
        g.db = sqlite3.connect(DATABASE, timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA busy_timeout = 15000")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','teacher')),
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        section TEXT NOT NULL,
        UNIQUE(name, section)
    );
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admission_no TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE RESTRICT,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );
    CREATE TABLE IF NOT EXISTS teacher_classes (
        teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
        PRIMARY KEY(teacher_id, class_id)
    );
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE RESTRICT,
        attendance_date TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Present','Absent','Leave')),
        marked_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, attendance_date)
    );
    """)
    # Seed demo data only when there are no users. Change/remove demo credentials before real use.
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        db.execute("INSERT INTO users(username, full_name, password_hash, role) VALUES(?,?,?,?)",
                   ("admin", "School Administrator", generate_password_hash("ChangeMe123!"), "admin"))
        db.execute("INSERT INTO users(username, full_name, password_hash, role) VALUES(?,?,?,?)",
                   ("teacher", "Demo Teacher", generate_password_hash("Teacher123!"), "teacher"))
        class_id = db.execute("INSERT INTO classes(name, section) VALUES(?,?)", ("10", "A")).lastrowid
        db.execute("INSERT INTO teacher_classes(teacher_id, class_id) VALUES(?,?)",
                   (db.execute("SELECT id FROM users WHERE username='teacher'").fetchone()["id"], class_id))
        db.executemany("INSERT INTO students(admission_no, full_name, class_id) VALUES(?,?,?)", [
            ("DEMO001", "Arun Kumar", class_id),
            ("DEMO002", "Kavya S", class_id),
            ("DEMO003", "Mohammed Ali", class_id),
            ("DEMO004", "Priya R", class_id),
        ])
        db.executemany("INSERT INTO subjects(name) VALUES(?)", [("Mathematics",), ("English",), ("Science",)])
    db.commit()


@app.before_request
def ensure_database():
    init_db()


def current_user():
    if "user_id" not in session:
        return None
    return get_db().execute(
        "SELECT id, username, full_name, role, active FROM users WHERE id=? AND active=1",
        (session["user_id"],)
    ).fetchone()


@app.context_processor
def inject_user():
    return {"current_user": current_user(), "today": date.today().isoformat()}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                flash("Please sign in to continue.", "warning")
                return redirect(url_for("login"))
            if user["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)
        return decorator
    return decorator


def valid_date(value):
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
        return parsed.isoformat()
    except (TypeError, ValueError):
        return None


def allowed_class_ids(user):
    if user["role"] == "admin":
        return None
    rows = get_db().execute("SELECT class_id FROM teacher_classes WHERE teacher_id=?", (user["id"],)).fetchall()
    return {r["class_id"] for r in rows}


def can_access_class(user, class_id):
    allowed = allowed_class_ids(user)
    return allowed is None or class_id in allowed


@app.route("/")
def index():
    if current_user():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username=? AND active=1", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash(f"Welcome, {user['full_name']}.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.post("/logout")
@login_required
def logout():
    session.clear()
    flash("You have signed out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    user = current_user()
    if user["role"] == "admin":
        student_count = db.execute("SELECT COUNT(*) FROM students WHERE active=1").fetchone()[0]
        class_count = db.execute("SELECT COUNT(*) FROM classes").fetchone()[0]
        teacher_count = db.execute("SELECT COUNT(*) FROM users WHERE role='teacher' AND active=1").fetchone()[0]
        today_count = db.execute("SELECT COUNT(*) FROM attendance WHERE attendance_date=?", (date.today().isoformat(),)).fetchone()[0]
        recent = db.execute("""SELECT a.attendance_date, a.status, s.full_name, s.admission_no, c.name AS class_name, c.section
            FROM attendance a JOIN students s ON s.id=a.student_id JOIN classes c ON c.id=s.class_id
            ORDER BY a.attendance_date DESC, s.full_name LIMIT 8""").fetchall()
        return render_template("admin_dashboard.html", student_count=student_count, class_count=class_count,
                               teacher_count=teacher_count, today_count=today_count, recent=recent)
    classes = get_db().execute("""SELECT c.* FROM classes c JOIN teacher_classes tc ON tc.class_id=c.id
        WHERE tc.teacher_id=? ORDER BY c.name, c.section""", (user["id"],)).fetchall()
    return render_template("teacher_dashboard.html", classes=classes)


@app.route("/students")
@login_required
def students():
    db = get_db()
    user = current_user()
    q = request.args.get("q", "").strip()[:100]
    class_filter = request.args.get("class_id", type=int)
    classes = db.execute("SELECT * FROM classes ORDER BY name, section").fetchall()
    where, params = ["s.active=1"], []
    if q:
        where.append("(s.full_name LIKE ? OR s.admission_no LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    if class_filter:
        if not can_access_class(user, class_filter):
            abort(403)
        where.append("s.class_id=?")
        params.append(class_filter)
    elif user["role"] == "teacher":
        ids = allowed_class_ids(user) or set()
        if not ids:
            where.append("1=0")
        else:
            where.append("s.class_id IN (" + ",".join("?" for _ in ids) + ")")
            params.extend(sorted(ids))
    rows = db.execute("""SELECT s.*, c.name AS class_name, c.section FROM students s
        JOIN classes c ON c.id=s.class_id WHERE """ + " AND ".join(where) +
        " ORDER BY c.name, c.section, s.full_name", params).fetchall()
    return render_template("students.html", students=rows, classes=classes, q=q, class_filter=class_filter)


@app.route("/students/add", methods=["GET", "POST"])
@login_required
@role_required("admin")
def add_student():
    db = get_db()
    classes = db.execute("SELECT * FROM classes ORDER BY name, section").fetchall()
    if request.method == "POST":
        admission = request.form.get("admission_no", "").strip()[:30]
        name = request.form.get("full_name", "").strip()[:100]
        class_id = request.form.get("class_id", type=int)
        if not admission or not name or not class_id or not db.execute("SELECT id FROM classes WHERE id=?", (class_id,)).fetchone():
            flash("Enter a valid admission number, student name, and class.", "danger")
        else:
            try:
                db.execute("INSERT INTO students(admission_no, full_name, class_id) VALUES(?,?,?)",
                           (admission, name, class_id))
                db.commit()
                flash("Student added.", "success")
                return redirect(url_for("students"))
            except sqlite3.IntegrityError:
                flash("That admission number already exists.", "danger")
    return render_template("student_form.html", classes=classes, student=None)


@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_student(student_id):
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id=? AND active=1", (student_id,)).fetchone()
    if not student:
        abort(404)
    classes = db.execute("SELECT * FROM classes ORDER BY name, section").fetchall()
    if request.method == "POST":
        admission = request.form.get("admission_no", "").strip()[:30]
        name = request.form.get("full_name", "").strip()[:100]
        class_id = request.form.get("class_id", type=int)
        try:
            if not admission or not name or not class_id:
                raise ValueError()
            db.execute("UPDATE students SET admission_no=?, full_name=?, class_id=? WHERE id=?",
                       (admission, name, class_id, student_id))
            db.commit()
            flash("Student updated.", "success")
            return redirect(url_for("students"))
        except (sqlite3.IntegrityError, ValueError):
            flash("Please check the fields; the admission number may already be in use.", "danger")
    return render_template("student_form.html", classes=classes, student=student)


@app.post("/students/<int:student_id>/archive")
@login_required
@role_required("admin")
def archive_student(student_id):
    get_db().execute("UPDATE students SET active=0 WHERE id=?", (student_id,))
    get_db().commit()
    flash("Student archived; attendance history was retained.", "info")
    return redirect(url_for("students"))


@app.route("/classes", methods=["GET", "POST"])
@login_required
@role_required("admin")
def classes():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()[:30]
        section = request.form.get("section", "").strip()[:20]
        if not name or not section:
            flash("Class and section are required.", "danger")
        else:
            try:
                db.execute("INSERT INTO classes(name, section) VALUES(?,?)", (name, section))
                db.commit()
                flash("Class added.", "success")
                return redirect(url_for("classes"))
            except sqlite3.IntegrityError:
                flash("That class and section already exist.", "danger")
    rows = db.execute("""SELECT c.*, COUNT(s.id) AS student_count FROM classes c
        LEFT JOIN students s ON s.class_id=c.id AND s.active=1 GROUP BY c.id ORDER BY c.name, c.section""").fetchall()
    teachers = db.execute("SELECT id, full_name FROM users WHERE role='teacher' AND active=1 ORDER BY full_name").fetchall()
    assignments = db.execute("SELECT teacher_id, class_id FROM teacher_classes").fetchall()
    assigned = {(r["teacher_id"], r["class_id"]) for r in assignments}
    if request.args.get("assign") == "1" and request.method == "GET":
        pass
    return render_template("classes.html", classes=rows, teachers=teachers, assigned=assigned)


@app.post("/classes/assign")
@login_required
@role_required("admin")
def assign_class():
    db = get_db()
    teacher_id = request.form.get("teacher_id", type=int)
    class_id = request.form.get("class_id", type=int)
    action = request.form.get("action")
    teacher = db.execute("SELECT id FROM users WHERE id=? AND role='teacher' AND active=1", (teacher_id,)).fetchone()
    cls = db.execute("SELECT id FROM classes WHERE id=?", (class_id,)).fetchone()
    if not teacher or not cls:
        flash("Choose a valid teacher and class.", "danger")
    elif action == "assign":
        db.execute("INSERT OR IGNORE INTO teacher_classes(teacher_id, class_id) VALUES(?,?)", (teacher_id, class_id))
        db.commit()
        flash("Class assigned to teacher.", "success")
    else:
        db.execute("DELETE FROM teacher_classes WHERE teacher_id=? AND class_id=?", (teacher_id, class_id))
        db.commit()
        flash("Class assignment removed.", "info")
    return redirect(url_for("classes"))


@app.route("/users", methods=["GET", "POST"])
@login_required
@role_required("admin")
def users():
    db = get_db()
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()[:50]
        name = request.form.get("full_name", "").strip()[:100]
        password = request.form.get("password", "")
        role = request.form.get("role", "teacher")
        if not re_username(username) or not name or len(password) < 10 or role not in ("admin", "teacher"):
            flash("Use a valid username, name, role, and password of at least 10 characters.", "danger")
        else:
            try:
                db.execute("INSERT INTO users(username, full_name, password_hash, role) VALUES(?,?,?,?)",
                           (username, name, generate_password_hash(password), role))
                db.commit()
                flash("User created. Share credentials securely.", "success")
                return redirect(url_for("users"))
            except sqlite3.IntegrityError:
                flash("That username already exists.", "danger")
    rows = db.execute("SELECT id, username, full_name, role, active, created_at FROM users ORDER BY role, full_name").fetchall()
    return render_template("users.html", users=rows)


def re_username(value):
    return bool(value) and len(value) >= 3 and all(c.isalnum() or c in "._-" for c in value)


@app.post("/users/<int:user_id>/toggle")
@login_required
@role_required("admin")
def toggle_user(user_id):
    if user_id == session["user_id"]:
        flash("You cannot deactivate your own account.", "danger")
        return redirect(url_for("users"))
    db = get_db()
    db.execute("UPDATE users SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?", (user_id,))
    db.commit()
    flash("User status updated.", "info")
    return redirect(url_for("users"))


@app.route("/subjects", methods=["GET", "POST"])
@login_required
@role_required("admin")
def subjects():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()[:80]
        if not name:
            flash("Subject name is required.", "danger")
        else:
            try:
                db.execute("INSERT INTO subjects(name) VALUES(?)", (name,))
                db.commit()
                flash("Subject added.", "success")
                return redirect(url_for("subjects"))
            except sqlite3.IntegrityError:
                flash("That subject already exists.", "danger")
    rows = db.execute("SELECT * FROM subjects ORDER BY name").fetchall()
    return render_template("subjects.html", subjects=rows)


@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    db = get_db()
    user = current_user()
    classes_rows = db.execute("SELECT * FROM classes ORDER BY name, section").fetchall()
    if user["role"] == "teacher":
        allowed = allowed_class_ids(user) or set()
        classes_rows = [c for c in classes_rows if c["id"] in allowed]
    selected_class = request.values.get("class_id", type=int)
    selected_date = valid_date(request.values.get("attendance_date", date.today().isoformat()))
    if not selected_date:
        selected_date = date.today().isoformat()
        flash("Invalid date; showing today.", "warning")
    if selected_class and not can_access_class(user, selected_class):
        abort(403)
    if request.method == "POST":
        if not selected_class or not db.execute("SELECT id FROM classes WHERE id=?", (selected_class,)).fetchone():
            flash("Select a valid class.", "danger")
            return redirect(url_for("attendance"))
        if not can_access_class(user, selected_class):
            abort(403)
        if selected_date > date.today().isoformat():
            flash("Attendance cannot be marked for a future date.", "danger")
            return redirect(url_for("attendance", class_id=selected_class, attendance_date=selected_date))
        students_rows = db.execute("SELECT id FROM students WHERE class_id=? AND active=1", (selected_class,)).fetchall()
        if not students_rows:
            flash("There are no active students in this class.", "warning")
            return redirect(url_for("attendance", class_id=selected_class, attendance_date=selected_date))
        try:
            for student in students_rows:
                status = request.form.get(f"status_{student['id']}")
                if status not in STATUSES:
                    raise ValueError("Every student must have a valid attendance status.")
                db.execute("""INSERT INTO attendance(student_id, attendance_date, status, marked_by)
                    VALUES(?,?,?,?) ON CONFLICT(student_id, attendance_date) DO UPDATE SET
                    status=excluded.status, marked_by=excluded.marked_by, updated_at=CURRENT_TIMESTAMP""",
                    (student["id"], selected_date, status, user["id"]))
            db.commit()
            flash("Attendance saved successfully.", "success")
        except ValueError as exc:
            db.rollback()
            flash(str(exc), "danger")
        return redirect(url_for("attendance", class_id=selected_class, attendance_date=selected_date))
    students_rows = []
    if selected_class and can_access_class(user, selected_class):
        students_rows = db.execute("""SELECT s.*, a.status FROM students s LEFT JOIN attendance a
            ON a.student_id=s.id AND a.attendance_date=? WHERE s.class_id=? AND s.active=1
            ORDER BY s.full_name""", (selected_date, selected_class)).fetchall()
    return render_template("attendance.html", classes=classes_rows, selected_class=selected_class,
                           selected_date=selected_date, students=students_rows, statuses=STATUSES)


@app.route("/reports")
@login_required
def reports():
    db = get_db()
    user = current_user()
    classes_rows = db.execute("SELECT * FROM classes ORDER BY name, section").fetchall()
    if user["role"] == "teacher":
        allowed = allowed_class_ids(user) or set()
        classes_rows = [c for c in classes_rows if c["id"] in allowed]
    class_id = request.args.get("class_id", type=int)
    student_query = request.args.get("q", "").strip()[:100]
    start = valid_date(request.args.get("start", date.today().replace(day=1).isoformat())) or date.today().replace(day=1).isoformat()
    end = valid_date(request.args.get("end", date.today().isoformat())) or date.today().isoformat()
    if start > end:
        start, end = end, start
    if class_id and not can_access_class(user, class_id):
        abort(403)
    where, params = ["s.active=1"], []
    if class_id:
        where.append("s.class_id=?")
        params.append(class_id)
    elif user["role"] == "teacher":
        ids = allowed_class_ids(user) or set()
        if not ids:
            where.append("1=0")
        else:
            where.append("s.class_id IN (" + ",".join("?" for _ in ids) + ")")
            params.extend(sorted(ids))
    if student_query:
        where.append("(s.full_name LIKE ? OR s.admission_no LIKE ?)")
        params.extend([f"%{student_query}%", f"%{student_query}%"])
    rows = db.execute("""SELECT s.id, s.admission_no, s.full_name, c.name AS class_name, c.section,
        COUNT(a.id) AS marked_days,
        SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present_days,
        SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) AS absent_days,
        SUM(CASE WHEN a.status='Leave' THEN 1 ELSE 0 END) AS leave_days,
        ROUND(100.0 * SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.id),0), 1) AS percentage
        FROM students s JOIN classes c ON c.id=s.class_id
        LEFT JOIN attendance a ON a.student_id=s.id AND a.attendance_date BETWEEN ? AND ?
        WHERE """ + " AND ".join(where) +
        " GROUP BY s.id ORDER BY c.name, c.section, s.full_name",
        [start, end] + params).fetchall()
    # Display a student even if no attendance has been marked in the range.
    return render_template("reports.html", rows=rows, classes=classes_rows, class_id=class_id,
                           q=student_query, start=start, end=end)


@app.route("/reports/export.csv")
@login_required
def export_report():
    # Reuse report filters and the same role checks by deriving CSV from the report rows.
    # Reuse the active request's authenticated session and filters.
    db = get_db()
    user = current_user()
    class_id = request.args.get("class_id", type=int)
    q = request.args.get("q", "").strip()[:100]
    start = valid_date(request.args.get("start", date.today().replace(day=1).isoformat())) or date.today().replace(day=1).isoformat()
    end = valid_date(request.args.get("end", date.today().isoformat())) or date.today().isoformat()
    if start > end: start, end = end, start
    if class_id and not can_access_class(user, class_id): abort(403)
    where = ["s.active=1"]
    params = [start, end]
    if class_id:
        where.append("s.class_id=?"); params.append(class_id)
    elif user["role"] == "teacher":
        ids = allowed_class_ids(user) or set()
        if not ids: where.append("1=0")
        else:
            where.append("s.class_id IN (" + ",".join("?" for _ in ids) + ")")
            params.extend(sorted(ids))
    if q:
        where.append("(s.full_name LIKE ? OR s.admission_no LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    rows = db.execute("""SELECT s.admission_no, s.full_name, c.name AS class_name, c.section,
        COUNT(a.id) AS marked_days,
        SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present_days,
        SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) AS absent_days,
        SUM(CASE WHEN a.status='Leave' THEN 1 ELSE 0 END) AS leave_days,
        ROUND(100.0 * SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.id),0),1) AS percentage
        FROM students s JOIN classes c ON c.id=s.class_id
        LEFT JOIN attendance a ON a.student_id=s.id AND a.attendance_date BETWEEN ? AND ?
        WHERE """ + " AND ".join(where) + """
        GROUP BY s.id ORDER BY c.name, c.section, s.full_name""", params).fetchall()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Admission Number", "Student Name", "Class", "Section", "Marked Days", "Present", "Absent", "Leave", "Attendance Percentage"])
    for r in rows:
        writer.writerow([r["admission_no"], r["full_name"], r["class_name"], r["section"], r["marked_days"],
                         r["present_days"] or 0, r["absent_days"] or 0, r["leave_days"] or 0,
                         "" if r["percentage"] is None else r["percentage"]])
    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f"attachment; filename=attendance-{start}-to-{end}.csv"
    return response

@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="You do not have permission to access this page."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="The requested page was not found."), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
