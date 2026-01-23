from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
from sqlalchemy import func, desc
import os

from app import db
from app.models import Doctor, Patient, Appointment

main = Blueprint('main', __name__)


def _delete_static_file(rel_path: str | None):
    """
    Delete a file inside app/static if it exists.
    rel_path example: 'uploads/abc.png'
    """
    if not rel_path:
        return
    abs_path = os.path.join('app', 'static', rel_path)
    if os.path.exists(abs_path):
        try:
            os.remove(abs_path)
        except Exception:
            pass


# ---------------- HOME ----------------
@main.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.login'))


# ---------------- ABOUT ----------------
@main.route('/about')
def about():
    doctors = Doctor.query.order_by(Doctor.created_at.desc()).all()
    return render_template('about.html', doctors=doctors)


# ---------------- REGISTER ----------------
@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = (request.form.get('username') or "").strip()
        email = (request.form.get('email') or "").strip().lower()
        password = request.form.get('password') or ""

        if not username or not email or not password:
            flash("Please fill in all fields.", "danger")
            return redirect(url_for('main.register'))

        if Doctor.query.filter(func.lower(Doctor.email) == email).first():
            flash("Email already exists!", "danger")
            return redirect(url_for('main.register'))

        if Doctor.query.filter(Doctor.username == username).first():
            flash("Username already exists!", "danger")
            return redirect(url_for('main.register'))

        doctor = Doctor(username=username, email=email)
        doctor.set_password(password)
        db.session.add(doctor)
        db.session.commit()

        flash("Account created! Please login.", "success")
        return redirect(url_for('main.login'))

    return render_template('register.html')


# ---------------- LOGIN ----------------
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_or_username = (request.form.get('email') or "").strip().lower()
        password = request.form.get('password') or ""

        doctor = Doctor.query.filter(func.lower(Doctor.email) == email_or_username).first()
        if not doctor:
            doctor = Doctor.query.filter(Doctor.username == email_or_username).first()

        if doctor and doctor.check_password(password):
            login_user(doctor)
            flash("Login successful!", "success")
            return redirect(url_for('main.dashboard'))

        flash("Invalid email or password!", "danger")
        return redirect(url_for('main.login'))

    return render_template('login.html')


# ---------------- LOGOUT ----------------
@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for('main.login'))


# =========================
# DASHBOARD
# =========================
@main.route('/dashboard')
@login_required
def dashboard():
    total_patients = Patient.query.filter_by(doctor_id=current_user.id).count()

    recent_patients = (
        Patient.query
        .filter_by(doctor_id=current_user.id)
        .order_by(desc(Patient.created_at))
        .limit(6)
        .all()
    )

    recent_appointments = (
        Appointment.query
        .filter_by(doctor_id=current_user.id)
        .order_by(desc(Appointment.created_at))
        .limit(6)
        .all()
    )

    return render_template(
        'dashboard.html',
        total_patients=total_patients,
        recent_patients=recent_patients,
        recent_appointments=recent_appointments
    )


# =========================
# PATIENTS
# =========================

@main.route('/patients')
@login_required
def patients():
    q = (request.args.get('q') or "").strip()
    query = Patient.query.filter_by(doctor_id=current_user.id)

    if q:
        like = f"%{q}%"
        query = query.filter(Patient.full_name.ilike(like))

    patients_list = query.order_by(desc(Patient.created_at)).all()
    return render_template('patients.html', patients=patients_list, q=q)


@main.route('/patients/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if patient.doctor_id != current_user.id:
        abort(403)
    return render_template('patient_detail.html', patient=patient)


@main.route('/patients/add', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or "").strip()
        birth_date = request.form.get('birth_date')
        gender = request.form.get('gender') or ""
        allergies = (request.form.get('allergies') or "").strip()
        medical_history = (request.form.get('medical_history') or "").strip()

        if not full_name or not birth_date:
            flash("Full name and birth date are required.", "danger")
            return redirect(url_for('main.add_patient'))

        birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d").date()

        photo = request.files.get('photo')
        image_path = None
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            upload_folder = os.path.join('app', 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            photo.save(os.path.join(upload_folder, filename))
            image_path = f"uploads/{filename}"

        patient = Patient(
            doctor_id=current_user.id,
            full_name=full_name,
            birth_date=birth_date_obj,
            gender=gender,
            allergies=allergies,
            medical_history=medical_history,
            image_path=image_path
        )

        db.session.add(patient)
        db.session.commit()
        flash("Patient added successfully!", "success")
        return redirect(url_for('main.patients'))

    return render_template('add_patient.html')


@main.route('/patients/<int:patient_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if patient.doctor_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        patient.full_name = (request.form.get('full_name') or "").strip()
        birth_date = request.form.get('birth_date')
        patient.gender = request.form.get('gender') or ""
        patient.allergies = (request.form.get('allergies') or "").strip()
        patient.medical_history = (request.form.get('medical_history') or "").strip()

        if not patient.full_name or not birth_date:
            flash("Full name and birth date are required.", "danger")
            return redirect(url_for('main.edit_patient', patient_id=patient.id))

        patient.birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()

        #  remove photo checkbox
        if request.form.get('remove_photo') == 'on':
            if patient.image_path:
                _delete_static_file(patient.image_path)
                patient.image_path = None

        #  upload new photo (replace old)
        photo = request.files.get('photo')
        if photo and photo.filename:
            if patient.image_path:
                _delete_static_file(patient.image_path)

            filename = secure_filename(photo.filename)
            upload_folder = os.path.join('app', 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            photo.save(os.path.join(upload_folder, filename))
            patient.image_path = f"uploads/{filename}"

        db.session.commit()
        flash("Patient updated successfully!", "success")
        return redirect(url_for('main.patient_detail', patient_id=patient.id))

    return render_template('edit_patient.html', patient=patient)


@main.route('/patients/<int:patient_id>/delete', methods=['POST'])
@login_required
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if patient.doctor_id != current_user.id:
        abort(403)

    # remove patient image file (optional cleanup)
    if patient.image_path:
        _delete_static_file(patient.image_path)

    # IMPORTANT: appointments should be deleted via model cascade (recommended)
    db.session.delete(patient)
    db.session.commit()
    flash("Patient deleted.", "info")
    return redirect(url_for('main.patients'))


# =========================
# APPOINTMENTS
# =========================

@main.route('/appointments')
@login_required
def appointments():
    q = (request.args.get('q') or "").strip()
    status = (request.args.get('status') or "").strip()

    query = Appointment.query.filter_by(doctor_id=current_user.id).join(Patient)

    if q:
        like = f"%{q}%"
        query = query.filter(Patient.full_name.ilike(like))

    if status:
        query = query.filter(Appointment.status == status)

    appts = query.order_by(desc(Appointment.scheduled_at)).all()
    return render_template('appointments.html', appointments=appts, q=q, status=status)


@main.route('/appointments/add', methods=['GET', 'POST'])
@login_required
def add_appointment():
    patients_list = Patient.query.filter_by(doctor_id=current_user.id).order_by(Patient.full_name.asc()).all()
    now_min = datetime.now().strftime("%Y-%m-%dT%H:%M")

    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        scheduled_at = request.form.get('scheduled_at')
        reason = (request.form.get('reason') or "").strip()
        notes = (request.form.get('notes') or "").strip()
        status = request.form.get('status') or "Scheduled"

        if not patient_id or not scheduled_at:
            flash("Patient and date/time are required.", "danger")
            return redirect(url_for('main.add_appointment'))

        patient = Patient.query.get_or_404(int(patient_id))
        if patient.doctor_id != current_user.id:
            abort(403)

        scheduled_dt = datetime.strptime(scheduled_at, "%Y-%m-%dT%H:%M")

        # block past dates (server-side)
        if scheduled_dt < datetime.now():
            flash("You cannot set an appointment in the past. Please choose a future date/time.", "danger")
            return redirect(url_for('main.add_appointment'))

        appt = Appointment(
            doctor_id=current_user.id,
            patient_id=patient.id,
            scheduled_at=scheduled_dt,
            reason=reason,
            notes=notes,
            status=status
        )
        db.session.add(appt)
        db.session.commit()

        flash("Appointment created successfully!", "success")
        return redirect(url_for('main.appointments'))

    return render_template('add_appointment.html', patients=patients_list, now_min=now_min)


@main.route('/appointments/<int:appointment_id>')
@login_required
def appointment_detail(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.doctor_id != current_user.id:
        abort(403)
    return render_template('appointment_detail.html', appointment=appt)


@main.route('/appointments/<int:appointment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.doctor_id != current_user.id:
        abort(403)

    patients_list = Patient.query.filter_by(doctor_id=current_user.id).order_by(Patient.full_name.asc()).all()
    now_min = datetime.now().strftime("%Y-%m-%dT%H:%M")

    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        scheduled_at = request.form.get('scheduled_at')
        reason = (request.form.get('reason') or "").strip()
        notes = (request.form.get('notes') or "").strip()
        status = request.form.get('status') or "Scheduled"

        if not patient_id or not scheduled_at:
            flash("Patient and date/time are required.", "danger")
            return redirect(url_for('main.edit_appointment', appointment_id=appt.id))

        patient = Patient.query.get_or_404(int(patient_id))
        if patient.doctor_id != current_user.id:
            abort(403)

        new_dt = datetime.strptime(scheduled_at, "%Y-%m-%dT%H:%M")

        if new_dt < datetime.now():
            flash("You cannot set an appointment in the past. Please choose a future date/time.", "danger")
            return redirect(url_for('main.edit_appointment', appointment_id=appt.id))

        appt.patient_id = patient.id
        appt.scheduled_at = new_dt
        appt.reason = reason
        appt.notes = notes
        appt.status = status

        db.session.commit()
        flash("Appointment updated successfully!", "success")
        return redirect(url_for('main.appointment_detail', appointment_id=appt.id))

    return render_template('edit_appointment.html', appointment=appt, patients=patients_list, now_min=now_min)


@main.route('/appointments/<int:appointment_id>/delete', methods=['POST'])
@login_required
def delete_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.doctor_id != current_user.id:
        abort(403)

    db.session.delete(appt)
    db.session.commit()
    flash("Appointment deleted.", "info")
    return redirect(url_for('main.appointments'))


# =========================
# DOCTOR PROFILE
# =========================

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


@main.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        username = (request.form.get('username') or "").strip()
        email = (request.form.get('email') or "").strip().lower()
        specialty = (request.form.get('specialty') or "").strip()
        phone = (request.form.get('phone') or "").strip()
        bio = (request.form.get('bio') or "").strip()

        if not username or not email:
            flash("Username and email are required.", "danger")
            return redirect(url_for('main.edit_profile'))

        if Doctor.query.filter(Doctor.id != current_user.id, Doctor.username == username).first():
            flash("Username already taken.", "danger")
            return redirect(url_for('main.edit_profile'))

        if Doctor.query.filter(Doctor.id != current_user.id, func.lower(Doctor.email) == email).first():
            flash("Email already in use.", "danger")
            return redirect(url_for('main.edit_profile'))

        # remove doctor photo
        if request.form.get('remove_doctor_photo') == 'on':
            if getattr(current_user, 'photo_path', None):
                _delete_static_file(current_user.photo_path)
            current_user.photo_path = None

        # upload new doctor photo
        photo = request.files.get('photo')
        if photo and photo.filename:
            if getattr(current_user, 'photo_path', None):
                _delete_static_file(current_user.photo_path)

            filename = secure_filename(photo.filename)
            upload_folder = os.path.join('app', 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            photo.save(os.path.join(upload_folder, filename))
            current_user.photo_path = f"uploads/{filename}"

        current_user.username = username
        current_user.email = email
        current_user.specialty = specialty or None
        current_user.phone = phone or None
        current_user.bio = bio or None

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('main.profile'))

    return render_template('edit_profile.html')


@main.route('/profile/password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password') or ""
        new_password = request.form.get('new_password') or ""

        if not current_user.check_password(current_password):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for('main.change_password'))

        if len(new_password) < 6:
            flash("New password must be at least 6 characters.", "danger")
            return redirect(url_for('main.change_password'))

        current_user.set_password(new_password)
        db.session.commit()

        flash("Password updated successfully!", "success")
        return redirect(url_for('main.profile'))

    return render_template('change_password.html')