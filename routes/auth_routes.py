from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
from utils.db_utils import log_activity

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    return render_template('index.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('login.html', error='Missing credentials')

        with sqlite3.connect('databases/users.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, password, role FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user[1], password):
                # Clear any existing flash messages before redirecting
                session.pop('_flashes', None)  # Fix: Clear flash messages on successful login
                session['username'] = user[0]
                session['role'] = user[2]
                log_activity(user[0], "Logged in")
                
                if user[2] == 'admin':
                    return redirect(url_for('admin.admin_dashboard'))
                elif user[2] == 'doctor':
                    return redirect(url_for('doctor.doctor_dashboard'))
                elif user[2] == 'patient':
                    return redirect(url_for('patient_bp.patients_dashboard'))
                elif user[2] == 'lab_assistant':
                    return redirect(url_for('lab_assistant.lab_assistant_dashboard'))
                else:
                    flash('Invalid user role.', 'error')
                    return render_template('login.html', error='Invalid role')
        
        # Updated error message to be generic
        flash('Invalid username or password.', 'error')
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@auth_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    username = session['username']
    role = session['role']
    
    # Ensure only admin can access this route
    if role != 'admin':
        flash('Access denied. Admin only.', 'error')
        return redirect(url_for('auth.login'))

    user_data = {'name': 'Admin User', 'contact': ''}  # Default admin data

    with sqlite3.connect('databases/activity_logs.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT action, timestamp FROM activity_logs WHERE username = ? ORDER BY timestamp DESC LIMIT 10",
                      (username,))
        activity_logs = cursor.fetchall()

    if request.method == 'POST':
        if 'update_profile' in request.form:
            try:
                name = request.form['name']
                contact = request.form['contact']
                user_data['name'] = name
                user_data['contact'] = contact
                log_activity(username, "Updated profile")
                flash('Profile updated successfully!', 'success')
            except Exception as e:
                flash(f'Error updating profile: {str(e)}', 'error')

        elif 'change_password' in request.form:
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            with sqlite3.connect('databases/users.db') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
                stored_password = cursor.fetchone()[0]

                if not check_password_hash(stored_password, current_password):
                    flash('Current password is incorrect', 'error')
                elif new_password != confirm_password:
                    flash('New passwords do not match', 'error')
                elif len(new_password) < 6:
                    flash('New password must be at least 6 characters', 'error')
                else:
                    cursor.execute("UPDATE users SET password = ? WHERE username = ?",
                                  (generate_password_hash(new_password), username))
                    conn.commit()
                    log_activity(username, "Changed password")
                    flash('Password changed successfully!', 'success')

        return redirect(url_for('auth.profile'))

    return render_template('profile.html', username=username, role=role, user_data=user_data, activity_logs=activity_logs)

@auth_bp.route('/logout')
def logout():
    if 'username' in session:
        log_activity(session['username'], "Logged out")
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/stats')
def get_stats():
    try:
        with sqlite3.connect('databases/doctors.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM doctors")
            doctor_count = cursor.fetchone()[0]
        
        with sqlite3.connect('databases/patients.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM patients")
            patient_count = cursor.fetchone()[0]
        
        with sqlite3.connect('databases/lab_assistants.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM lab_assistants")
            lab_assistant_count = cursor.fetchone()[0]
        
        return jsonify({
            'doctors': doctor_count,
            'patients': patient_count,
            'labAssistants': lab_assistant_count,
            'appointments': 0
        })
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500