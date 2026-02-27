from flask import Flask, g, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'inventory.db')

app = Flask(__name__)
app.secret_key = 'dev-secret-change-me'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def execute_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    cur.close()


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/inventory')
def inventory():
    items = query_db('SELECT * FROM items')
    return render_template('inventory.html', items=items)


@app.route('/borrow', methods=['GET', 'POST'])
def borrow():
    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        borrower = request.form['borrower'].strip()
        qty = int(request.form['qty'])

        item = query_db('SELECT * FROM items WHERE id = ?', (item_id,), one=True)
        if not item:
            flash('Item not found.', 'danger')
            return redirect(url_for('borrow'))

        if qty <= 0 or qty > item['available']:
            flash('Invalid quantity requested. Check availability.', 'warning')
            return redirect(url_for('borrow'))

        # reduce available
        execute_db('UPDATE items SET available = available - ? WHERE id = ?', (qty, item_id))
        # add loan record
        execute_db('INSERT INTO loans (item_id, borrower, qty, borrow_date, returned) VALUES (?, ?, ?, ?, 0)',
                   (item_id, borrower, qty, datetime.utcnow().isoformat()))
        flash(f'{qty} x {item["name"]} borrowed by {borrower}.', 'success')
        return redirect(url_for('inventory'))

    items = query_db('SELECT * FROM items WHERE available > 0')
    return render_template('borrow.html', items=items)


@app.route('/loans')
def loans():
    # show all loans, active first
    active = query_db('SELECT l.id, l.item_id, l.borrower, l.qty, l.borrow_date, i.name FROM loans l JOIN items i ON l.item_id = i.id WHERE l.returned = 0')
    returned = query_db('SELECT l.id, l.item_id, l.borrower, l.qty, l.borrow_date, l.return_date, i.name FROM loans l JOIN items i ON l.item_id = i.id WHERE l.returned = 1')
    return render_template('loans.html', active=active, returned=returned)


@app.route('/return/<int:loan_id>', methods=['POST'])
def return_loan(loan_id):
    loan = query_db('SELECT * FROM loans WHERE id = ?', (loan_id,), one=True)
    if not loan:
        flash('Loan not found.', 'danger')
        return redirect(url_for('loans'))

    if loan['returned']:
        flash('Loan already returned.', 'info')
        return redirect(url_for('loans'))

    # mark returned and increase available
    execute_db('UPDATE loans SET returned = 1, return_date = ? WHERE id = ?', (datetime.utcnow().isoformat(), loan_id))
    execute_db('UPDATE items SET available = available + ? WHERE id = ?', (loan['qty'], loan['item_id']))
    flash(f"Marked returned: {loan['qty']} x item #{loan['item_id']} from {loan['borrower']}", 'success')
    return redirect(url_for('loans'))


if __name__ == '__main__':
    # quick check: create DB if doesn't exist and run
    if not os.path.exists(DB_PATH):
        print('Database not found. Run `python init_db.py` to create and seed the database.')
    app.run(debug=True)
