# Vendilume Local Setup

This guide reproduces the checked in application on a single computer. It assumes Python 3.13, PostgreSQL, Grafana, Git, and a terminal are installed. Windows PowerShell commands are shown; substitute the equivalent shell commands on another operating system. The example role names and passwords are placeholders.

## 1. Prepare Python

```powershell
git clone https://github.com/Sephernie/Vendilume.git
Set-Location Vendilume
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

In `.env`, replace `DJANGO_SECRET_KEY` with a long random value and `POSTGRES_PASSWORD` with the password assigned below. Keep `.env` private. Use `DJANGO_DEBUG=True` only for local development and `DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost` for this setup. Gemini is optional: leave `GEMINI_API_KEY` empty to use deterministic Smart Insights. Keep `GRAFANA_BASE_URL=http://localhost:3000` if Grafana uses its default port.

## 2. Prepare PostgreSQL

Connect as a PostgreSQL administrator, for example with `psql -U postgres`. Substitute strong private passwords:

```sql
CREATE ROLE vendilume_user LOGIN PASSWORD 'replace-with-app-password';
CREATE DATABASE vendilume_db OWNER vendilume_user;
```

Ensure `.env` matches this database, role, host, port, and password. The app role owns the database and creates the schema and view through migrations. Then run:

```powershell
python manage.py migrate
python manage.py setup_roles
python manage.py createsuperuser
python manage.py check
```

Sign in to Django Admin with the superuser and assign the **Administrators** group to that account. You can create ordinary employee accounts through Vendilume's **Manage Users** page afterward.

## 3. Give Grafana read access

After migrations, connect to `vendilume_db` as a PostgreSQL administrator and create a separate reader:

```sql
CREATE ROLE grafana_reader LOGIN PASSWORD 'replace-with-reader-password';
GRANT CONNECT ON DATABASE vendilume_db TO grafana_reader;
GRANT USAGE ON SCHEMA public TO grafana_reader;
GRANT SELECT ON TABLE public.analytics_sales TO grafana_reader;
```

If the account already exists, omit its `CREATE ROLE` statement. Grant access to the view after it exists. Verify with that account:

```sql
SELECT count(*) FROM public.analytics_sales;
```

The reader needs no write access or direct grants on the underlying sales tables.

## 4. Configure Grafana

For a single-computer setup, configure Grafana to listen on `127.0.0.1:3000`. Enable embedding and anonymous access with the **Viewer** organization role in Grafana's configuration, then restart it. The settings belong in these sections of `grafana.ini` (uncomment or override them as appropriate for your installation):

```ini
[server]
http_addr = 127.0.0.1

[security]
allow_embedding = true

[auth.anonymous]
enabled = true
org_role = Viewer
```

Keep this configuration on loopback only; it is not a shared-network security design.

In Grafana, create a **PostgreSQL** datasource using `vendilume_db` and the `grafana_reader` credentials. Choose the host reachable from the Grafana process, usually `localhost:5432` for services on one computer. Run **Save & test**.

Import `grafana/dashboards/vendilume-sales-overview.json`. The exported JSON contains two datasource UIDs from the original installation: one in panel queries and one in dashboard variables. During or after import, point **all seven panels and all seven variables** to the new PostgreSQL datasource. If Grafana does not remap both sets automatically, edit the datasource references in the import JSON to the new UID and import that local copy; do not commit a machine-specific UID. Confirm that the dataset variable populates and panels display data after a dataset is uploaded. Copy the imported dashboard UID from its URL to `GRAFANA_DASHBOARD_UID` in `.env`.

## 5. Start and verify

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/accounts/login/`. Upload the included CSV template or your own valid sales CSV, open its dataset detail, and choose **View Analytics**. The embedded dashboard should show the selected dataset; the filter controls above it should update the panels and insights together. If the iframe is empty, check Grafana's local health endpoint, dashboard UID, datasource mappings in both panels and variables, Viewer permissions, embedding setting, and the reader's view grant.

To check the Python application after setup:

```powershell
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

The Phase 14 checkpoint passed 154 tests. A fresh installation should run its own checks. For an internet or shared-network deployment, add a protected HTTPS reverse proxy and revisit Grafana authentication before exposing either service.
