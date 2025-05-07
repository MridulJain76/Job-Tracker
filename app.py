from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
import sqlite3
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')

# Get database path from environment variable or use default
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'database.db')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def get_db_connection():
    return sqlite3.connect(DATABASE_PATH)

# Initialize the database
def init_db():
    # Only remove database in development
    if os.environ.get('FLASK_ENV') == 'development' and os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)
        
    conn = get_db_connection()
    c = conn.cursor()

    # Create users table
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create jobs table with additional fields
    c.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        company TEXT NOT NULL,
        position TEXT NOT NULL,
        status TEXT NOT NULL,
        application_date DATE NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized with tables.")

# Function to insert sample data (for testing)
def insert_sample_data():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()

    # Insert sample user
    c.execute('''
    INSERT INTO users (username, email, password)
    VALUES ('testuser', 'testuser@example.com', 'password123')
    ''')

    # Insert sample job applications
    c.execute('''
    INSERT INTO jobs (user_id, company, position, status, application_date, notes)
    VALUES 
        (1, 'Company A', 'Software Developer', 'Applied', '2024-03-01', 'Applied through LinkedIn'),
        (1, 'Company B', 'Data Analyst', 'Interviewed', '2024-03-05', 'Technical interview scheduled'),
        (1, 'Company C', 'Frontend Developer', 'Offered', '2024-03-10', 'Salary negotiation in progress'),
        (1, 'Company D', 'Backend Developer', 'Rejected', '2024-03-15', 'Position filled internally')
    ''')

    conn.commit()
    conn.close()
    print("Sample data inserted into the database.")

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(id=user[0], username=user[1], email=user[2])
    return None

class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('login.html')
        
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user[3], password):  # user[3] is the hashed password
            user_obj = User(id=user[0], username=user[1], email=user[2])
            login_user(user_obj)
            flash('Successfully logged in!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not username or not email or not password:
            flash('Please fill in all fields', 'error')
            return render_template('register.html')
        
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        
        # Check if username already exists
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        if c.fetchone():
            flash('Username already exists', 'error')
            conn.close()
            return render_template('register.html')
        
        # Check if email already exists
        c.execute('SELECT * FROM users WHERE email = ?', (email,))
        if c.fetchone():
            flash('Email already registered', 'error')
            conn.close()
            return render_template('register.html')
        
        # Hash the password before storing
        hashed_password = generate_password_hash(password)
        
        c.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                 (username, email, hashed_password))
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT id, company, position, status, application_date, notes, created_at, updated_at 
        FROM jobs 
        WHERE user_id = ? 
        ORDER BY application_date DESC
    ''', (current_user.id,))
    jobs = c.fetchall()
    conn.close()
    
    # Convert jobs to list of dictionaries for easier template access
    jobs_list = []
    for job in jobs:
        jobs_list.append({
            'id': job[0],
            'company': job[1],
            'position': job[2],
            'status': job[3],
            'application_date': job[4],
            'notes': job[5],
            'created_at': job[6],
            'updated_at': job[7]
        })
    
    return render_template('dashboard.html', jobs=jobs_list)

@app.route('/add_job', methods=['POST'])
@login_required
def add_job():
    try:
        company = request.form.get('company')
        position = request.form.get('position')
        status = request.form.get('status')
        application_date = request.form.get('application_date')
        notes = request.form.get('notes')
        
        if not all([company, position, status, application_date]):
            flash('Please fill in all required fields', 'error')
            return redirect(url_for('dashboard'))
        
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO jobs (user_id, company, position, status, application_date, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (current_user.id, company, position, status, application_date, notes))
        conn.commit()
        conn.close()
        
        flash('Job application added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding job application: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/edit_job/<int:job_id>', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    if request.method == 'POST':
        try:
            company = request.form.get('company')
            position = request.form.get('position')
            status = request.form.get('status')
            application_date = request.form.get('application_date')
            notes = request.form.get('notes')
            
            if not all([company, position, status, application_date]):
                flash('Please fill in all required fields', 'error')
                return redirect(url_for('edit_job', job_id=job_id))
            
            c.execute('''
                UPDATE jobs 
                SET company = ?, position = ?, status = ?, application_date = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            ''', (company, position, status, application_date, notes, job_id, current_user.id))
            conn.commit()
            flash('Job application updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Error updating job application: {str(e)}', 'error')
            return redirect(url_for('edit_job', job_id=job_id))
    
    c.execute('SELECT * FROM jobs WHERE id = ? AND user_id = ?', (job_id, current_user.id))
    job = c.fetchone()
    conn.close()
    
    if not job:
        flash('Job not found!', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_job.html', job={
        'id': job[0],
        'company': job[2],
        'position': job[3],
        'status': job[4],
        'application_date': job[5],
        'notes': job[6]
    })

@app.route('/delete_job/<int:job_id>', methods=['POST'])
@login_required
def delete_job(job_id):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM jobs WHERE id = ? AND user_id = ?', (job_id, current_user.id))
        conn.commit()
        conn.close()
        
        flash('Job application deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting job application: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Successfully logged out!', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    # Only initialize database and insert sample data in development
    if os.environ.get('FLASK_ENV') == 'development':
        init_db()
        insert_sample_data()
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
