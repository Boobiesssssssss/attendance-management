# Deployment and Portability Guide

## Local configuration
- Python 3.10+
- Install dependencies with `pip install -r requirements.txt`
- Configure `SECRET_KEY`, `DATABASE_PATH`, and `COOKIE_SECURE` as environment variables.
- Start with `python app.py` for local development or `gunicorn app:app` for deployment.

## Render deployment
The repository contains `render.yaml` for a Blueprint deployment. It expects a persistent disk mounted at `/var/data`. Verify current Render plan restrictions and disk charges: the free web-service tier does not guarantee persistent local SQLite storage. Do not deploy a SQLite database to an ephemeral filesystem and assume it will retain data across restarts.

For a strictly free demo, consider:
1. Render free web service + an independently hosted managed database with a free tier, after adapting the app to that database; or
2. A host that provides persistent storage under its current free plan, after verifying limits; or
3. Use Render with persistent storage if the cost is acceptable.

## Environment variables
- `SECRET_KEY`: unique random secret; never commit it.
- `DATABASE_PATH`: absolute path to persistent SQLite file.
- `COOKIE_SECURE`: set to `1` when served exclusively over HTTPS.

## Portability / migration
1. Export or safely back up the database.
2. Copy source files and pinned dependencies to the target host.
3. Provision a compatible Python runtime and persistent storage.
4. Set environment variables using the destination host's secret manager.
5. Restore the database and verify row counts and foreign-key integrity.
6. Run automated tests, then test login, role restrictions, attendance save/edit, reports, and CSV export.
7. Verify HTTPS, session cookie settings, logs, monitoring, and backups.
8. Update the public URL and document any provider-specific changes.

## Backup guidance
Use SQLite's online backup mechanism or a quiesced copy; do not copy a live database casually during writes. Store backups in a separate approved location, encrypt them where appropriate, restrict access, and regularly test restoration. A backup is only useful if restoration has been verified.

## Production gaps to resolve
- Add CSRF protection to every state-changing form.
- Add login rate limiting and safe password reset/change flows.
- Replace known demo credentials and seed records.
- Confirm privacy/legal requirements with school leadership.
- Establish backup retention, restoration drills, and incident response.
- Consider PostgreSQL for multi-user concurrent production usage.
