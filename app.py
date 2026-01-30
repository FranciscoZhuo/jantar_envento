import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)
DB_FILE = 'burgers.db'
ADMIN_PASSWORD = 'admin'


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            burger TEXT NOT NULL,
            received INTEGER NOT NULL DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()


@app.route('/')
def index():
    return render_template('checkin.html')


@app.route('/api/pickup', methods=['POST'])
def api_pickup():
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify(status='not_found')

    conn = get_db()
    row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    if not row:
        conn.close()
        return jsonify(status='not_found')

    name = row['name']
    burger = row['burger']

    if row['received']:
        conn.close()
        return jsonify(status='already', name=name, burger=burger)

    conn.execute('UPDATE users SET received = 1 WHERE id = ?', (row['id'],))
    conn.commit()
    conn.close()
    return jsonify(status='success', name=name, burger=burger)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    key = request.args.get('key', '')
    if key != ADMIN_PASSWORD:
        error = False
        if request.method == 'POST':
            pwd = request.form.get('password', '')
            if pwd == ADMIN_PASSWORD:
                return redirect(url_for('admin', key=ADMIN_PASSWORD))
            error = True
        return render_template('admin_login.html', error=error)

    message = None
    msg_class = 'success'
    conn = get_db()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            new_name = request.form.get('new_name', '').strip()
            new_burger = request.form.get('new_burger', '').strip()
            if new_name and new_burger:
                conn.execute('INSERT INTO users (name, burger) VALUES (?, ?)', (new_name, new_burger))
                conn.commit()
                message = f'Added {new_name} with burger "{new_burger}".'
            else:
                message = 'Name and burger are required.'
                msg_class = 'error'

        elif action == 'edit':
            user_id = request.form.get('user_id')
            edit_name = request.form.get('edit_name', '').strip()
            edit_burger = request.form.get('edit_burger', '').strip()
            if edit_name and edit_burger:
                conn.execute('UPDATE users SET name = ?, burger = ? WHERE id = ?',
                             (edit_name, edit_burger, user_id))
                conn.commit()
                message = f'Updated user #{user_id}.'
            else:
                message = 'Name and burger are required.'
                msg_class = 'error'

        elif action == 'delete':
            user_id = request.form.get('user_id')
            conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
            message = f'Deleted user #{user_id}.'
            msg_class = 'error'

        elif action == 'mark':
            user_id = request.form.get('user_id')
            conn.execute('UPDATE users SET received = 1 WHERE id = ?', (user_id,))
            conn.commit()
            row = conn.execute('SELECT name FROM users WHERE id = ?', (user_id,)).fetchone()
            message = f'Marked {row["name"]} as picked up.'

        elif action == 'reset':
            user_id = request.form.get('user_id')
            conn.execute('UPDATE users SET received = 0 WHERE id = ?', (user_id,))
            conn.commit()
            row = conn.execute('SELECT name FROM users WHERE id = ?', (user_id,)).fetchone()
            message = f'Reset {row["name"]} to waiting.'
            msg_class = 'error'

        elif action == 'reset_all':
            conn.execute('UPDATE users SET received = 0')
            conn.commit()
            message = 'All entries have been reset.'
            msg_class = 'error'

    rows = conn.execute('SELECT * FROM users ORDER BY id').fetchall()
    total = len(rows)
    picked = sum(1 for r in rows if r['received'])
    remaining = total - picked

    conn.close()

    return render_template(
        'admin.html',
        rows=rows, total=total, picked=picked, remaining=remaining,
        message=message, msg_class=msg_class
    )


init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
