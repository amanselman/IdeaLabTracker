# IDEALab Borrowing Demo v0.5

This is a small unpolished demo web app to request and track borrowing of components in IDEALab.

Quick steps to run locally (Windows / Bash):

1. Create a Python virtual environment (recommended):

```bash
python -m venv .venv
source .venv/Scripts/activate   # on Windows PowerShell use: .venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Initialize the database and seed sample data:

```bash
python init_db.py
```

This creates two demo user accounts:

- **student1** / **student** (borrower)
- **admin** / **admin** (admin with inventory rights)

4. Run the app:

4. Run the app:

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser. Log in using one of the demo credentials; the "Admin" link will appear for the admin user.

Notes and next steps:
- This is intentionally minimal: it uses SQLite and a small HTML UI.
- To make this production-ready: add authentication, input validation, better CSS, and persistent migrations.
- You can extend the DB to include student IDs and export logs.

Running the automated tests:

```bash
python -m pytest -q
```

The suite logs in as both a student and admin, exercises borrowing/returning, and verifies the admin inventory actions.
