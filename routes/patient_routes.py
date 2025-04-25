from flask import Blueprint, render_template, send_file, session, redirect, url_for, request, jsonify
from io import BytesIO
import sqlite3
import re
from datetime import datetime
import google.generativeai as genai

patient_bp = Blueprint('patient_bp', __name__)

# Configure Gemini API (replace with your API key)
genai.configure(api_key="AIzaSyBUQRNqrR04Sw9g_dGY25r-9FnFNt8MvIc")
model = genai.GenerativeModel('gemini-1.5-flash')

@patient_bp.route('/patients_dashboard')
def patients_dashboard():
    if 'username' not in session or session.get('role') != 'patient':
        return redirect(url_for('auth.login'))
    
    patient_id = session['username']
    try:
        with sqlite3.connect('databases/prescriptions.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT prescription_id, doctor_name, prescription_date FROM prescriptions WHERE patient_id = ? ORDER BY prescription_date DESC", 
                           (patient_id,))
            prescriptions = cursor.fetchall()

        with sqlite3.connect('databases/lab_reports.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, patient_name, lab_assistant_name, report_date, report_time FROM lab_reports WHERE patient_id = ? ORDER BY id ASC",
                           (patient_id,))
            lab_reports = cursor.fetchall()

        with sqlite3.connect('databases/patients.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''SELECT patient_id, name, date_of_birth, gender, address, contact, emergency_contact,
                            insurance_details, blood_group, allergies, medical_history, preferred_doctor
                            FROM patients WHERE patient_id = ?''', (patient_id,))
            user_data = cursor.fetchone()

        with sqlite3.connect('databases/activity_logs.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT action, timestamp FROM activity_logs WHERE username = ? ORDER BY timestamp DESC LIMIT 10",
                           (patient_id,))
            activity_logs = cursor.fetchall()

        # Calculate counts for prescriptions and lab reports
        prescription_count = len(prescriptions)
        lab_report_count = len(lab_reports)

        return render_template('patients_dashboard.html', 
                             prescriptions=prescriptions, 
                             lab_reports=lab_reports,
                             user_data=user_data,
                             activity_logs=activity_logs,
                             prescription_count=prescription_count,
                             lab_report_count=lab_report_count)
    except Exception as e:
        return f"Error: {str(e)}", 500

@patient_bp.route('/prescriptions')
def prescriptions():
    if 'username' not in session or session.get('role') != 'patient':
        return redirect(url_for('auth.login'))
    
    patient_id = session['username']
    try:
        with sqlite3.connect('databases/prescriptions.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT prescription_id, doctor_name, prescription_date FROM prescriptions WHERE patient_id = ? ORDER BY prescription_date DESC", 
                           (patient_id,))
            prescriptions = cursor.fetchall()

        with sqlite3.connect('databases/patients.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''SELECT patient_id, name, date_of_birth, gender, address, contact, emergency_contact,
                            insurance_details, blood_group, allergies, medical_history, preferred_doctor
                            FROM patients WHERE patient_id = ?''', (patient_id,))
            user_data = cursor.fetchone()

        with sqlite3.connect('databases/activity_logs.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT action, timestamp FROM activity_logs WHERE username = ? ORDER BY timestamp DESC LIMIT 10",
                           (patient_id,))
            activity_logs = cursor.fetchall()

        return render_template('patients_dashboard.html', 
                             prescriptions=prescriptions, 
                             lab_reports=[],
                             user_data=user_data,
                             activity_logs=activity_logs)
    except Exception as e:
        return f"Error: {str(e)}", 500

@patient_bp.route('/lab_reports')
def lab_reports():
    if 'username' not in session or session.get('role') != 'patient':
        return redirect(url_for('auth.login'))
    
    patient_id = session['username']
    try:
        with sqlite3.connect('databases/lab_reports.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, patient_name, lab_assistant_name, report_date, report_time FROM lab_reports WHERE patient_id = ? ORDER BY id ASC",
                           (patient_id,))
            lab_reports = cursor.fetchall()

        with sqlite3.connect('databases/patients.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''SELECT patient_id, name, date_of_birth, gender, address, contact, emergency_contact,
                            insurance_details, blood_group, allergies, medical_history, preferred_doctor
                            FROM patients WHERE patient_id = ?''', (patient_id,))
            user_data = cursor.fetchone()

        with sqlite3.connect('databases/activity_logs.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT action, timestamp FROM activity_logs WHERE username = ? ORDER BY timestamp DESC LIMIT 10",
                           (patient_id,))
            activity_logs = cursor.fetchall()

        return render_template('patients_dashboard.html', 
                             prescriptions=[],
                             lab_reports=lab_reports,
                             user_data=user_data,
                             activity_logs=activity_logs)
    except Exception as e:
        return f"Error: {str(e)}", 500

@patient_bp.route('/download_prescription/<prescription_id>')
def download_prescription(prescription_id):
    if 'username' not in session or session.get('role') != 'patient':
        return redirect(url_for('auth.login'))
    
    try:
        with sqlite3.connect('databases/prescriptions_pdf.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pdf_data FROM prescriptions_pdf WHERE prescription_id = ?", (prescription_id,))
            result = cursor.fetchone()
            if not result:
                return f"PDF not found for prescription ID {prescription_id}", 404
            pdf_data = result[0]
        
        view = request.args.get('view', default='false').lower() == 'true'
        
        return send_file(
            BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=not view,
            download_name=f"prescription_{prescription_id}.pdf"
        )
    except Exception as e:
        return f"Error: {str(e)}", 500

@patient_bp.route('/download_lab_report/<report_id>')
def download_lab_report(report_id):
    if 'username' not in session or session.get('role') != 'patient':
        return redirect(url_for('auth.login'))
    
    try:
        with sqlite3.connect('databases/lab_reports.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT report_file FROM lab_reports WHERE id = ?", (report_id,))
            result = cursor.fetchone()
            if not result:
                return f"PDF not found for lab report ID {report_id}", 404
            pdf_data = result[0]
        
        view = request.args.get('view', default='false').lower() == 'true'
        
        return send_file(
            BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=not view,
            download_name=f"lab_report_{report_id}.pdf"
        )
    except Exception as e:
        return f"Error: {str(e)}", 500

@patient_bp.route('/chatbot', methods=['POST'])
def chatbot():
    if 'username' not in session or session.get('role') != 'patient':
        return jsonify({'error': 'Unauthorized'}), 401
    
    patient_id = session['username']
    data = request.get_json()
    query = data.get('query', '').strip()
    option = data.get('option', '')

    # Log the chatbot interaction
    try:
        with sqlite3.connect('databases/activity_logs.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO activity_logs (username, action, timestamp) VALUES (?, ?, ?)",
                           (patient_id, f"Chatbot query: {query or option}", datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
    except Exception as e:
        print(f"Error logging activity: {str(e)}")

    # Language detection: English only
    is_hinglish = False  # Force English responses

    # Convert query to lowercase for searching
    query_for_search = query.lower()

    # Check for general medical queries (e.g., "which medicine should I take")
    is_general_medical = bool(re.search(r'\b(what|which)\b.*\b(medicine|take)\b', query_for_search)) or \
                         bool(re.search(r'\b(headache|fever)\b', query_for_search))

    # Check for definitional queries (e.g., "what is blood group")
    is_definitional = bool(re.search(r'\bwhat is\b', query_for_search))

    # Check for non-medical queries (e.g., "weather", "news")
    is_non_medical = bool(re.search(r'\b(weather|news|today)\b', query_for_search))

    # Handle menu-based options
    if option:
        try:
            if option == 'lab_report':
                with sqlite3.connect('databases/lab_reports.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, lab_assistant_name, report_date FROM lab_reports WHERE patient_id = ? ORDER BY id ASC LIMIT 1",
                                   (patient_id,))
                    report = cursor.fetchone()
                    if report:
                        response = f"Your lab report: ID {report['id']}, Date: {report['report_date']}, Lab Assistant: {report['lab_assistant_name']}. View: <a href='/patient/download_lab_report/{report['id']}?view=true' target='_blank'>Click here</a>"
                    else:
                        response = "No lab reports found."
            
            elif option == 'prescription':
                with sqlite3.connect('databases/prescriptions.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT prescription_id, doctor_name, prescription_date FROM prescriptions WHERE patient_id = ? ORDER BY prescription_date DESC LIMIT 1",
                                   (patient_id,))
                    prescription = cursor.fetchone()
                    if prescription:
                        response = f"Your prescription: ID {prescription['prescription_id']}, Date: {prescription['prescription_date']}, Doctor: {prescription['doctor_name']}. View: <a href='/patient/download_prescription/{prescription['prescription_id']}?view=true' target='_blank'>Click here</a>"
                    else:
                        response = "No prescriptions found."
            
            elif option == 'profile':
                with sqlite3.connect('databases/patients.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT name, date_of_birth, contact FROM patients WHERE patient_id = ?", (patient_id,))
                    profile = cursor.fetchone()
                    if profile:
                        response = f"Your profile: Name: {profile['name']}, DOB: {profile['date_of_birth']}, Contact: {profile['contact']}"
                    else:
                        response = "Profile not found."
            
            elif option == 'help':
                response = "I am Patient History Tracker. I can show your lab reports, prescriptions, profile, medical history, allergies, medicines, total reports, preferred doctor, or blood group. Use the buttons or type a query like 'Show my lab report'."
            
            elif option == 'medical_history':
                with sqlite3.connect('databases/patients.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT medical_history FROM patients WHERE patient_id = ?", (patient_id,))
                    profile = cursor.fetchone()
                    if profile and profile['medical_history']:
                        response = f"Your medical history: {profile['medical_history']}"
                    else:
                        response = "No medical history found."
            
            elif option == 'allergies':
                with sqlite3.connect('databases/patients.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT allergies FROM patients WHERE patient_id = ?", (patient_id,))
                    profile = cursor.fetchone()
                    if profile and profile['allergies']:
                        response = f"Your allergies: {profile['allergies']}"
                    else:
                        response = "No allergies found."
            
            elif option == 'medicine_name':
                with sqlite3.connect('databases/prescriptions.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT medicine_name FROM prescriptions WHERE patient_id = ? ORDER BY prescription_date DESC LIMIT 1",
                                   (patient_id,))
                    prescription = cursor.fetchone()
                    if prescription and prescription['medicine_name']:
                        response = f"Your latest medicine: {prescription['medicine_name']}"
                    else:
                        response = "No medicines found."
            
            elif option == 'total_prescriptions':
                with sqlite3.connect('databases/prescriptions.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM prescriptions WHERE patient_id = ?", (patient_id,))
                    count = cursor.fetchone()[0]
                    response = f"Your total prescriptions: {count}"
            
            elif option == 'total_lab_reports':
                with sqlite3.connect('databases/lab_reports.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM lab_reports WHERE patient_id = ?", (patient_id,))
                    count = cursor.fetchone()[0]
                    response = f"Your total lab reports: {count}"
            
            elif option == 'preferred_doctor':
                with sqlite3.connect('databases/patients.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT preferred_doctor FROM patients WHERE patient_id = ?", (patient_id,))
                    patient = cursor.fetchone()
                    if patient and patient['preferred_doctor']:
                        with sqlite3.connect('databases/doctors.db') as conn2:
                            conn2.row_factory = sqlite3.Row
                            cursor2 = conn2.cursor()
                            cursor2.execute("SELECT name FROM doctors WHERE doctor_id = ?", (patient['preferred_doctor'],))
                            doctor = cursor2.fetchone()
                            if doctor:
                                response = f"Your preferred doctor: {doctor['name']}"
                            else:
                                response = "No record found for your preferred doctor."
                    else:
                        response = "No preferred doctor found."
            
            elif option == 'lab_assistant_name':
                with sqlite3.connect('databases/lab_reports.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT lab_assistant_name FROM lab_reports WHERE patient_id = ? ORDER BY id ASC LIMIT 1",
                                   (patient_id,))
                    report = cursor.fetchone()
                    if report and report['lab_assistant_name']:
                        response = f"Lab assistant for your latest report: {report['lab_assistant_name']}"
                    else:
                        response = "No lab reports or lab assistant found."
            
            elif option == 'appointments':
                response = "Appointments feature is not available yet. Please contact the admin."
            
            elif option == 'emergency_contact':
                with sqlite3.connect('databases/patients.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT emergency_contact FROM patients WHERE patient_id = ?", (patient_id,))
                    profile = cursor.fetchone()
                    if profile and profile['emergency_contact']:
                        response = f"Your emergency contact: {profile['emergency_contact']}"
                    else:
                        response = "No emergency contact found."
            
            elif option == 'insurance_details':
                with sqlite3.connect('databases/patients.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT insurance_details FROM patients WHERE patient_id = ?", (patient_id,))
                    profile = cursor.fetchone()
                    if profile and profile['insurance_details']:
                        response = f"Your insurance details: {profile['insurance_details']}"
                    else:
                        response = "No insurance details found."
            
            elif option == 'activity_logs':
                with sqlite3.connect('databases/activity_logs.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT action, timestamp FROM activity_logs WHERE username = ? ORDER BY timestamp DESC LIMIT 10",
                                   (patient_id,))
                    logs = cursor.fetchall()
                    if logs:
                        response = f"Your recent activity:\n" + "\n".join([f"- {log['action']} at {log['timestamp']}" for log in logs])
                    else:
                        response = "No recent activity found."
            
            elif option == 'blood_group':
                with sqlite3.connect('databases/patients.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT blood_group FROM patients WHERE patient_id = ?", (patient_id,))
                    profile = cursor.fetchone()
                    if profile and profile['blood_group']:
                        response = f"Your blood group: {profile['blood_group']}"
                    else:
                        response = "No blood group found."
            
            else:
                response = "Invalid option."
            
            return jsonify({'response': response})

        except Exception as e:
            return jsonify({'response': f"Error: {str(e)}"}), 500

    # Handle free-text queries
    if query:
        try:
            lower_query = query_for_search  # Use the converted query for searching
            db_result_found = False
            response = ""

            # If it's a non-medical query, respond with a scope message
            if is_non_medical:
                response = "Sorry, I can only answer medical questions!"
                return jsonify({'response': response})

            # If it's a general medical query or definitional query, skip database and use Gemini
            if is_general_medical or is_definitional:
                try:
                    prompt = f"Answer this medical-related question in a detailed and informative way, providing at least 3-4 sentences of explanation: {query}"
                    gemini_response = model.generate_content(prompt)
                    response = gemini_response.text.strip()
                    response = f"Here’s the information: {response}"
                    return jsonify({'response': response})
                except Exception as e:
                    response = "Sorry, I couldn’t find an answer right now. You can ask about your lab report or prescription instead!"
                    return jsonify({'response': response})

            # Database search for specific queries
            if re.search(r'\bblood group\b.*\b(report|lab)\b', lower_query):
                # Prioritize blood group over report if both keywords are present
                with sqlite3.connect('databases/patients.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT blood_group FROM patients WHERE patient_id = ?", (patient_id,))
                    profile = cursor.fetchone()
                    if profile and profile['blood_group']:
                        db_result_found = True
                        response = f"Your blood group: {profile['blood_group']}"
                    else:
                        response = "No blood group found."

            elif re.search(r'\blab\b|\breport\b|\breports\b', lower_query):
                with sqlite3.connect('databases/lab_reports.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, lab_assistant_name, report_date FROM lab_reports WHERE patient_id = ? ORDER BY id ASC LIMIT 1",
                                   (patient_id,))
                    report = cursor.fetchone()
                    if report:
                        db_result_found = True
                        response = f"Your lab report: ID {report['id']}, Date: {report['report_date']}, Lab Assistant: {report['lab_assistant_name']}. View: <a href='/patient/download_lab_report/{report['id']}?view=true' target='_blank'>Click here</a>"
                    else:
                        response = "No lab reports found."
            
            elif re.search(r'\bprescription\b|\bprescriptions\b', lower_query):
                with sqlite3.connect('databases/prescriptions.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT prescription_id, doctor_name, prescription_date FROM prescriptions WHERE patient_id = ? ORDER BY prescription_date DESC LIMIT 1",
                                   (patient_id,))
                    prescription = cursor.fetchone()
                    if prescription:
                        db_result_found = True
                        response = f"Your prescription: ID {prescription['prescription_id']}, Date: {prescription['prescription_date']}, Doctor: {prescription['doctor_name']}. View: <a href='/patient/download_prescription/{prescription['prescription_id']}?view=true' target='_blank'>Click here</a>"
                    else:
                        response = "No prescriptions found."
            
            elif re.search(r'\bprofile\b|\bmy details\b', lower_query):
                with sqlite3.connect('databases/patients.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT name, date_of_birth, contact FROM patients WHERE patient_id = ?", (patient_id,))
                    profile = cursor.fetchone()
                    if profile:
                        db_result_found = True
                        response = f"Your profile: Name: {profile['name']}, DOB: {profile['date_of_birth']}, Contact: {profile['contact']}"
                    else:
                        response = "Profile not found."
            
            elif re.search(r'\bmedical history\b|\bhistory\b', lower_query):
                with sqlite3.connect('databases/patients.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT medical_history FROM patients WHERE patient_id = ?", (patient_id,))
                    profile = cursor.fetchone()
                    if profile and profile['medical_history']:
                        db_result_found = True
                        response = f"Your medical history: {profile['medical_history']}"
                    else:
                        response = "No medical history found."
            
            elif re.search(r'\ballergies\b|\ballergy\b', lower_query):
                with sqlite3.connect('databases/patients.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT allergies FROM patients WHERE patient_id = ?", (patient_id,))
                    profile = cursor.fetchone()
                    if profile and profile['allergies']:
                        db_result_found = True
                        response = f"Your allergies: {profile['allergies']}"
                    else:
                        response = "No allergies found."
            
            elif re.search(r'\bmedicine\b|\bmedicines\b', lower_query):
                # Check for specific conditions (e.g., "medicine for fever")
                condition_match = re.search(r'\b(for)\b.*\b(fever|headache)\b', lower_query)
                with sqlite3.connect('databases/prescriptions.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT medicine_name FROM prescriptions WHERE patient_id = ? ORDER BY prescription_date DESC LIMIT 1",
                                   (patient_id,))
                    prescription = cursor.fetchone()
                    if prescription and prescription['medicine_name'] and not condition_match:
                        db_result_found = True
                        response = f"Your latest medicine: {prescription['medicine_name']}"
                    else:
                        response = "No medicines found."
            
            elif re.search(r'\btotal prescription\b|\btotal prescriptions\b', lower_query):
                with sqlite3.connect('databases/prescriptions.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM prescriptions WHERE patient_id = ?", (patient_id,))
                    count = cursor.fetchone()[0]
                    db_result_found = True
                    response = f"Your total prescriptions: {count}"
            
            elif re.search(r'\btotal lab report\b|\btotal lab reports\b', lower_query):
                with sqlite3.connect('databases/lab_reports.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM lab_reports WHERE patient_id = ?", (patient_id,))
                    count = cursor.fetchone()[0]
                    db_result_found = True
                    response = f"Your total lab reports: {count}"
            
            elif re.search(r'\bpreferred doctor\b|\bdoctor\b|\bwho is my doctor\b', lower_query):
                with sqlite3.connect('databases/patients.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT preferred_doctor FROM patients WHERE patient_id = ?", (patient_id,))
                    patient = cursor.fetchone()
                    if patient and patient['preferred_doctor']:
                        with sqlite3.connect('databases/doctors.db') as conn2:
                            conn2.row_factory = sqlite3.Row
                            cursor2 = conn2.cursor()
                            cursor2.execute("SELECT name FROM doctors WHERE doctor_id = ?", (patient['preferred_doctor'],))
                            doctor = cursor2.fetchone()
                            if doctor:
                                db_result_found = True
                                response = f"Your preferred doctor: {doctor['name']}"
                            else:
                                response = "No record found for your preferred doctor."
                    else:
                        response = "No preferred doctor found."
            
            elif re.search(r'\blab assistant\b', lower_query):
                with sqlite3.connect('databases/lab_reports.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT lab_assistant_name FROM lab_reports WHERE patient_id = ? ORDER BY id ASC LIMIT 1",
                                   (patient_id,))
                    report = cursor.fetchone()
                    if report and report['lab_assistant_name']:
                        db_result_found = True
                        response = f"Lab assistant for your latest report: {report['lab_assistant_name']}"
                    else:
                        response = "No lab reports or lab assistant found."
            
            elif re.search(r'\bappointment\b|\bappointments\b', lower_query):
                db_result_found = True
                response = "Appointments feature is not available yet. Please contact the admin."
            
            elif re.search(r'\bemergency contact\b', lower_query):
                with sqlite3.connect('databases/patients.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT emergency_contact FROM patients WHERE patient_id = ?", (patient_id,))
                    profile = cursor.fetchone()
                    if profile and profile['emergency_contact']:
                        db_result_found = True
                        response = f"Your emergency contact: {profile['emergency_contact']}"
                    else:
                        response = "No emergency contact found."
            
            elif re.search(r'\binsurance\b|\binsurance details\b', lower_query):
                with sqlite3.connect('databases/patients.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT insurance_details FROM patients WHERE patient_id = ?", (patient_id,))
                    profile = cursor.fetchone()
                    if profile and profile['insurance_details']:
                        db_result_found = True
                        response = f"Your insurance details: {profile['insurance_details']}"
                    else:
                        response = "No insurance details found."
            
            elif re.search(r'\bactivity\b|\bactivity logs\b|\brecent activity\b', lower_query):
                with sqlite3.connect('databases/activity_logs.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT action, timestamp FROM activity_logs WHERE username = ? ORDER BY timestamp DESC LIMIT 10",
                                   (patient_id,))
                    logs = cursor.fetchall()
                    if logs:
                        db_result_found = True
                        response = f"Your recent activity:\n" + "\n".join([f"- {log['action']} at {log['timestamp']}" for log in logs])
                    else:
                        response = "No recent activity found."
            
            elif re.search(r'\bblood group\b', lower_query):
                with sqlite3.connect('databases/patients.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT blood_group FROM patients WHERE patient_id = ?", (patient_id,))
                    profile = cursor.fetchone()
                    if profile and profile['blood_group']:
                        db_result_found = True
                        response = f"Your blood group: {profile['blood_group']}"
                    else:
                        response = "No blood group found."
            
            else:
                # If no database match, use Gemini API to generate a response
                try:
                    prompt = f"Answer this medical-related question in a detailed and informative way, providing at least 3-4 sentences of explanation: {query}"
                    gemini_response = model.generate_content(prompt)
                    response = gemini_response.text.strip()
                    response = f"Here’s the information: {response}"
                except Exception as e:
                    response = "Sorry, I couldn’t find an answer right now. You can ask about your lab report or prescription instead!"
            
            return jsonify({'response': response})

        except Exception as e:
            return jsonify({'response': f"Error: {str(e)}"}), 500
    
    return jsonify({'response': "No query provided."}), 400