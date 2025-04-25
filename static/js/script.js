document.addEventListener('DOMContentLoaded', () => {
    // Sidebar toggle
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const menuToggle = document.querySelector('.menu-toggle');

    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            mainContent.classList.toggle('collapsed');
        });
    }

    // Flash message dismissal
    const flashCloses = document.querySelectorAll('.flash-close');
    flashCloses.forEach(closeBtn => {
        closeBtn.addEventListener('click', () => {
            const flashMessage = closeBtn.parentElement;
            flashMessage.style.transition = 'opacity 0.3s';
            flashMessage.style.opacity = '0';
            setTimeout(() => flashMessage.remove(), 300);
        });
    });

    // Form input animations (include select elements)
    const inputs = document.querySelectorAll('.form-group input, .form-group textarea, .form-group select');
    inputs.forEach(input => {
        input.addEventListener('focus', () => {
            input.parentElement.classList.add('focused');
        });
        input.addEventListener('blur', () => {
            if (!input.value) {
                input.parentElement.classList.remove('focused');
            }
        });
    });

    // Fetch stats for dashboard
    if (document.getElementById('doctor-count')) {
        fetchStats();
    }

    // Profile form validation
    const profileForm = document.querySelector('form[name="update_profile"]');
    if (profileForm) {
        profileForm.addEventListener('submit', (e) => {
            const name = document.getElementById('name')?.value;
            if (name && name.trim().length < 2) {
                e.preventDefault();
                alert('Name must be at least 2 characters long.');
            }
        });
    }

    // Password form validation
    const passwordForm = document.querySelector('form[name="change_password"]');
    if (passwordForm) {
        passwordForm.addEventListener('submit', (e) => {
            const newPassword = document.getElementById('new_password')?.value;
            const confirmPassword = document.getElementById('confirm_password')?.value;

            if (!newPassword) {
                e.preventDefault();
                alert('Please enter a new password.');
            } else if (newPassword.length < 6) {
                e.preventDefault();
                alert('New password must be at least 6 characters long.');
            } else if (newPassword !== confirmPassword) {
                e.preventDefault();
                alert('New passwords do not match.');
            }
        });
    }

    // Add doctor form validation
    const doctorForm = document.querySelector('.doctor-form');
    if (doctorForm) {
        doctorForm.addEventListener('submit', (e) => {
            const name = document.getElementById('name')?.value;
            const email = document.getElementById('email')?.value;
            const phone = document.getElementById('phone')?.value;
            const password = document.getElementById('password')?.value;
            const dateOfBirth = document.getElementById('date_of_birth')?.value;
            const medicalRegistrationNumber = document.getElementById('medical_registration_number')?.value;
            const specialization = document.getElementById('specialization')?.value;
            const gender = document.getElementById('gender')?.value;
            const department = document.getElementById('department')?.value;

            if (!name || name.trim().length < 2) {
                e.preventDefault();
                alert('Name must be at least 2 characters long.');
                return;
            }
            if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
                e.preventDefault();
                alert('Please enter a valid email address.');
                return;
            }
            if (!phone || !/^\+?\d{10,15}$/.test(phone)) {
                e.preventDefault();
                alert('Please enter a valid phone number (10-15 digits).');
                return;
            }
            if (!password || password.length < 6) {
                e.preventDefault();
                alert('Password must be at least 6 characters long.');
                return;
            }
            if (!dateOfBirth) {
                e.preventDefault();
                alert('Please enter a date of birth.');
                return;
            }
            const dob = new Date(dateOfBirth);
            const today = new Date();
            if (dob > today) {
                e.preventDefault();
                alert('Date of birth cannot be in the future.');
                return;
            }
            const age = today.getFullYear() - dob.getFullYear();
            if (age < 25) {
                e.preventDefault();
                alert('Doctors must be at least 25 years old.');
                return;
            }
            if (!medicalRegistrationNumber || medicalRegistrationNumber.length < 5) {
                e.preventDefault();
                alert('Medical registration number must be at least 5 characters.');
                return;
            }
            if (!specialization || specialization.trim().length < 3) {
                e.preventDefault();
                alert('Specialization must be at least 3 characters long.');
                return;
            }
            if (!gender) {
                e.preventDefault();
                alert('Please select a gender.');
                return;
            }
            if (!department) {
                e.preventDefault();
                alert('Please select a department.');
                return;
            }
        });
    }

    // Add patient form validation
    const patientForm = document.querySelector('.patient-form');
    if (patientForm) {
        patientForm.addEventListener('submit', (e) => {
            const username = document.getElementById('username')?.value;
            const password = document.getElementById('password')?.value;
            const name = document.getElementById('name')?.value;
            const dateOfBirth = document.getElementById('date_of_birth')?.value;
            const contact = document.getElementById('contact')?.value;
            const gender = document.getElementById('gender')?.value;
            const emergencyContact = document.getElementById('emergency_contact')?.value;

            if (!username || username.trim().length < 3) {
                e.preventDefault();
                alert('Username must be at least 3 characters long.');
                return;
            }
            if (!password || password.length < 6) {
                e.preventDefault();
                alert('Password must be at least 6 characters long.');
                return;
            }
            if (!name || name.trim().length < 2) {
                e.preventDefault();
                alert('Name must be at least 2 characters long.');
                return;
            }
            if (!dateOfBirth) {
                e.preventDefault();
                alert('Please enter a date of birth.');
                return;
            }
            const dob = new Date(dateOfBirth);
            const today = new Date();
            if (dob > today) {
                e.preventDefault();
                alert('Date of birth cannot be in the future.');
                return;
            }
            if (!contact || !/^\+?\d{10,15}$/.test(contact)) {
                e.preventDefault();
                alert('Please enter a valid contact number (10-15 digits).');
                return;
            }
            if (!gender) {
                e.preventDefault();
                alert('Please select a gender.');
                return;
            }
            if (emergencyContact && !/^\+?\d{10,15}$/.test(emergencyContact)) {
                e.preventDefault();
                alert('Please enter a valid emergency contact number (10-15 digits) or leave it empty.');
                return;
            }
        });
    }
});

async function fetchStats() {
    const doctorCountEl = document.getElementById('doctor-count');
    const patientCountEl = document.getElementById('patient-count');
    const labAssistantCountEl = document.getElementById('lab-assistant-count');

    // Show loading state
    if (doctorCountEl && patientCountEl && labAssistantCountEl) {
        doctorCountEl.textContent = 'Loading...';
        patientCountEl.textContent = 'Loading...';
        labAssistantCountEl.textContent = 'Loading...';
    }

    try {
        const response = await fetch('/api/stats');
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const stats = await response.json();

        if (doctorCountEl && patientCountEl && labAssistantCountEl) {
            doctorCountEl.textContent = stats.doctors || 0;
            patientCountEl.textContent = stats.patients || 0;
            labAssistantCountEl.textContent = stats.labAssistants || 0;
        }
    } catch (error) {
        console.error('Error fetching stats:', error);
        if (doctorCountEl && patientCountEl && labAssistantCountEl) {
            doctorCountEl.textContent = 'Error';
            patientCountEl.textContent = 'Error';
            labAssistantCountEl.textContent = 'Error';
        }
    }
}


document.addEventListener('DOMContentLoaded', () => {
    // Sidebar Toggle
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const menuToggle = document.querySelector('.menu-toggle');

    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            mainContent.classList.toggle('collapsed');
        });
    }

    // Flash Message Dismissal
    const flashCloses = document.querySelectorAll('.flash-close');
    flashCloses.forEach(close => {
        close.addEventListener('click', () => {
            const flash = close.parentElement;
            flash.style.opacity = '0';
            setTimeout(() => flash.remove(), 300);
        });
    });

    // Search Form Handling
    const searchForm = document.querySelector('.search-form');
    if (searchForm) {
        const searchInput = searchForm.querySelector('input[name="search"]');
        const searchButton = searchForm.querySelector('.search-btn');

        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchForm.submit();
            }
        });

        searchButton.addEventListener('click', (e) => {
            e.preventDefault();
            searchForm.submit();
        });
    }

    // Doctor Form Validation (for add/edit doctor)
    const doctorForm = document.querySelector('.doctor-form');
    if (doctorForm) {
        doctorForm.addEventListener('submit', (e) => {
            const fields = {
                name: document.getElementById('name')?.value.trim(),
                email: document.getElementById('email')?.value.trim(),
                phone: document.getElementById('phone')?.value.trim(),
                password: document.getElementById('password')?.value,
                dateOfBirth: document.getElementById('date_of_birth')?.value,
                medicalRegistrationNumber: document.getElementById('medical_registration_number')?.value.trim()
            };

            if (fields.name && fields.name.length < 2) {
                e.preventDefault();
                alert('Name must be at least 2 characters.');
                return;
            }

            if (fields.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(fields.email)) {
                e.preventDefault();
                alert('Invalid email address.');
                return;
            }

            if (fields.phone && !/^\+?\d{10,15}$/.test(fields.phone)) {
                e.preventDefault();
                alert('Phone number must be 10-15 digits.');
                return;
            }

            if (fields.password && fields.password.length < 6) {
                e.preventDefault();
                alert('Password must be at least 6 characters.');
                return;
            }

            if (fields.dateOfBirth) {
                const dob = new Date(fields.dateOfBirth);
                const today = new Date();
                if (dob > today) {
                    e.preventDefault();
                    alert('Date of birth cannot be in the future.');
                    return;
                }
                const age = today.getFullYear() - dob.getFullYear();
                if (age < 25) {
                    e.preventDefault();
                    alert('Doctors must be at least 25 years old.');
                    return;
                }
            }

            if (fields.medicalRegistrationNumber && fields.medicalRegistrationNumber.length < 5) {
                e.preventDefault();
                alert('Medical registration number must be at least 5 characters.');
                return;
            }
        });
    }

    // Patient Form Validation
    const patientForm = document.querySelector('.patient-form');
    if (patientForm) {
        patientForm.addEventListener('submit', (e) => {
            const fields = {
                username: document.getElementById('username')?.value.trim(),
                password: document.getElementById('password')?.value,
                name: document.getElementById('name')?.value.trim(),
                dateOfBirth: document.getElementById('date_of_birth')?.value,
                contact: document.getElementById('contact')?.value.trim()
            };

            if (fields.username && fields.username.length < 3) {
                e.preventDefault();
                alert('Username must be at least 3 characters.');
                return;
            }

            if (fields.password && fields.password.length < 6) {
                e.preventDefault();
                alert('Password must be at least 6 characters.');
                return;
            }

            if (fields.name && fields.name.length < 2) {
                e.preventDefault();
                alert('Name must be at least 2 characters.');
                return;
            }

            if (fields.dateOfBirth) {
                const dob = new Date(fields.dateOfBirth);
                const today = new Date();
                if (dob > today) {
                    e.preventDefault();
                    alert('Date of birth cannot be in the future.');
                    return;
                }
            }

            if (fields.contact && !/^\+?\d{10,15}$/.test(fields.contact)) {
                e.preventDefault();
                alert('Contact number must be 10-15 digits.');
                return;
            }
        });
    }
});


