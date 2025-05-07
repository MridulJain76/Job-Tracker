from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
import sqlite3

bp = Blueprint('jobs', __name__)

@bp.route('/')
@login_required
def dashboard():
    conn = sqlite3.connect('database.db')
    jobs = conn.execute('SELECT * FROM jobs WHERE user_id = ?', (current_user.id,)).fetchall()
    conn.close()
    jobs_list = []
    for job in jobs:
        jobs_list.append({
            'id': job[0],
            'company': job[2],
            'position': job[3],
            'status': job[4],
            'application_date': job[5],
            'notes': job[6]
        })
    return render_template('dashboard.html', jobs=jobs_list)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_job():
    if request.method == 'POST':
        company = request.form['company']
        position = request.form['position']
        status = request.form['status']
        conn = sqlite3.connect('database.db')
        conn.execute('INSERT INTO jobs (user_id, company, position, status) VALUES (?, ?, ?, ?)',
                     (current_user.id, company, position, status))
        conn.commit()
        conn.close()
        return redirect(url_for('jobs.dashboard'))
    return render_template('add_job.html')

@bp.route('/delete/<int:id>')
@login_required
def delete_job(id):
    conn = sqlite3.connect('database.db')
    conn.execute('DELETE FROM jobs WHERE id = ? AND user_id = ?', (id, current_user.id))
    conn.commit()
    conn.close()
    return redirect(url_for('jobs.dashboard'))
