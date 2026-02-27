# IDEALab Borrowing Demo

This is a small demo web app to request and track borrowing of components in IDEALab.

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

4. Run the app:

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser.

Notes and next steps:
- This is intentionally minimal: it uses SQLite and a small HTML UI.
- To make this production-ready: add authentication, input validation, better CSS, and persistent migrations.
- You can extend the DB to include student IDs and export logs.
