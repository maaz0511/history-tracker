from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from datetime import datetime
import sqlite3
from io import BytesIO
from werkzeug.security import check_password_hash, generate_password_hash
from utils.db_utils import log_activity

lab_assistant_bp = Blueprint('lab_assistant', __name__)

@lab_assistant_bp.route('/lab_assistant_dashboard', methods=['GET', 'POST'])
def lab_assistant_dashboard():
    if 'username' not in session or session['role'] != 'lab_assistant':
        flash('Please log in as a lab assistant to access this page.', 'error')
        return redirect(url_for('auth.login'))

    username = session['username']

    # Fetch lab assistant data for profile section
    user_data = {}
    try:
        with sqlite3.connect('databases/lab_assistants.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT name, email, phone, date_of_birth, gender, blood_group,
                            address, emergency_contact, qualification, lab_registration_number,
                            lab_department FROM lab_assistants WHERE lab_assistant_id = ?''', (username,))
            user_data_row = cursor.fetchone()
            if user_data_row:
                user_data = {
                    'name': user_data_row[0], 'email': user_data_row[1], 'phone': user_data_row[2],
                    'date_of_birth': user_data_row[3], 'gender': user_data_row[4], 'blood_group': user_data_row[5],
                    'address': user_data_row[6], 'emergency_contact': user_data_row[7], 'qualification': user_data_row[8],
                    'lab_registration_number': user_data_row[9], 'lab_department': user_data_row[10]
                }
            else:
                flash('Lab assistant data not found.', 'error')
                return redirect(url_for('auth.logout'))

            lab_assistant_name = user_data['name']
    except sqlite3.Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('auth.logout'))

    # Fetch activity logs
    activity_logs = []
    try:
        with sqlite3.connect('databases/activity_logs.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT action, timestamp FROM activity_logs WHERE username = ? ORDER BY timestamp DESC LIMIT 10", (username,))
            activity_logs = cursor.fetchall()
    except sqlite3.Error as e:
        flash(f'Database error: {str(e)}', 'error')

    # Handle profile updates
    if request.method == 'POST':
        if 'update_profile' in request.form:
            try:
                name = request.form['name']
                email = request.form['email']
                phone = request.form['phone']
                date_of_birth = request.form['date_of_birth']
                gender = request.form['gender']
                blood_group = request.form['blood_group']
                address = request.form['address']
                emergency_contact = request.form['emergency_contact']
                qualification = request.form['qualification']
                lab_registration_number = request.form['lab_registration_number']
                lab_department = request.form['lab_department']
                with sqlite3.connect('databases/lab_assistants.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute('''UPDATE lab_assistants SET name = ?, email = ?, phone = ?,
                                   date_of_birth = ?, gender = ?, blood_group = ?, address = ?,
                                   emergency_contact = ?, qualification = ?, lab_registration_number = ?,
                                   lab_department = ? WHERE lab_assistant_id = ?''',
                                  (name, email, phone, date_of_birth, gender, blood_group,
                                   address, emergency_contact, qualification, lab_registration_number,
                                   lab_department, username))
                    conn.commit()
                log_activity(username, "Updated profile")
                flash('Profile updated successfully!', 'success')
            except sqlite3.Error as e:
                flash(f'Error updating profile: {str(e)}', 'error')

        elif 'change_password' in request.form:
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            try:
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
            except sqlite3.Error as e:
                flash(f'Database error: {str(e)}', 'error')

        return redirect(url_for('lab_assistant.lab_assistant_dashboard', section='profile'))

    try:
        with sqlite3.connect('databases/lab_reports.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM lab_reports WHERE lab_assistant_id = ?", (username,))
            total_reports = cursor.fetchone()[0]

            cursor.execute("SELECT report_date, report_time FROM lab_reports WHERE lab_assistant_id = ? ORDER BY report_date DESC, report_time DESC LIMIT 1", (username,))
            recent_report = cursor.fetchone()
            recent_activity = f"Last report added on {recent_report[0]} at {recent_report[1]}" if recent_report else None

            report_search = request.args.get('report_search', '').strip()
            report_sort_by = request.args.get('report_sort_by', 'report_date')
            report_sort_order = request.args.get('report_sort_order', 'desc')
            report_page = int(request.args.get('report_page', 1))
            per_page = 10

            valid_report_sort_columns = ['report_date']
            if report_sort_by not in valid_report_sort_columns:
                report_sort_by = 'report_date'
            report_sort_order = 'desc' if report_sort_order.lower() == 'desc' else 'asc'

            query = f'SELECT id, patient_id, patient_name, lab_assistant_name, report_date, report_time FROM lab_reports WHERE lab_assistant_id = ?'
            params = [username]
            if report_search:
                query += ' AND (patient_id LIKE ? OR report_date LIKE ?)'
                search_term = f'%{report_search}%'
                params.extend([search_term, search_term])
            query += f' ORDER BY {report_sort_by} {report_sort_order}'
            query += ' LIMIT ? OFFSET ?'
            offset = (report_page - 1) * per_page
            params.extend([per_page, offset])
            cursor.execute(query, params)
            reports = cursor.fetchall()

            # Calculate total pages
            count_query = "SELECT COUNT(*) FROM lab_reports WHERE lab_assistant_id = ?"
            count_params = [username]
            if report_search:
                count_query += " AND (patient_id LIKE ? OR report_date LIKE ?)"
                count_params.extend([search_term, search_term])
            cursor.execute(count_query, count_params)
            total_reports_count = cursor.fetchone()[0]
            total_report_pages = (total_reports_count + per_page - 1) // per_page

            lab_reports = [
                {
                    'id': r[0],
                    'patient_id': r[1],
                    'patient_name': r[2],
                    'lab_assistant_name': r[3],
                    'report_date': r[4],
                    'report_time': r[5]
                } for r in reports
            ]

        current_date = datetime.now().strftime('%Y-%m-%d')
        current_time = datetime.now().strftime('%H:%M')

        default_section = request.args.get('section', 'dashboard')

        return render_template('lab_assistant_dashboard.html',
                              lab_assistant_name=lab_assistant_name,
                              total_reports=total_reports,
                              recent_activity=recent_activity,
                              lab_reports=lab_reports,
                              report_search=report_search,
                              report_sort_by=report_sort_by,
                              report_sort_order=report_sort_order,
                              report_page=report_page,
                              total_report_pages=total_report_pages,
                              current_date=current_date,
                              current_time=current_time,
                              default_section=default_section,
                              user_data=user_data,
                              activity_logs=activity_logs)

    except sqlite3.Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return render_template('lab_assistant_dashboard.html',
                              lab_assistant_name='Lab Assistant',
                              total_reports=0,
                              recent_activity=None,
                              lab_reports=[],
                              report_search='',
                              report_sort_by='report_date',
                              report_sort_order='desc',
                              report_page=1,
                              total_report_pages=1,
                              current_date=datetime.now().strftime('%Y-%m-%d'),
                              current_time=datetime.now().strftime('%H:%M'),
                              default_section='dashboard',
                              user_data={},
                              activity_logs=[])

@lab_assistant_bp.route('/fetch_patient_name')
def fetch_patient_name():
    patient_id = request.args.get('patient_id', '').strip()
    try:
        with sqlite3.connect('databases/patients.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM patients WHERE patient_id = ?", (patient_id,))
            patient = cursor.fetchone()
            if patient:
                return jsonify({'patient_name': patient[0]})
            return jsonify({'patient_name': None})
    except sqlite3.Error as e:
        return jsonify({'patient_name': None}), 500

@lab_assistant_bp.route('/add_lab_report', methods=['POST'])
def add_lab_report():
    if 'username' not in session or session['role'] != 'lab_assistant':
        flash('Please log in as a lab assistant to access this page.', 'error')
        return redirect(url_for('auth.login'))

    patient_id = request.form['patient_id']
    report_date = request.form['report_date']
    report_time = request.form['report_time']
    report_file = request.files['report_file']

    try:
        with sqlite3.connect('databases/patients.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM patients WHERE patient_id = ?", (patient_id,))
            patient = cursor.fetchone()
            if not patient:
                flash('Invalid patient ID.', 'error')
                return redirect(url_for('lab_assistant.lab_assistant_dashboard', section='add-reports'))
            patient_name = patient[0]
    except sqlite3.Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('lab_assistant.lab_assistant_dashboard', section='add-reports'))

    try:
        with sqlite3.connect('databases/lab_assistants.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM lab_assistants WHERE lab_assistant_id = ?", (session['username'],))
            lab_assistant = cursor.fetchone()
            if not lab_assistant:
                flash('Lab assistant data not found.', 'error')
                return redirect(url_for('auth.logout'))
            lab_assistant_name = lab_assistant[0]
    except sqlite3.Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('lab_assistant.lab_assistant_dashboard', section='add-reports'))

    if not report_file or report_file.filename == '':
        flash('No file uploaded.', 'error')
        return redirect(url_for('lab_assistant.lab_assistant_dashboard', section='add-reports'))
    if not report_file.filename.endswith('.pdf'):
        flash('Only PDF files are allowed.', 'error')
        return redirect(url_for('lab_assistant.lab_assistant_dashboard', section='add-reports'))

    try:
        file_content = report_file.read()
        with sqlite3.connect('databases/lab_reports.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO lab_reports
                            (lab_assistant_id, lab_assistant_name, patient_id, patient_name, report_date, report_time, report_file)
                            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                          (session['username'], lab_assistant_name, patient_id, patient_name, report_date, report_time, file_content))
            conn.commit()
        log_activity(session['username'], f"Added lab report for patient {patient_id}")
        flash('Lab report added successfully!', 'success')
    except sqlite3.Error as e:
        flash(f'Database error: {str(e)}', 'error')

    return redirect(url_for('lab_assistant.lab_assistant_dashboard', section='view-reports'))

@lab_assistant_bp.route('/download_lab_report/<int:report_id>')
def download_lab_report(report_id):
    if 'username' not in session or session['role'] != 'lab_assistant':
        flash('Please log in as a lab assistant to access this page.', 'error')
        return redirect(url_for('auth.login'))

    try:
        with sqlite3.connect('databases/lab_reports.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT report_file, patient_id, report_date FROM lab_reports WHERE id = ? AND lab_assistant_id = ?",
                          (report_id, session['username']))
            report = cursor.fetchone()
            if not report:
                flash('Report not found or you do not have access.', 'error')
                return redirect(url_for('lab_assistant.lab_assistant_dashboard', section='view-reports'))

            file_content, patient_id, report_date = report
            return send_file(
                BytesIO(file_content),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'report_{patient_id}_{report_date}.pdf'
            )
    except sqlite3.Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('lab_assistant.lab_assistant_dashboard', section='view-reports'))

@lab_assistant_bp.route('/view_lab_report/<int:report_id>')
def view_lab_report(report_id):
    if 'username' not in session or session['role'] != 'lab_assistant':
        flash('Please log in as a lab assistant to access this page.', 'error')
        return redirect(url_for('auth.login'))

    try:
        with sqlite3.connect('databases/lab_reports.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT report_file, patient_id, report_date FROM lab_reports WHERE id = ? AND lab_assistant_id = ?",
                          (report_id, session['username']))
            report = cursor.fetchone()
            if not report:
                flash('Report not found or you do not have access.', 'error')
                return redirect(url_for('lab_assistant.lab_assistant_dashboard', section='view-reports'))

            file_content, patient_id, report_date = report
            return send_file(
                BytesIO(file_content),
                mimetype='application/pdf',
                as_attachment=False,
                download_name=f'report_{patient_id}_{report_date}.pdf'
            )
    except sqlite3.Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('lab_assistant.lab_assistant_dashboard', section='view-reports'))