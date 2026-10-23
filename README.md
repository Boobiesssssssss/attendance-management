# Online Attendance Management System

A responsive Flask + SQLite starter application for Sankar Matriculation School, Sankagiri West, Namakkal District, Tamil Nadu.

## Features

- Separate administrator and teacher roles
- Password hashing with Werkzeug
- Admin user creation/deactivation
- Class and section management, teacher-class assignments, subjects
- Student add/edit/archive and admission-number uniqueness
- Daily attendance (Present / Absent / Leave), with edits for an existing date
- Date-range attendance reports and CSV export
- Attendance percentage calculated as Present / all marked days × 100
- Teacher class access checks and parameterized SQL queries
- Responsive templates and health endpoint

## Demo accounts (local starter only)

- Admin: `admin` / `ChangeMe123!`
- Teacher: `teacher` / `Teacher123!`

**These are public demo credentials. Change or remove them before deployment or any real school use.** The starter seeds demo users when the database is first created. For a public demo, use fictional student records only. Do not use real student data until the school approves the system and security, privacy, backup, and recovery practices have been reviewed.

## Run locally

Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
# Set SECRET_KEY to a unique random value in your shell before real use.
python app.py
```

Open `http://127.0.0.1:5000`. The database file is created automatically. Use `/health` to check app health.

## Deploy to Render

1. Create a GitHub repository and upload the project files (do not upload `.env`, `attendance.db`, or real student information).
2. In Render, create a new **Blueprint** from that repository. Render will read `render.yaml`.
3. Confirm the generated `SECRET_KEY` environment variable. The blueprint mounts a persistent disk at `/var/data` and sets `DATABASE_PATH=/var/data/attendance.db`.
4. Deploy and wait for `/health` to return `{"status":"ok"}`.
5. Open the Render URL and test both roles with fictional sample data.
6. Replace demo credentials and seed data before any public demonstration. A stronger production setup should provide a one-time admin bootstrap flow rather than a known default password.

### Hosting caveats

Render free web services can sleep after inactivity and have ephemeral filesystems. A disk-backed SQLite database requires a paid persistent disk on Render; free hosting generally does not provide the persistent disk configured in `render.yaml`. Therefore this configuration is intended for a Render service with a persistent disk, not a guaranteed zero-cost production deployment. If you must remain on Render's free web service tier, do not treat local SQLite as durable storage: use a separately hosted database with a free tier, or choose a host/storage arrangement that supports persistence. Verify current plan terms before deployment.

SQLite is suitable for a small school project/demo, but a managed PostgreSQL database is preferable for multi-user production usage. Check provider free-tier limits and backup policies.

## Security checklist before real use

- Set a long, random `SECRET_KEY` and `COOKIE_SECURE=1` behind HTTPS.
- Remove/replace known demo accounts and all fictional seed data as appropriate.
- Require unique strong passwords and have a safe password reset process.
- Review access rules, especially teacher-to-class assignments.
- Add CSRF protection to all state-changing forms before production.
- Add rate limiting / lockout protections to login.
- Configure automated database backups and test a restore.
- Restrict who can download reports and who can create/deactivate accounts.
- Use HTTPS only; do not commit secrets or real student data to Git.
- Obtain school authorization and follow applicable student-data privacy requirements.

## Database schema

Tables are initialized by `init_db()` in `app.py`:
- `users`: admin/teacher accounts
- `classes`: class and section
- `students`: admission number, name, class, active/archive status
- `subjects`: subject list
- `teacher_classes`: teacher-to-class permissions
- `attendance`: one row per student/date, status, marker and timestamp

## Backups and migration

For SQLite, stop writes before copying the database, or use SQLite's online backup API. Keep encrypted backups in a separate approved location and periodically test restoring one. To migrate to another host, copy source code, configure environment variables, provision persistent storage, and move the database with a verified backup. For PostgreSQL migration, schema and SQL statements must be adapted and tested; this project is SQLite-specific.

## Tests

Run:

```bash
pip install pytest
pytest
```

Tests use an isolated temporary SQLite database.
