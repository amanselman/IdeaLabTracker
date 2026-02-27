import os
import sqlite3
import tempfile

import pytest

import init_db
import app as myapp


def setup_function(fn):
    # ensure fresh DB for each test
    db_path = myapp.DB_PATH
    if os.path.exists(db_path):
        os.remove(db_path)
    init_db.create_db()


def test_borrow_and_return_flow():
    client = myapp.app.test_client()

    # inventory should be accessible
    rv = client.get('/inventory')
    assert rv.status_code == 200
    assert b'Arduino Uno' in rv.data

    # borrow 1 of item id 1
    rv = client.post('/borrow', data={'item_id': '1', 'borrower': 'TestUser', 'qty': '1'}, follow_redirects=True)
    assert rv.status_code == 200

    # check DB for loan record
    conn = sqlite3.connect(myapp.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, item_id, borrower, qty, returned FROM loans WHERE borrower = ?", ('TestUser',))
    row = cur.fetchone()
    assert row is not None
    loan_id, item_id, borrower, qty, returned = row
    assert item_id == 1
    assert borrower == 'TestUser'
    assert qty == 1
    assert returned == 0

    # record return
    rv = client.post(f'/return/{loan_id}', follow_redirects=True)
    assert rv.status_code == 200

    # verify loan marked returned
    cur.execute('SELECT returned FROM loans WHERE id = ?', (loan_id,))
    r = cur.fetchone()
    assert r is not None and r[0] == 1

    conn.close()
