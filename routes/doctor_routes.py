from flask import Blueprint, render_template, redirect, url_for, session, flash, request, jsonify, send_file
import sqlite3
from datetime import datetime
from io import BytesIO
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db_utils import generate_prescription_id, save_prescription, generate_and_save_pdf, log_activity, get_prescriptions_for_doctor, get_prescription_pdf, get_lab_reports_for_doctor, get_lab_report_pdf, update_doctor_profile, get_doctor_activity_logs

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.route('/doctor_dashboard', methods=['GET', 'POST'])
def doctor_dashboard():
    if 'username' not in session or session['role'] != 'doctor':
        flash('Please log in as a doctor to access this page.', 'error')
        return redirect(url_for('auth.login'))

    try:
        # Fetch doctor details
        with sqlite3.connect('databases/doctors.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM doctors WHERE doctor_id = ?", (session['username'],))
            doctor = cursor.fetchone()
            if not doctor:
                flash('Doctor data not found.', 'error')
                return redirect(url_for('auth.logout'))
            doctor_data = {
                'name': doctor['name'],
                'email': doctor['email'],
                'phone': doctor['phone'],
                'specialization': doctor['specialization'],
                'department': doctor['department'],
                'medical_registration_number': doctor['medical_registration_number']
            }

        # Fetch assigned patients
        with sqlite3.connect('databases/patients.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT patient_id, name, date_of_birth, gender, contact, blood_group FROM patients WHERE preferred_doctor = ?", (session['username'],))
            patients = cursor.fetchall()
            patient_count = len(patients)

        # Fetch prescriptions for the doctor
        prescriptions = get_prescriptions_for_doctor(session['username'])

        # Fetch lab reports for the doctor's patients
        lab_reports = get_lab_reports_for_doctor(session['username'])

        # Fetch activity logs for the doctor
        activity_logs = get_doctor_activity_logs(session['username'])

        # Initialize active section
        active_section = request.form.get('active_section', 'dashboard')

        # Handle prescription form submission
        if request.method == 'POST' and 'submit_prescription' in request.form:
            patient_id = request.form.get('patient_id', '').strip()
            symptoms = request.form.get('symptoms', '').strip()
            diagnosis = request.form.get('diagnosis', '').strip()
            advice = request.form.get('advice', '').strip()
            medicine_name = request.form.get('medicine_name', '').strip()
            dosage = request.form.get('dosage', '').strip()
            frequency = request.form.get('frequency', '').strip()
            duration = request.form.get('duration', '').strip()
            notes = request.form.get('notes', '').strip()
            prescription_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            prescription_id = generate_prescription_id()

            # Validate required fields
            if not all([patient_id, symptoms, diagnosis, medicine_name, dosage, frequency, duration]):
                flash('All required fields must be filled.', 'error')
                return render_template('doctor_dashboard.html', 
                                     doctor_data=doctor_data, 
                                     patients=patients, 
                                     patient_count=patient_count,
                                     prescriptions=prescriptions,
                                     lab_reports=lab_reports,
                                     activity_logs=activity_logs,
                                     active_section='prescription')

            # Fetch patient name
            with sqlite3.connect('databases/patients.db') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM patients WHERE patient_id = ?", (patient_id,))
                patient = cursor.fetchone()
                if not patient:
                    flash('Patient not found.', 'error')
                    return render_template('doctor_dashboard.html', 
                                         doctor_data=doctor_data, 
                                         patients=patients, 
                                         patient_count=patient_count,
                                         prescriptions=prescriptions,
                                         lab_reports=lab_reports,
                                         activity_logs=activity_logs,
                                         active_section='prescription')
                patient_name = patient[0]

            # Prepare prescription data
            prescription_data = {
                'prescription_id': prescription_id,
                'patient_id': patient_id,
                'doctor_id': session['username'],
                'patient_name': patient_name,
                'doctor_name': doctor_data['name'],
                'symptoms': symptoms,
                'diagnosis': diagnosis,
                'advice': advice,
                'medicine_name': medicine_name,
                'dosage': dosage,
                'frequency': frequency,
                'duration': duration,
                'notes': notes,
                'prescription_date': prescription_date
            }

            # Save prescription and PDF in a transaction-like manner
            try:
                save_prescription(prescription_data)
                generate_and_save_pdf(prescription_data)
                log_activity(session['username'], f'Created prescription {prescription_id} for patient {patient_id}')
                flash('Prescription created successfully!', 'success')
            except Exception as e:
                flash(f'Failed to save prescription: {str(e)}', 'error')

            # Stay on the prescription section to show the message
            return render_template('doctor_dashboard.html', 
                                 doctor_data=doctor_data, 
                                 patients=patients, 
                                 patient_count=patient_count,
                                 prescriptions=prescriptions,
                                 lab_reports=lab_reports,
                                 activity_logs=activity_logs,
                                 active_section='prescription')

        # Handle profile update
        if request.method == 'POST' and 'update_profile' in request.form:
            updates = {
                'name': request.form.get('name', '').strip(),
                'email': request.form.get('email', '').strip(),
                'phone': request.form.get('phone', '').strip(),
                'specialization': request.form.get('specialization', '').strip(),
                'department': request.form.get('department', '').strip()
            }
            # Remove empty fields to avoid updating with empty strings
            updates = {k: v for k, v in updates.items() if v}
            
            if not updates:
                flash('No profile changes provided.', 'error')
            else:
                try:
                    if update_doctor_profile(session['username'], updates):
                        log_activity(session['username'], 'Updated profile')
                        flash('Profile updated successfully!', 'success')
                        # Update doctor_data with new values
                        for key, value in updates.items():
                            doctor_data[key] = value
                    else:
                        flash('No changes were made to the profile.', 'info')
                except Exception as e:
                    flash(f'Failed to update profile: {str(e)}', 'error')
            
            # Stay on the profile section to show the message
            return render_template('doctor_dashboard.html', 
                                 doctor_data=doctor_data, 
                                 patients=patients, 
                                 patient_count=patient_count,
                                 prescriptions=prescriptions,
                                 lab_reports=lab_reports,
                                 activity_logs=activity_logs,
                                 active_section='profile')

        # Handle password change
        if request.method == 'POST' and 'change_password' in request.form:
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not all([current_password, new_password, confirm_password]):
                flash('All password fields are required.', 'error')
            elif new_password != confirm_password:
                flash('New password and confirmation do not match.', 'error')
            elif len(new_password) < 8:
                flash('New password must be at least 8 characters long.', 'error')
            else:
                # Verify current password
                with sqlite3.connect('databases/users.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT password FROM users WHERE username = ?", (session['username'],))
                    result = cursor.fetchone()
                    if not result or not check_password_hash(result[0], current_password):
                        flash('Current password is incorrect.', 'error')
                    else:
                        # Update password
                        new_password_hash = generate_password_hash(new_password)
                        cursor.execute("UPDATE users SET password = ? WHERE username = ?", 
                                       (new_password_hash, session['username']))
                        conn.commit()
                        log_activity(session['username'], 'Changed password')
                        flash('Password changed successfully!', 'success')
                        # Update session to reflect new password hash (optional, for security)
                        session['password_hash'] = new_password_hash

            # Stay on the profile section to show the message
            return render_template('doctor_dashboard.html', 
                                 doctor_data=doctor_data, 
                                 patients=patients, 
                                 patient_count=patient_count,
                                 prescriptions=prescriptions,
                                 lab_reports=lab_reports,
                                 activity_logs=activity_logs,
                                 active_section='profile')

        return render_template('doctor_dashboard.html', 
                             doctor_data=doctor_data, 
                             patients=patients, 
                             patient_count=patient_count,
                             prescriptions=prescriptions,
                             lab_reports=lab_reports,
                             activity_logs=activity_logs,
                             active_section=active_section)
    except sqlite3.Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return render_template('doctor_dashboard.html', 
                             doctor_name='Doctor', 
                             patients=[], 
                             patient_count=0,
                             prescriptions=[],
                             lab_reports=[],
                             activity_logs=[],
                             active_section='dashboard')

@doctor_bp.route('/search_patients', methods=['GET'])
def search_patients():
    if 'username' not in session or session['role'] != 'doctor':
        return jsonify({'error': 'Unauthorized'}), 401

    query = request.args.get('query', '').strip()
    if not query:
        return jsonify([])

    try:
        with sqlite3.connect('databases/patients.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT patient_id, name FROM patients WHERE preferred_doctor = ? AND (patient_id LIKE ? OR name LIKE ?)", 
                           (session['username'], f'%{query}%', f'%{query}%'))
            patients = cursor.fetchall()
            return jsonify([{'patient_id': patient['patient_id'], 'name': patient['name']} for patient in patients])
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500

@doctor_bp.route('/view_prescription_pdf/<prescription_id>')
def view_prescription_pdf(prescription_id):
    if 'username' not in session or session['role'] != 'doctor':
        flash('Please log in as a doctor to access this page.', 'error')
        return redirect(url_for('auth.login'))

    try:
        with sqlite3.connect('databases/prescriptions.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT doctor_id FROM prescriptions WHERE prescription_id = ?", (prescription_id,))
            result = cursor.fetchone()
            if not result or result[0] != session['username']:
                flash('Unauthorized access to prescription.', 'error')
                return redirect(url_for('doctor.doctor_dashboard', active_section='view_prescriptions'))

        pdf_data = get_prescription_pdf(prescription_id)
        return send_file(
            BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=False,
            download_name=f'prescription_{prescription_id}.pdf'
        )
    except Exception as e:
        flash(f'Failed to view PDF: {str(e)}', 'error')
        return redirect(url_for('doctor.doctor_dashboard', active_section='view_prescriptions'))

@doctor_bp.route('/download_prescription_pdf/<prescription_id>')
def download_prescription_pdf(prescription_id):
    if 'username' not in session or session['role'] != 'doctor':
        flash('Please log in as a doctor to access this page.', 'error')
        return redirect(url_for('auth.login'))

    try:
        with sqlite3.connect('databases/prescriptions.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT doctor_id FROM prescriptions WHERE prescription_id = ?", (prescription_id,))
            result = cursor.fetchone()
            if not result or result[0] != session['username']:
                flash('Unauthorized access to prescription.', 'error')
                return redirect(url_for('doctor.doctor_dashboard', active_section='view_prescriptions'))

        pdf_data = get_prescription_pdf(prescription_id)
        log_activity(session['username'], f'Downloaded prescription PDF {prescription_id}')
        flash('Prescription PDF downloaded successfully!', 'success')
        return send_file(
            BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'prescription_{prescription_id}.pdf'
        )
    except Exception as e:
        flash(f'Failed to download PDF: {str(e)}', 'error')
        return redirect(url_for('doctor.doctor_dashboard', active_section='view_prescriptions'))

@doctor_bp.route('/view_lab_report_pdf/<int:report_id>')
def view_lab_report_pdf(report_id):
    if 'username' not in session or session['role'] != 'doctor':
        flash('Please log in as a doctor to access this page.', 'error')
        return redirect(url_for('auth.login'))

    try:
        with sqlite3.connect('databases/lab_reports.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT patient_id FROM lab_reports WHERE id = ?", (report_id,))
            result = cursor.fetchone()
            if not result:
                flash('Lab report not found.', 'error')
                return redirect(url_for('doctor.doctor_dashboard', active_section='view_lab_reports'))

            patient_id = result[0]

        with sqlite3.connect('databases/patients.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT preferred_doctor FROM patients WHERE patient_id = ?", (patient_id,))
            result = cursor.fetchone()
            if not result or result[0] != session['username']:
                flash('Unauthorized access to lab report.', 'error')
                return redirect(url_for('doctor.doctor_dashboard', active_section='view_lab_reports'))

        pdf_data = get_lab_report_pdf(report_id)
        return send_file(
            BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=False,
            download_name=f'lab_report_{report_id}.pdf'
        )
    except Exception as e:
        flash(f'Failed to view lab report PDF: {str(e)}', 'error')
        return redirect(url_for('doctor.doctor_dashboard', active_section='view_lab_reports'))

@doctor_bp.route('/download_lab_report_pdf/<int:report_id>')
def download_lab_report_pdf(report_id):
    if 'username' not in session or session['role'] != 'doctor':
        flash('Please log in as a doctor to access this page.', 'error')
        return redirect(url_for('auth.login'))

    try:
        with sqlite3.connect('databases/lab_reports.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT patient_id FROM lab_reports WHERE id = ?", (report_id,))
            result = cursor.fetchone()
            if not result:
                flash('Lab report not found.', 'error')
                return redirect(url_for('doctor.doctor_dashboard', active_section='view_lab_reports'))

            patient_id = result[0]

        with sqlite3.connect('databases/patients.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT preferred_doctor FROM patients WHERE patient_id = ?", (patient_id,))
            result = cursor.fetchone()
            if not result or result[0] != session['username']:
                flash('Unauthorized access to lab report.', 'error')
                return redirect(url_for('doctor.doctor_dashboard', active_section='view_lab_reports'))

        pdf_data = get_lab_report_pdf(report_id)
        log_activity(session['username'], f'Downloaded lab report PDF {report_id}')
        flash('Lab report PDF downloaded successfully!', 'success')
        return send_file(
            BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'lab_report_{report_id}.pdf'
        )
    except Exception as e:
        flash(f'Failed to download lab report PDF: {str(e)}', 'error')
        return redirect(url_for('doctor.doctor_dashboard', active_section='view_lab_reports'))