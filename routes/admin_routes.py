from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash
import sqlite3
from datetime import date, datetime, time
from io import StringIO, BytesIO
import csv
from utils.db_utils import generate_doctor_id, generate_patient_id, generate_lab_assistant_id, log_activity

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin_dashboard')
def admin_dashboard():
    if 'username' in session and session['role'] == 'admin':
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
            
            with sqlite3.connect('databases/activity_logs.db') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT action, timestamp 
                    FROM activity_logs 
                    WHERE username = ? 
                    AND action NOT LIKE '%Logged in%' 
                    AND action NOT LIKE '%Logged out%' 
                    ORDER BY timestamp DESC 
                    LIMIT 5
                """, (session['username'],))
                activities = [{'action': row[0], 'timestamp': row[1]} for row in cursor.fetchall()]
            
            return render_template('admin_dashboard.html',
                                  doctor_count=doctor_count,
                                  patient_count=patient_count,
                                  lab_assistant_count=lab_assistant_count,
                                  activities=activities)
        except sqlite3.Error as e:
            flash(f'Database error: {str(e)}', 'error')
            return render_template('admin_dashboard.html',
                                  doctor_count=0,
                                  patient_count=0,
                                  lab_assistant_count=0,
                                  activities=[])
    return redirect(url_for('auth.login'))

@admin_bp.route('/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    if 'username' in session and session['role'] == 'admin':
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            phone = request.form['phone']
            blood_group = request.form['blood_group']
            specialization = request.form['specialization']
            date_of_birth = request.form['date_of_birth']
            medical_registration_number = request.form['medical_registration_number']
            gender = request.form['gender']
            address = request.form['address']
            emergency_contact = request.form['emergency_contact']
            department = request.form['department']
            password = request.form['password']

            doctor_id = generate_doctor_id()

            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'error')
                return render_template('add_doctor.html', error='Password too short')
            if len(medical_registration_number) < 5:
                flash('Medical registration number must be at least 5 characters.', 'error')
                return render_template('add_doctor.html', error='Invalid registration number')
            if not email or '@' not in email:
                flash('Please enter a valid email address.', 'error')
                return render_template('add_doctor.html', error='Invalid email')

            try:
                with sqlite3.connect('databases/users.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO users VALUES (?, ?, ?)",
                                 (doctor_id, generate_password_hash(password), 'doctor'))
                    conn.commit()
                
                with sqlite3.connect('databases/doctors.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute('''INSERT INTO doctors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                 (doctor_id, name, email, phone, blood_group, specialization,
                                  date_of_birth, medical_registration_number, gender, address,
                                  emergency_contact, department))
                    conn.commit()
                
                log_activity(session['username'], f"Added doctor: {doctor_id} ({name})")
                flash(f'Doctor added successfully! Doctor ID: {doctor_id}', 'success')
                return render_template('add_doctor.html', doctor_id=doctor_id)
            except sqlite3.IntegrityError:
                flash('Doctor ID or email already exists.', 'error')
                return render_template('add_doctor.html', error='Doctor ID conflict')
            except sqlite3.Error as e:
                flash(f'Database error: {str(e)}', 'error')
                return render_template('add_doctor.html', error='Database error')
        
        return render_template('add_doctor.html')
    return redirect(url_for('auth.login'))

@admin_bp.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if 'username' in session and session['role'] == 'admin':
        if request.method == 'POST':
            password = request.form['password']
            name = request.form['name']
            date_of_birth = request.form['date_of_birth']
            gender = request.form['gender']
            address = request.form.get('address', '')
            contact = request.form['contact']
            emergency_contact = request.form.get('emergency_contact', '')
            insurance_details = request.form.get('insurance_details', '')
            blood_group = request.form.get('blood_group', '')
            allergies = request.form.get('allergies', '')
            medical_history = request.form.get('medical_history', '')
            preferred_doctor = request.form.get('preferred_doctor', '')

            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'error')
                return render_template('add_patient.html', error='Password too short')
            
            if not contact.isdigit() or len(contact) != 10:
                flash('Contact number must be a 10-digit number.', 'error')
                return render_template('add_patient.html', error='Invalid contact number')

            try:
                patient_id = generate_patient_id()

                with sqlite3.connect('databases/users.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT username FROM users WHERE username = ?", (patient_id,))
                    if cursor.fetchone():
                        flash('Patient ID already exists in users.', 'error')
                        return render_template('add_patient.html', error='Patient ID conflict')
                    cursor.execute("INSERT INTO users VALUES (?, ?, ?)",
                                 (patient_id, generate_password_hash(password), 'patient'))
                    conn.commit()
                
                with sqlite3.connect('databases/patients.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute('''INSERT INTO patients 
                                    (patient_id, name, date_of_birth, gender, address, contact, 
                                     emergency_contact, insurance_details, blood_group, allergies, 
                                     medical_history, preferred_doctor)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                 (patient_id, name, date_of_birth, gender, address, contact,
                                  emergency_contact, insurance_details, blood_group, allergies,
                                  medical_history, preferred_doctor))
                    conn.commit()
                
                log_activity(session['username'], f"Added patient: {patient_id} ({name})")
                flash(f'Patient added successfully! Patient ID: {patient_id}', 'success')
                return redirect(url_for('admin.add_patient'))
            except sqlite3.IntegrityError as e:
                flash(f'Error: {str(e)}', 'error')
                return render_template('add_patient.html', error='Patient ID conflict')
            except sqlite3.Error as e:
                flash(f'Database error: {str(e)}', 'error')
                return render_template('add_patient.html', error='Database error')
        
        with sqlite3.connect('databases/doctors.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT doctor_id, name FROM doctors")
            doctors = cursor.fetchall()
        return render_template('add_patient.html', doctors=doctors, today=date.today().isoformat())
    return redirect(url_for('auth.login'))

@admin_bp.route('/add_lab_assistant', methods=['GET', 'POST'])
def add_lab_assistant():
    if 'username' in session and session['role'] == 'admin':
        if request.method == 'POST':
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
            password = request.form['password']

            lab_assistant_id = generate_lab_assistant_id()

            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'error')
                return render_template('add_lab_assistant.html', error='Password too short')
            if len(lab_registration_number) < 5:
                flash('Lab registration number must be at least 5 characters.', 'error')
                return render_template('add_lab_assistant.html', error='Invalid registration number')
            if not email or '@' not in email:
                flash('Please enter a valid email address.', 'error')
                return render_template('add_lab_assistant.html', error='Invalid email')
            if not phone.isdigit() or len(phone) != 10:
                flash('Phone number must be a 10-digit number.', 'error')
                return render_template('add_lab_assistant.html', error='Invalid phone number')

            try:
                with sqlite3.connect('databases/users.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT username FROM users WHERE username = ?", (lab_assistant_id,))
                    if cursor.fetchone():
                        flash('Lab Assistant ID already exists in users.', 'error')
                        return render_template('add_lab_assistant.html', error='Lab Assistant ID conflict')
                    cursor.execute("INSERT INTO users VALUES (?, ?, ?)",
                                 (lab_assistant_id, generate_password_hash(password), 'lab_assistant'))
                    conn.commit()

                with sqlite3.connect('databases/lab_assistants.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute('''INSERT INTO lab_assistants 
                                    (lab_assistant_id, name, email, phone, date_of_birth, gender, 
                                     blood_group, address, emergency_contact, qualification, 
                                     lab_registration_number, lab_department)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                 (lab_assistant_id, name, email, phone, date_of_birth, gender,
                                  blood_group, address, emergency_contact, qualification,
                                  lab_registration_number, lab_department))
                    conn.commit()

                log_activity(session['username'], f"Added lab assistant: {lab_assistant_id} ({name})")
                flash(f'Lab Assistant added successfully! Lab Assistant ID: {lab_assistant_id}', 'success')
                return render_template('add_lab_assistant.html', lab_assistant_id=lab_assistant_id)
            except sqlite3.IntegrityError:
                flash('Lab Assistant ID or email already exists.', 'error')
                return render_template('add_lab_assistant.html', error='Lab Assistant ID conflict')
            except sqlite3.Error as e:
                flash(f'Database error: {str(e)}', 'error')
                return render_template('add_lab_assistant.html', error='Database error')
        
        return render_template('add_lab_assistant.html')
    return redirect(url_for('auth.login'))

@admin_bp.route('/view_doctors', methods=['GET'])
def view_doctors():
    if 'username' in session and session['role'] == 'admin':
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort_by', 'name')
        sort_order = request.args.get('sort_order', 'asc')
        page = int(request.args.get('page', 1))
        per_page = 10

        prev_search = session.get('prev_search', '')
        if search != prev_search:
            page = 1
            session['prev_search'] = search

        valid_sort_columns = ['name', 'specialization', 'department']
        if sort_by not in valid_sort_columns:
            sort_by = 'name'
        sort_order = 'DESC' if sort_order.lower() == 'desc' else 'ASC'

        try:
            with sqlite3.connect('databases/doctors.db') as conn:
                cursor = conn.cursor()
                query = f'SELECT * FROM doctors ORDER BY {sort_by} {sort_order}'
                params = []
                if search:
                    query = f'''SELECT * FROM doctors WHERE name LIKE ? OR doctor_id LIKE ? OR specialization LIKE ?
                              ORDER BY {sort_by} {sort_order}'''
                    search_term = f'%{search}%'
                    params = [search_term, search_term, search_term]
                
                cursor.execute(query, params)
                all_doctors = cursor.fetchall()

                total_doctors = len(all_doctors)
                total_pages = (total_doctors + per_page - 1) // per_page
                start = (page - 1) * per_page
                end = start + per_page
                doctors = all_doctors[start:end]

                doctor_list = [
                    {
                        'doctor_id': d[0], 'name': d[1], 'email': d[2], 'phone': d[3],
                        'blood_group': d[4], 'specialization': d[5], 'date_of_birth': d[6],
                        'medical_registration_number': d[7], 'gender': d[8], 'address': d[9],
                        'emergency_contact': d[10], 'department': d[11]
                    } for d in doctors
                ]

            return render_template('view_doctors.html',
                                 doctors=doctor_list,
                                 search=search,
                                 sort_by=sort_by,
                                 sort_order=sort_order,
                                 page=page,
                                 total_pages=total_pages,
                                 per_page=per_page)
        except sqlite3.Error as e:
            flash(f'Database error: {str(e)}', 'error')
            return render_template('view_doctors.html', doctors=[])
    return redirect(url_for('auth.login'))

@admin_bp.route('/delete_doctor/<doctor_id>', methods=['POST'])
def delete_doctor(doctor_id):
    if 'username' in session and session['role'] == 'admin':
        try:
            with sqlite3.connect('databases/doctors.db') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM doctors WHERE doctor_id = ?", (doctor_id,))
                doctor_name = cursor.fetchone()
                if not doctor_name:
                    flash('Doctor not found.', 'error')
                    return redirect(url_for('admin.view_doctors'))
                doctor_name = doctor_name[0]
                cursor.execute("DELETE FROM doctors WHERE doctor_id = ?", (doctor_id,))
                conn.commit()
            
            with sqlite3.connect('databases/users.db') as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE username = ?", (doctor_id,))
                conn.commit()
            
            log_activity(session['username'], f"Deleted doctor: {doctor_id} ({doctor_name})")
            flash(f'Doctor {doctor_name} ({doctor_id}) deleted successfully!', 'success')
        except sqlite3.Error as e:
            flash(f'Error deleting doctor: {str(e)}', 'error')
        return redirect(url_for('admin.view_doctors'))
    return redirect(url_for('auth.login'))

@admin_bp.route('/edit_doctor/<doctor_id>', methods=['GET', 'POST'])
def edit_doctor(doctor_id):
    if 'username' in session and session['role'] == 'admin':
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            phone = request.form['phone']
            blood_group = request.form['blood_group']
            specialization = request.form['specialization']
            date_of_birth = request.form['date_of_birth']
            medical_registration_number = request.form['medical_registration_number']
            gender = request.form['gender']
            address = request.form['address']
            emergency_contact = request.form['emergency_contact']
            department = request.form['department']

            if len(medical_registration_number) < 5:
                flash('Medical registration number must be at least 5 characters.', 'error')
                return redirect(url_for('admin.edit_doctor', doctor_id=doctor_id))
            if not email or '@' not in email:
                flash('Please enter a valid email address.', 'error')
                return redirect(url_for('admin.edit_doctor', doctor_id=doctor_id))

            try:
                with sqlite3.connect('databases/doctors.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute('''UPDATE doctors SET name = ?, email = ?, phone = ?,
                                   specialization = ?, date_of_birth = ?, medical_registration_number = ?,
                                   gender = ?, address = ?, emergency_contact = ?, department = ?
                                   WHERE doctor_id = ?''',
                                 (name, email, phone, blood_group, specialization, date_of_birth,
                                  medical_registration_number, gender, address, emergency_contact,
                                  department, doctor_id))
                    conn.commit()
                
                log_activity(session['username'], f"Edited doctor: {doctor_id} ({name})")
                flash(f'Doctor {name} ({doctor_id}) updated successfully!', 'success')
                return redirect(url_for('admin.view_doctors'))
            except sqlite3.Error as e:
                flash(f'Database error: {str(e)}', 'error')
                return redirect(url_for('admin.edit_doctor', doctor_id=doctor_id))
        
        try:
            with sqlite3.connect('databases/doctors.db') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM doctors WHERE doctor_id = ?", (doctor_id,))
                doctor = cursor.fetchone()
                if not doctor:
                    flash('Doctor not found.', 'error')
                    return redirect(url_for('admin.view_doctors'))
                
                doctor_data = {
                    'doctor_id': doctor[0], 'name': doctor[1], 'email': doctor[2], 'phone': doctor[3],
                    'blood_group': doctor[4], 'specialization': doctor[5], 'date_of_birth': doctor[6],
                    'medical_registration_number': doctor[7], 'gender': doctor[8], 'address': doctor[9],
                    'emergency_contact': doctor[10], 'department': doctor[11]
                }
            return render_template('edit_doctor.html', doctor=doctor_data)
        except sqlite3.Error as e:
            flash(f'Database error: {str(e)}', 'error')
            return redirect(url_for('admin.view_doctors'))
    return redirect(url_for('auth.login'))

@admin_bp.route('/export_doctors')
def export_doctors():
    if 'username' not in session or session['role'] != 'admin':
        flash('Please log in as admin to export doctors.', 'error')
        return redirect(url_for('auth.login'))

    try:
        with sqlite3.connect('databases/doctors.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM doctors")
            doctors = cursor.fetchall()
        
        if not doctors:
            flash('No doctors found to export.', 'error')
            return redirect(url_for('admin.view_doctors'))

        output = StringIO()
        writer = csv.writer(output, lineterminator='\n')
        writer.writerow(['Doctor ID', 'Name', 'Email', 'Phone', 'Blood Group', 'Specialization',
                        'Date of Birth', 'Medical Registration Number', 'Gender', 'Address',
                        'Emergency Contact', 'Department'])
        for doctor in doctors:
            writer.writerow(doctor)
        
        output.seek(0)
        bytes_output = BytesIO(output.getvalue().encode('utf-8'))
        
        return send_file(
            bytes_output,
            mimetype='text/csv',
            as_attachment=True,
            download_name='doctors_export.csv'
        )
    except sqlite3.Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('admin.view_doctors'))
    except Exception as e:
        flash(f'Error exporting doctors: {str(e)}', 'error')
        return redirect(url_for('admin.view_doctors'))

@admin_bp.route('/view_patients', methods=['GET'])
def view_patients():
    if 'username' in session and session['role'] == 'admin':
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort_by', 'name')
        sort_order = request.args.get('sort_order', 'asc')
        page = int(request.args.get('page', 1))
        per_page = 10

        prev_search = session.get('prev_search', '')
        if search != prev_search:
            page = 1
            session['prev_search'] = search

        valid_sort_columns = ['name', 'patient_id']
        if sort_by not in valid_sort_columns:
            sort_by = 'name'
        sort_order = 'DESC' if sort_order.lower() == 'desc' else 'ASC'

        try:
            # Fetch patients
            with sqlite3.connect('databases/patients.db') as conn:
                cursor = conn.cursor()
                query = f'SELECT patient_id, name, date_of_birth, gender, contact, preferred_doctor FROM patients ORDER BY {sort_by} {sort_order}'
                params = []
                if search:
                    query = f'SELECT patient_id, name, date_of_birth, gender, contact, preferred_doctor FROM patients WHERE name LIKE ? OR patient_id LIKE ? ORDER BY {sort_by} {sort_order}'
                    search_term = f'%{search}%'
                    params = [search_term, search_term]
                
                cursor.execute(query, params)
                all_patients = cursor.fetchall()

                total_patients = len(all_patients)
                total_pages = (total_patients + per_page - 1) // per_page
                start = (page - 1) * per_page
                end = start + per_page
                patients = all_patients[start:end]

            # Fetch doctor names for each patient
            patient_list = []
            with sqlite3.connect('databases/doctors.db') as conn:
                cursor = conn.cursor()
                for p in patients:
                    patient_id, name, date_of_birth, gender, contact, preferred_doctor = p
                    
                    # Fetch the doctor's name if preferred_doctor exists
                    doctor_name = None
                    if preferred_doctor:
                        cursor.execute("SELECT name FROM doctors WHERE doctor_id = ?", (preferred_doctor,))
                        doctor = cursor.fetchone()
                        doctor_name = doctor[0] if doctor else None

                    patient_list.append({
                        'patient_id': patient_id,
                        'name': name,
                        'date_of_birth': date_of_birth,
                        'gender': gender,
                        'contact': contact,
                        'doctor_name': doctor_name  # Add doctor_name to the dictionary
                    })

            return render_template('view_patients.html',
                                  patients=patient_list,
                                  search=search,
                                  sort_by=sort_by,
                                  sort_order=sort_order,
                                  page=page,
                                  total_pages=total_pages,
                                  per_page=per_page)
        except sqlite3.Error as e:
            flash(f'Database error: {str(e)}', 'error')
            return render_template('view_patients.html', patients=[])
    return redirect(url_for('auth.login'))

@admin_bp.route('/view_lab_assistants', methods=['GET'])
def view_lab_assistants():
    if 'username' in session and session['role'] == 'admin':
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort_by', 'name')
        sort_order = request.args.get('sort_order', 'asc')
        page = int(request.args.get('page', 1))
        per_page = 10

        prev_search = session.get('prev_search', '')
        if search != prev_search:
            page = 1
            session['prev_search'] = search

        valid_sort_columns = ['name', 'lab_department']
        if sort_by not in valid_sort_columns:
            sort_by = 'name'
        sort_order = 'DESC' if sort_order.lower() == 'desc' else 'ASC'

        try:
            with sqlite3.connect('databases/lab_assistants.db') as conn:
                cursor = conn.cursor()
                query = f'SELECT * FROM lab_assistants ORDER BY {sort_by} {sort_order}'
                params = []
                if search:
                    query = f'''SELECT * FROM lab_assistants WHERE name LIKE ? OR lab_assistant_id LIKE ? OR lab_department LIKE ?
                              ORDER BY {sort_by} {sort_order}'''
                    search_term = f'%{search}%'
                    params = [search_term, search_term, search_term]
                
                cursor.execute(query, params)
                all_lab_assistants = cursor.fetchall()

                total_lab_assistants = len(all_lab_assistants)
                total_pages = (total_lab_assistants + per_page - 1) // per_page
                start = (page - 1) * per_page
                end = start + per_page
                lab_assistants = all_lab_assistants[start:end]

                lab_assistant_list = [
                    {
                        'lab_assistant_id': la[0], 'name': la[1], 'email': la[2], 'phone': la[3],
                        'date_of_birth': la[4], 'gender': la[5], 'blood_group': la[6],
                        'address': la[7], 'emergency_contact': la[8], 'qualification': la[9],
                        'lab_registration_number': la[10], 'lab_department': la[11]
                    } for la in lab_assistants
                ]

            return render_template('view_lab_assistants.html',
                                 lab_assistants=lab_assistant_list,
                                 search=search,
                                 sort_by=sort_by,
                                 sort_order=sort_order,
                                 page=page,
                                 total_pages=total_pages,
                                 per_page=per_page)
        except sqlite3.Error as e:
            flash(f'Database error: {str(e)}', 'error')
            return render_template('view_lab_assistants.html', lab_assistants=[])
    return redirect(url_for('auth.login'))

@admin_bp.route('/delete_lab_assistant/<lab_assistant_id>', methods=['POST'])
def delete_lab_assistant(lab_assistant_id):
    if 'username' in session and session['role'] == 'admin':
        try:
            with sqlite3.connect('databases/lab_assistants.db') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM lab_assistants WHERE lab_assistant_id = ?", (lab_assistant_id,))
                lab_assistant_name = cursor.fetchone()
                if not lab_assistant_name:
                    flash('Lab Assistant not found.', 'error')
                    return redirect(url_for('admin.view_lab_assistants'))
                lab_assistant_name = lab_assistant_name[0]
                cursor.execute("DELETE FROM lab_assistants WHERE lab_assistant_id = ?", (lab_assistant_id,))
                conn.commit()
            
            with sqlite3.connect('databases/users.db') as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE username = ?", (lab_assistant_id,))
                conn.commit()
            
            log_activity(session['username'], f"Deleted lab assistant: {lab_assistant_id} ({lab_assistant_name})")
            flash(f'Lab Assistant {lab_assistant_name} ({lab_assistant_id}) deleted successfully!', 'success')
        except sqlite3.Error as e:
            flash(f'Error deleting lab assistant: {str(e)}', 'error')
        return redirect(url_for('admin.view_lab_assistants'))
    return redirect(url_for('auth.login'))

@admin_bp.route('/edit_lab_assistant/<lab_assistant_id>', methods=['GET', 'POST'])
def edit_lab_assistant(lab_assistant_id):
    if 'username' in session and session['role'] == 'admin':
        if request.method == 'POST':
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

            if len(lab_registration_number) < 5:
                flash('Lab registration number must be at least 5 characters.', 'error')
                return redirect(url_for('admin.edit_lab_assistant', lab_assistant_id=lab_assistant_id))
            if not email or '@' not in email:
                flash('Please enter a valid email address.', 'error')
                return redirect(url_for('admin.edit_lab_assistant', lab_assistant_id=lab_assistant_id))
            if not phone.isdigit() or len(phone) != 10:
                flash('Phone number must be a 10-digit number.', 'error')
                return redirect(url_for('admin.edit_lab_assistant', lab_assistant_id=lab_assistant_id))

            try:
                with sqlite3.connect('databases/lab_assistants.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute('''UPDATE lab_assistants SET name = ?, email = ?, phone = ?,
                                   date_of_birth = ?, gender = ?, blood_group = ?, address = ?,
                                   emergency_contact = ?, qualification = ?, lab_registration_number = ?,
                                   lab_department = ? WHERE lab_assistant_id = ?''',
                                 (name, email, phone, date_of_birth, gender, blood_group,
                                  address, emergency_contact, qualification, lab_registration_number,
                                  lab_department, lab_assistant_id))
                    conn.commit()
                
                log_activity(session['username'], f"Edited lab assistant: {lab_assistant_id} ({name})")
                flash(f'Lab Assistant {name} ({lab_assistant_id}) updated successfully!', 'success')
                return redirect(url_for('admin.view_lab_assistants'))
            except sqlite3.Error as e:
                flash(f'Database error: {str(e)}', 'error')
                return redirect(url_for('admin.edit_lab_assistant', lab_assistant_id=lab_assistant_id))
        
        try:
            with sqlite3.connect('databases/lab_assistants.db') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM lab_assistants WHERE lab_assistant_id = ?", (lab_assistant_id,))
                lab_assistant = cursor.fetchone()
                if not lab_assistant:
                    flash('Lab Assistant not found.', 'error')
                    return redirect(url_for('admin.view_lab_assistants'))
                
                lab_assistant_data = {
                    'lab_assistant_id': lab_assistant[0], 'name': lab_assistant[1], 'email': lab_assistant[2],
                    'phone': lab_assistant[3], 'date_of_birth': lab_assistant[4], 'gender': lab_assistant[5],
                    'blood_group': lab_assistant[6], 'address': lab_assistant[7], 'emergency_contact': lab_assistant[8],
                    'qualification': lab_assistant[9], 'lab_registration_number': lab_assistant[10],
                    'lab_department': lab_assistant[11]
                }
            return render_template('edit_lab_assistant.html', lab_assistant=lab_assistant_data)
        except sqlite3.Error as e:
            flash(f'Database error: {str(e)}', 'error')
            return redirect(url_for('admin.view_lab_assistants'))
    return redirect(url_for('auth.login'))

@admin_bp.route('/export_lab_assistants')
def export_lab_assistants():
    if 'username' not in session or session['role'] != 'admin':
        flash('Please log in as admin to export lab assistants.', 'error')
        return redirect(url_for('auth.login'))

    try:
        with sqlite3.connect('databases/lab_assistants.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM lab_assistants")
            lab_assistants = cursor.fetchall()
        
        if not lab_assistants:
            flash('No lab assistants found to export.', 'error')
            return redirect(url_for('admin.view_lab_assistants'))

        output = StringIO()
        writer = csv.writer(output, lineterminator='\n')
        writer.writerow(['Lab Assistant ID', 'Name', 'Email', 'Phone', 'Date of Birth', 'Gender',
                        'Blood Group', 'Address', 'Emergency Contact', 'Qualification',
                        'Lab Registration Number', 'Lab Department'])
        for lab_assistant in lab_assistants:
            writer.writerow(lab_assistant)
        
        output.seek(0)
        bytes_output = BytesIO(output.getvalue().encode('utf-8'))
        
        return send_file(
            bytes_output,
            mimetype='text/csv',
            as_attachment=True,
            download_name='lab_assistants_export.csv'
        )
    except sqlite3.Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('admin.view_lab_assistants'))
    except Exception as e:
        flash(f'Error exporting lab assistants: {str(e)}', 'error')
        return redirect(url_for('admin.view_lab_assistants'))