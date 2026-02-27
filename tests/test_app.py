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


def login(client, username, password):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)


def logout(client):
    return client.get('/logout', follow_redirects=True)


def test_borrow_and_return_flow():
    client = myapp.app.test_client()

    # login as student1
    rv = login(client, 'student1', 'student')
    assert rv.status_code == 200
    assert b'Logged in successfully' in rv.data

    # inventory is accessible
    rv = client.get('/inventory')
    assert rv.status_code == 200
    assert b'Arduino Uno' in rv.data

    # borrow 1 of item id 1
    rv = client.post('/borrow', data={'item_id': '1', 'qty': '1'}, follow_redirects=True)
    assert rv.status_code == 200

    # check DB for loan record belonging to student1
    conn = sqlite3.connect(myapp.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, item_id, borrower, qty, returned FROM loans WHERE borrower = ?", ('student1',))
    row = cur.fetchone()
    assert row is not None
    loan_id, item_id, borrower, qty, returned = row
    assert item_id == 1
    assert borrower == 'student1'
    assert qty == 1
    assert returned == 0

    # return the loan
    rv = client.post(f'/return/{loan_id}', follow_redirects=True)
    assert rv.status_code == 200

    cur.execute('SELECT returned FROM loans WHERE id = ?', (loan_id,))
    r = cur.fetchone()
    assert r is not None and r[0] == 1
    conn.close()
    logout(client)


def test_admin_can_manage_inventory():
    client = myapp.app.test_client()
    # login admin
    rv = login(client, 'admin', 'admin')
    assert b'Logged in successfully' in rv.data

    # access admin inventory page
    rv = client.get('/admin/inventory')
    assert rv.status_code == 200
    assert b'Admin Inventory' in rv.data

    # add a new item
    rv = client.post('/admin/add_item', data={'name': 'TestItem', 'total': '3'}, follow_redirects=True)
    assert b'Item added' in rv.data

    # edit the item
    # find its id from db
    conn = sqlite3.connect(myapp.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM items WHERE name = ?", ('TestItem',))
    row = cur.fetchone()
    assert row is not None
    item_id = row[0]
    conn.close()

    rv = client.post(f'/admin/edit_item/{item_id}', data={'name': 'TestItemX', 'total': '5', 'available': '5'}, follow_redirects=True)
    assert b'Item updated' in rv.data

    # delete the item
    rv = client.post(f'/admin/delete_item/{item_id}', follow_redirects=True)
    assert b'Item deleted' in rv.data

    logout(client)
