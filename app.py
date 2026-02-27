from flask import Flask, g, render_template, request, redirect, url_for, flash, session, abort
import sqlite3
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

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


@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = query_db('SELECT * FROM users WHERE id = ?', (user_id,), one=True)


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


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.url))
        if not g.user['is_admin']:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = query_db('SELECT * FROM users WHERE username = ?', (username,), one=True)
        if user is None or not check_password_hash(user['password_hash'], password):
            flash('Invalid credentials', 'danger')
        else:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            flash('Logged in successfully', 'success')
            next_page = request.args.get('next') or url_for('index')
            return redirect(next_page)
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('index'))


@app.route('/inventory')
def inventory():
    items = query_db('SELECT * FROM items')
    return render_template('inventory.html', items=items)


@app.route('/borrow', methods=['GET', 'POST'])
@login_required
def borrow():
    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        qty = int(request.form['qty'])
        borrower = g.user['username']

        item = query_db('SELECT * FROM items WHERE id = ?', (item_id,), one=True)
        if not item:
            flash('Item not found.', 'danger')
            return redirect(url_for('borrow'))

        if qty <= 0 or qty > item['available']:
            flash('Invalid quantity requested. Check availability.', 'warning')
            return redirect(url_for('borrow'))

        execute_db('UPDATE items SET available = available - ? WHERE id = ?', (qty, item_id))
        execute_db('INSERT INTO loans (item_id, borrower, qty, borrow_date, returned) VALUES (?, ?, ?, ?, 0)',
                   (item_id, borrower, qty, datetime.utcnow().isoformat()))
        flash(f'{qty} x {item["name"]} borrowed.', 'success')
        return redirect(url_for('inventory'))

    items = query_db('SELECT * FROM items WHERE available > 0')
    return render_template('borrow.html', items=items)


@app.route('/loans')
@login_required
def loans():
    if g.user['is_admin']:
        active = query_db('SELECT l.id, l.item_id, l.borrower, l.qty, l.borrow_date, i.name FROM loans l JOIN items i ON l.item_id = i.id WHERE l.returned = 0')
        returned = query_db('SELECT l.id, l.item_id, l.borrower, l.qty, l.borrow_date, l.return_date, i.name FROM loans l JOIN items i ON l.item_id = i.id WHERE l.returned = 1')
    else:
        active = query_db('SELECT l.id, l.item_id, l.borrower, l.qty, l.borrow_date, i.name FROM loans l JOIN items i ON l.item_id = i.id WHERE l.returned = 0 AND l.borrower = ?', (g.user['username'],))
        returned = query_db('SELECT l.id, l.item_id, l.borrower, l.qty, l.borrow_date, l.return_date, i.name FROM loans l JOIN items i ON l.item_id = i.id WHERE l.returned = 1 AND l.borrower = ?', (g.user['username'],))
    return render_template('loans.html', active=active, returned=returned)


@app.route('/return/<int:loan_id>', methods=['POST'])
@login_required
def return_loan(loan_id):
    loan = query_db('SELECT * FROM loans WHERE id = ?', (loan_id,), one=True)
    if not loan:
        flash('Loan not found.', 'danger')
        return redirect(url_for('loans'))

    if loan['returned']:
        flash('Loan already returned.', 'info')
        return redirect(url_for('loans'))

    # only borrower or admin can return
    if not g.user['is_admin'] and loan['borrower'] != g.user['username']:
        flash('Not authorized to return this loan.', 'danger')
        return redirect(url_for('loans'))

    execute_db('UPDATE loans SET returned = 1, return_date = ? WHERE id = ?', (datetime.utcnow().isoformat(), loan_id))
    execute_db('UPDATE items SET available = available + ? WHERE id = ?', (loan['qty'], loan['item_id']))
    flash('Return recorded.', 'success')
    return redirect(url_for('loans'))


# admin inventory management
@app.route('/admin/inventory')
@admin_required
def admin_inventory():
    items = query_db('SELECT * FROM items')
    return render_template('admin_inventory.html', items=items)

@app.route('/admin/add_item', methods=['POST'])
@admin_required
def add_item():
    name = request.form['name'].strip()
    try:
        total = int(request.form['total'])
    except ValueError:
        total = -1
    if not name or total < 0:
        flash('Invalid name or total.', 'warning')
    else:
        execute_db('INSERT INTO items (name, total, available) VALUES (?, ?, ?)', (name, total, total))
        flash('Item added.', 'success')
    return redirect(url_for('admin_inventory'))

@app.route('/admin/edit_item/<int:item_id>', methods=['GET', 'POST'])
@admin_required
def edit_item(item_id):
    item = query_db('SELECT * FROM items WHERE id = ?', (item_id,), one=True)
    if not item:
        abort(404)
    if request.method == 'POST':
        name = request.form['name'].strip()
        try:
            total = int(request.form['total'])
            avail = int(request.form['available'])
        except ValueError:
            total = avail = -1
        if not name or total < 0 or avail < 0 or avail > total:
            flash('Invalid values.', 'warning')
        else:
            execute_db('UPDATE items SET name=?, total=?, available=? WHERE id=?', (name, total, avail, item_id))
            flash('Item updated.', 'success')
            return redirect(url_for('admin_inventory'))
    return render_template('edit_item.html', item=item)

@app.route('/admin/delete_item/<int:item_id>', methods=['POST'])
@admin_required
def delete_item(item_id):
    execute_db('DELETE FROM items WHERE id = ?', (item_id,))
    flash('Item deleted.', 'success')
    return redirect(url_for('admin_inventory'))


if __name__ == '__main__':
    # quick check: create DB if doesn't exist and run
    if not os.path.exists(DB_PATH):
        print('Database not found. Run `python init_db.py` to create and seed the database.')
    app.run(debug=True)
