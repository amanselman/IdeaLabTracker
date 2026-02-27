"""
Initialize the SQLite database for the IDEALab borrowing demo.
Run: python init_db.py
"""
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'inventory.db')

schema = '''
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    total INTEGER NOT NULL DEFAULT 0,
    available INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    borrower TEXT NOT NULL,
    qty INTEGER NOT NULL,
    borrow_date TEXT,
    returned INTEGER NOT NULL DEFAULT 0,
    return_date TEXT,
    FOREIGN KEY(item_id) REFERENCES items(id)
);
'''

sample_items = [
    ('Arduino Uno', 10),
    ('Raspberry Pi 4', 5),
    ('Breadboard', 20),
    ('Stepper Motor', 6),
    ('Servo Motor', 12),
]


def create_db():
    if os.path.exists(DB_PATH):
        print('Database already exists at', DB_PATH)
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(schema)
    for name, total in sample_items:
        cur.execute('INSERT INTO items (name, total, available) VALUES (?, ?, ?)', (name, total, total))
    conn.commit()
    conn.close()
    print('Database created and seeded at', DB_PATH)


if __name__ == '__main__':
    create_db()
