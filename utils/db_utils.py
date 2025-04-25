import sqlite3
import os
import random
import string
from werkzeug.security import generate_password_hash
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import PageTemplate, Frame
from reportlab.platypus.flowables import HRFlowable

def init_db():
    os.makedirs('databases', exist_ok=True)

    # Initialize lab_reports database
    with sqlite3.connect('databases/lab_reports.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS lab_reports
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        lab_assistant_id TEXT,
                        lab_assistant_name TEXT,
                        patient_id TEXT,
                        patient_name TEXT,
                        report_date TEXT,
                        report_time TEXT,
                        report_file BLOB,
                        FOREIGN KEY (lab_assistant_id) REFERENCES lab_assistants(lab_assistant_id),
                        FOREIGN KEY (patient_id) REFERENCES patients(patient_id))''')
        try:
            cursor.execute("ALTER TABLE lab_reports ADD COLUMN lab_assistant_name TEXT")
        except sqlite3.OperationalError:
            pass
        conn.commit()

    # Initialize users database
    with sqlite3.connect('databases/users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users
                        (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
        cursor.execute("SELECT username FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users VALUES (?, ?, ?)",
                         ('admin', generate_password_hash('admin123'), 'admin'))
        conn.commit()

    # Initialize doctors database
    with sqlite3.connect('databases/doctors.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS doctors
                        (doctor_id TEXT PRIMARY KEY, name TEXT, email TEXT, phone TEXT, blood_group TEXT,
                         specialization TEXT, date_of_birth TEXT, medical_registration_number TEXT,
                         gender TEXT, address TEXT, emergency_contact TEXT, department TEXT)''')
        conn.commit()

    # Initialize patients database
    with sqlite3.connect('databases/patients.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS patients
                        (patient_id TEXT PRIMARY KEY, name TEXT, date_of_birth TEXT, gender TEXT,
                         address TEXT, contact TEXT, emergency_contact TEXT, insurance_details TEXT,
                         blood_group TEXT, allergies TEXT, medical_history TEXT, preferred_doctor TEXT)''')
        conn.commit()

    # Initialize lab_assistants database
    with sqlite3.connect('databases/lab_assistants.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS lab_assistants
                        (lab_assistant_id TEXT PRIMARY KEY, name TEXT, email TEXT, phone TEXT,
                         date_of_birth TEXT, gender TEXT, blood_group TEXT, address TEXT,
                         emergency_contact TEXT, qualification TEXT, lab_registration_number TEXT,
                         lab_department TEXT)''')
        conn.commit()

    # Initialize activity_logs database
    with sqlite3.connect('databases/activity_logs.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS activity_logs
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, action TEXT, timestamp TEXT)''')
        conn.commit()

    # Initialize prescriptions database
    with sqlite3.connect('databases/prescriptions.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS prescriptions (
            prescription_id TEXT PRIMARY KEY,
            patient_id TEXT,
            doctor_id TEXT,
            patient_name TEXT,
            doctor_name TEXT,
            symptoms TEXT,
            diagnosis TEXT,
            advice TEXT,
            medicine_name TEXT,
            dosage TEXT,
            frequency TEXT,
            duration TEXT,
            notes TEXT,
            prescription_date TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
        )''')
        try:
            cursor.execute("ALTER TABLE prescriptions ADD COLUMN patient_name TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE prescriptions ADD COLUMN doctor_name TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE prescriptions ADD COLUMN prescription_date TEXT")
        except sqlite3.OperationalError:
            pass
        conn.commit()

    # Initialize prescriptions_pdf database
    with sqlite3.connect('databases/prescriptions_pdf.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS prescriptions_pdf (
            prescription_id TEXT PRIMARY KEY,
            pdf_data BLOB,
            FOREIGN KEY (prescription_id) REFERENCES prescriptions(prescription_id)
        )''')
        conn.commit()

def generate_prescription_id():
    prefix = "PR"
    while True:
        digits = ''.join(random.choices(string.digits, k=6))
        prescription_id = f"{prefix}{digits}"
        with sqlite3.connect('databases/prescriptions.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT prescription_id FROM prescriptions WHERE prescription_id = ?", (prescription_id,))
            if not cursor.fetchone():
                return prescription_id

def save_prescription(prescription_data):
    """Save prescription details to prescriptions.db."""
    try:
        with sqlite3.connect('databases/prescriptions.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO prescriptions 
                            (prescription_id, patient_id, doctor_id, patient_name, doctor_name, 
                             symptoms, diagnosis, advice, medicine_name, dosage, frequency, 
                             duration, notes, prescription_date) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (prescription_data['prescription_id'],
                           prescription_data['patient_id'],
                           prescription_data['doctor_id'],
                           prescription_data['patient_name'],
                           prescription_data['doctor_name'],
                           prescription_data['symptoms'],
                           prescription_data['diagnosis'],
                           prescription_data['advice'],
                           prescription_data['medicine_name'],
                           prescription_data['dosage'],
                           prescription_data['frequency'],
                           prescription_data['duration'],
                           prescription_data['notes'],
                           prescription_data['prescription_date']))
            conn.commit()
    except sqlite3.Error as e:
        raise Exception(f"Failed to save prescription to prescriptions.db: {str(e)}")

def header(canvas, doc):
    """Add a header to each page of the PDF."""
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#1E3A8A"))
    canvas.rect(0, letter[1] - 80, letter[0], 80, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawCentredString(letter[0] / 2, letter[1] - 40, "Prescription")
    canvas.setFont("Helvetica", 10)
    canvas.drawString(40, letter[1] - 60, "MediCare Clinic")
    canvas.drawRightString(letter[0] - 40, letter[1] - 60, f"Prescription ID: {doc.prescription_id}")
    canvas.restoreState()

def footer(canvas, doc):
    """Add a footer to each page of the PDF."""
    canvas.saveState()
    canvas.setFont("Helvetica-Oblique", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(letter[0] / 2, 30, "This prescription is valid for 30 days. Please consult your doctor for further advice.")
    canvas.line(40, 50, letter[0] - 40, 50)
    canvas.drawString(letter[0] - 150, 60, "Doctor's Signature: ________________")
    canvas.restoreState()

def generate_and_save_pdf(prescription_data):
    """Generate a professionally styled PDF for the prescription and save it to prescriptions_pdf.db."""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
            topMargin=1.5*inch,  # Increased to accommodate header
            bottomMargin=1.5*inch  # Increased to accommodate footer
        )
        doc.prescription_id = prescription_data['prescription_id']

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor("#1E3A8A")
        )
        label_style = ParagraphStyle(
            'LabelStyle',
            parent=styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Bold',
            spaceAfter=6
        )
        content_style = ParagraphStyle(
            'ContentStyle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            leading=14,  # Line spacing for better readability
            alignment=0  # Left-aligned
        )
        table_content_style = ParagraphStyle(
            'TableContentStyle',
            parent=styles['Normal'],
            fontSize=10,  # Smaller font for table content
            leading=12,
            alignment=0
        )

        story = []

        # Patient & Doctor Details Section
        story.append(Paragraph("Patient & Doctor Details", title_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=12))
        details_data = [
            ["Patient Name:", Paragraph(prescription_data['patient_name'], content_style)],
            ["Doctor Name:", Paragraph(prescription_data['doctor_name'], content_style)],
            ["Date:", Paragraph(prescription_data['prescription_date'], content_style)]
        ]
        details_table = Table(
            details_data,
            colWidths=[1.5*inch, doc.width - 1.5*inch]  # Adjusted to fit page width
        )
        details_table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 12),
            ('FONT', (1, 0), (1, -1), 'Helvetica', 12),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(details_table)
        story.append(Spacer(1, 0.5*inch))  # Increased spacing

        # Symptoms Section
        story.append(Paragraph("Symptoms", title_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=6))
        story.append(Paragraph(prescription_data['symptoms'], content_style))
        story.append(Spacer(1, 0.5*inch))

        # Diagnosis Section
        story.append(Paragraph("Diagnosis", title_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=6))
        story.append(Paragraph(prescription_data['diagnosis'], content_style))
        story.append(Spacer(1, 0.5*inch))

        # Medication Section
        story.append(Paragraph("Medication", title_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=6))
        medication_data = [
            ["Medicine Name", "Dosage", "Frequency", "Duration"],
            [
                Paragraph(prescription_data['medicine_name'], table_content_style),
                Paragraph(prescription_data['dosage'], table_content_style),
                Paragraph(prescription_data['frequency'], table_content_style),
                Paragraph(prescription_data['duration'], table_content_style)
            ]
        ]
        # Dynamically calculate column widths to fit the page
        table_width = doc.width
        col_width = table_width / 4  # Equal width for each column
        medication_table = Table(
            medication_data,
            colWidths=[col_width, col_width, col_width, col_width]
        )
        medication_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 12),
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        story.append(medication_table)
        story.append(Spacer(1, 0.5*inch))

        # Advice Section (if present)
        if prescription_data['advice']:
            story.append(Paragraph("Advice", title_style))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=6))
            story.append(Paragraph(prescription_data['advice'], content_style))
            story.append(Spacer(1, 0.5*inch))

        # Notes Section (if present)
        if prescription_data['notes']:
            story.append(Paragraph("Notes", title_style))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=6))
            story.append(Paragraph(prescription_data['notes'], content_style))
            story.append(Spacer(1, 0.5*inch))

        # Define the page frame
        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id='normal'
        )
        template = PageTemplate(id='prescription_template', frames=frame, onPage=header, onPageEnd=footer)
        doc.addPageTemplates([template])

        doc.build(story)

        pdf_data = buffer.getvalue()
        buffer.close()

        # Save to database
        with sqlite3.connect('databases/prescriptions_pdf.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO prescriptions_pdf (prescription_id, pdf_data) 
                            VALUES (?, ?)''',
                          (prescription_data['prescription_id'], pdf_data))
            conn.commit()

        return pdf_data
    except Exception as e:
        raise Exception(f"Failed to generate or save PDF: {str(e)}")
    
    
def get_prescriptions_for_doctor(doctor_id):
    """Fetch all prescriptions for a given doctor."""
    try:
        with sqlite3.connect('databases/prescriptions.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT prescription_id, patient_name, prescription_date FROM prescriptions WHERE doctor_id = ? ORDER BY prescription_date DESC", 
                           (doctor_id,))
            prescriptions = cursor.fetchall()
            return prescriptions
    except sqlite3.Error as e:
        raise Exception(f"Failed to fetch prescriptions: {str(e)}")

def get_prescription_pdf(prescription_id):
    """Retrieve the PDF binary data for a given prescription."""
    try:
        with sqlite3.connect('databases/prescriptions_pdf.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pdf_data FROM prescriptions_pdf WHERE prescription_id = ?", (prescription_id,))
            result = cursor.fetchone()
            if not result:
                raise Exception(f"PDF not found for prescription ID {prescription_id}")
            return result[0]
    except sqlite3.Error as e:
        raise Exception(f"Failed to fetch PDF: {str(e)}")

def get_lab_reports_for_doctor(doctor_id):
    """Fetch all lab reports for patients assigned to a given doctor."""
    try:
        with sqlite3.connect('databases/patients.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT patient_id, name, contact FROM patients WHERE preferred_doctor = ?", (doctor_id,))
            patients = cursor.fetchall()
            patient_ids = [patient['patient_id'] for patient in patients]
            patient_info = {patient['patient_id']: {'name': patient['name'], 'contact': patient['contact']} for patient in patients}

        if not patient_ids:
            return []

        with sqlite3.connect('databases/lab_reports.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            placeholders = ','.join('?' for _ in patient_ids)
            query = f"SELECT id, patient_id, patient_name, lab_assistant_name, report_date, report_time FROM lab_reports WHERE patient_id IN ({placeholders}) ORDER BY report_date DESC, report_time DESC"
            cursor.execute(query, patient_ids)
            lab_reports = cursor.fetchall()

        enriched_reports = []
        for report in lab_reports:
            patient_id = report['patient_id']
            patient_contact = patient_info.get(patient_id, {}).get('contact', 'N/A')
            enriched_report = dict(report)
            enriched_report['patient_contact'] = patient_contact
            enriched_reports.append(enriched_report)

        return enriched_reports
    except sqlite3.Error as e:
        raise Exception(f"Failed to fetch lab reports: {str(e)}")

def get_lab_report_pdf(report_id):
    """Retrieve the PDF binary data for a given lab report."""
    try:
        with sqlite3.connect('databases/lab_reports.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT report_file FROM lab_reports WHERE id = ?", (report_id,))
            result = cursor.fetchone()
            if not result:
                raise Exception(f"PDF not found for lab report ID {report_id}")
            return result[0]
    except sqlite3.Error as e:
        raise Exception(f"Failed to fetch lab report PDF: {str(e)}")

def update_doctor_profile(doctor_id, updates):
    """Update the doctor's profile in doctors.db."""
    try:
        with sqlite3.connect('databases/doctors.db') as conn:
            cursor = conn.cursor()
            # Build the SET clause dynamically based on the updates dictionary
            set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
            query = f"UPDATE doctors SET {set_clause} WHERE doctor_id = ?"
            values = list(updates.values()) + [doctor_id]
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0  # Return True if update was successful
    except sqlite3.Error as e:
        raise Exception(f"Failed to update doctor profile: {str(e)}")

def get_doctor_activity_logs(doctor_id):
    """Fetch the activity logs for a given doctor."""
    try:
        with sqlite3.connect('databases/activity_logs.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT action, timestamp FROM activity_logs WHERE username = ? ORDER BY timestamp DESC LIMIT 50", 
                           (doctor_id,))
            logs = cursor.fetchall()
            return logs
    except sqlite3.Error as e:
        raise Exception(f"Failed to fetch activity logs: {str(e)}")

def generate_doctor_id():
    prefix = "EMP"
    while True:
        digits = ''.join(random.choices(string.digits, k=4))
        doctor_id = f"{prefix}{digits}"
        with sqlite3.connect('databases/doctors.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT doctor_id FROM doctors WHERE doctor_id = ?", (doctor_id,))
            if not cursor.fetchone():
                return doctor_id

def generate_patient_id():
    prefix = "PID"
    while True:
        digits = ''.join(random.choices(string.digits, k=4))
        patient_id = f"{prefix}{digits}"
        with sqlite3.connect('databases/patients.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT patient_id FROM patients WHERE patient_id = ?", (patient_id,))
            if not cursor.fetchone():
                return patient_id

def generate_lab_assistant_id():
    prefix = "LA"
    while True:
        digits = ''.join(random.choices(string.digits, k=4))
        lab_assistant_id = f"{prefix}{digits}"
        with sqlite3.connect('databases/lab_assistants.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT lab_assistant_id FROM lab_assistants WHERE lab_assistant_id = ?", (lab_assistant_id,))
            if not cursor.fetchone():
                return lab_assistant_id

def log_activity(username, action):
    with sqlite3.connect('databases/activity_logs.db') as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT INTO activity_logs (username, action, timestamp) VALUES (?, ?, ?)",
                      (username, action, timestamp))
        conn.commit()

