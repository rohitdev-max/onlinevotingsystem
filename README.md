# Rohit Voting System

A Flask-based prototype for college, community, and demonstration elections. It includes voter and administrator pages, candidate/election management, and live aggregate turnout reporting.

> **Prototype only.** This project is not certified or suitable for government, legally binding, or other high-stakes elections. Identity checks are not an authorized Aadhaar integration. Do not use real voter, identity, biometric, or election data.

## Technology

- Python and Flask
- Flask-SQLAlchemy and SQLite for the app's default local database
- MySQL utility scripts and SQL schema under `database/`
- HTML, CSS, JavaScript, and Bootstrap

The application uses SQLite by default. The MySQL initialization utilities are separate from the Flask application's default database configuration.

## Run locally

Requirements: Python 3.8 or newer and `pip`.

Clone the repository and enter its directory:

```bash
git clone <repository-url>
cd <repository-directory>
```

Create and activate a virtual environment.

**Windows (PowerShell):**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies and create a local environment file:

```bash
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env`, then replace the placeholder `SECRET_KEY` with a random value. The example's MySQL settings are only used by the MySQL utility scripts.

Start the development server:

```bash
python app.py
```

Open <http://127.0.0.1:5000>. The Flask app creates its default SQLite database (`rohit_voting.db`) locally. The database, environment files, uploaded files, and cookie files are excluded from Git.

### Admin account setup

The Flask app does not create an administrator account automatically. The repository's legacy demo initialization scripts include the well-known `admin` / `admin123` credentials. They are for disposable local testing only; never expose the account or use it with real data. Review the script and target database before running it. A production-safe administrator provisioning flow is not included.

## Database utilities

`test_db_connection.py` and `database/init_db.py` are MySQL utilities and require the `DATABASE_*` values in `.env`. They do not change the Flask app's default SQLite configuration.

**Warning:** `database/schema.sql` drops existing tables before recreating them. Only use the MySQL initializer with a disposable development database whose contents may be deleted. Do not run it against a database containing data you need.

## Tests

Run the unit tests with:

```bash
python -m unittest discover -s tests -v
```

## Live turnout

The dashboards poll authenticated Flask endpoints for aggregate election turnout. Vote totals are derived from committed vote rows. The interface reports aggregate counts; it is a prototype and does not provide independently audited or election-grade guarantees.

## Security and privacy

- Keep `.env`, database files, cookie files, uploads, and real voter data out of Git.
- Never commit credentials, identity documents, face images, or production data.
- Use a unique secret key and secure production configuration for any non-local deployment.
- The default development configuration enables debug mode and disables CSRF protection; it is not suitable for deployment.
- This software has not been independently security-audited or certified for elections.

If credentials or personal data have ever been committed or pushed, removing them in a later commit is not enough: rotate the credentials and follow GitHub's guidance for sensitive data in repository history.

## License

No license is currently included. Unless the repository owner adds one, GitHub users do not receive permission to reuse, modify, or distribute this project.
