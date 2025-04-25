from flask import Flask
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.doctor_routes import doctor_bp
from routes.patient_routes import patient_bp
from routes.lab_assistant_routes import lab_assistant_bp
from utils.db_utils import init_db

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with a secure secret key

# Register blueprints with appropriate prefixes
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(doctor_bp)
app.register_blueprint(patient_bp, url_prefix='/patient')  # Added url_prefix for patient routes
app.register_blueprint(lab_assistant_bp)

if __name__ == '__main__':
    init_db()  # Initialize the database
    app.run(debug=True)