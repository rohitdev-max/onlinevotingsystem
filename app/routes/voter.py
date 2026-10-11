from datetime import datetime, timezone
import re

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import User, Election, VoterEligibility
from app import db
from functools import wraps
from app.services.time import india_now_naive
from app.routes.admin import _save_face_image, _save_kyc_document

voter_bp = Blueprint('voter', __name__)

def validate_phone_number(phone):
    """Ensure a phone number contains only 10 digits."""
    return phone.isdigit() and len(phone) == 10

def validate_password(password):
    """Enforce a minimum length and bcrypt's 72-byte input limit."""
    return len(password) >= 8 and len(password.encode('utf-8')) <= 72

def validate_identity_reference(identity_reference):
    """Accept an Aadhaar number or PAN in its standard format."""
    return bool(
        re.fullmatch(r'[2-9][0-9]{11}', identity_reference) or
        re.fullmatch(r'[A-Z]{5}[0-9]{4}[A-Z]', identity_reference, re.IGNORECASE)
    )

def voter_login_required(f):
    """Decorator to require voter login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        voter_id = session.get('voter_id')
        voter = db.session.get(User, voter_id) if voter_id else None
        if not voter:
            session.clear()
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('voter.voter_login'))
        if voter.kyc_status != 'VERIFIED' or voter.face_auth_status != 'VERIFIED':
            session.clear()
            flash('Your registration must be verified before you can access voter features.', 'warning')
            return redirect(url_for('voter.voter_login'))
        return f(*args, **kwargs)
    return decorated_function

@voter_bp.route('/vote')
def vote_entry():
    """Main voter entry point - choose login method"""
    return render_template('voter/entry.html')

@voter_bp.route('/voter/register', methods=['GET', 'POST'])
def voter_register():
    """Allow voters to submit their own registration for review."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        identity_reference = request.form.get('identity_reference', '').strip()
        password = request.form.get('password', '')
        password_confirmation = request.form.get('password_confirmation', '')
        kyc_document = request.files.get('kyc_document')
        face_image = request.files.get('face_image')

        if (not name or not phone or not identity_reference or not password or
                not kyc_document or not kyc_document.filename or
                not face_image or not face_image.filename or
                request.form.get('face_capture_method') != 'camera'):
            flash('Name, phone, password, identity reference, KYC document, and a live face capture are required.', 'error')
            return render_template('voter/register.html')

        if not validate_password(password):
            flash('Password must be at least 8 characters and no more than 72 bytes.', 'error')
            return render_template('voter/register.html')

        if password != password_confirmation:
            flash('Passwords do not match.', 'error')
            return render_template('voter/register.html')

        if not validate_phone_number(phone):
            flash('Phone number must contain exactly 10 digits.', 'error')
            return render_template('voter/register.html')

        if not validate_identity_reference(identity_reference):
            flash('Identity reference must be a 12-digit Aadhaar number or a PAN in the format ABCDE1234F.', 'error')
            return render_template('voter/register.html')

        if User.query.filter_by(phone=phone).first():
            flash('A voter with this phone number already exists.', 'error')
            return render_template('voter/register.html')

        if User.query.filter_by(identity_reference=identity_reference).first():
            flash('A voter with this identity reference already exists.', 'error')
            return render_template('voter/register.html')

        try:
            kyc_document_filename = _save_kyc_document(kyc_document)
            face_image_filename = _save_face_image(face_image)
        except ValueError as error:
            flash(str(error), 'error')
            return render_template('voter/register.html')

        voter = User(
            name=name,
            phone=phone,
            identity_reference=identity_reference,
            kyc_document_filename=kyc_document_filename,
            face_image_filename=face_image_filename,
            kyc_submitted_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        voter.set_password(password)
        db.session.add(voter)
        db.session.commit()

        flash('Registration submitted. You can log in after an administrator verifies your details.', 'info')
        return redirect(url_for('voter.voter_login'))

    return render_template('voter/register.html')

@voter_bp.route('/voter/login', methods=['GET', 'POST'])
def voter_login():
    """Voter login using a registered phone number and password."""
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        if not phone or not password:
            flash('Please provide both your phone number and password.', 'error')
            return render_template('voter/login.html')

        if not validate_phone_number(phone):
            flash('Phone number must contain exactly 10 digits.', 'error')
            return render_template('voter/login.html')

        voter = User.query.filter_by(phone=phone).first()
        if not voter or not voter.check_password(password):
            flash('Invalid phone number or password.', 'error')
            return render_template('voter/login.html')

        if voter.kyc_status != 'VERIFIED' or voter.face_auth_status != 'VERIFIED':
            flash('Your registration is not verified yet. Please contact an administrator for help.', 'warning')
            return render_template('voter/login.html')

        session.clear()
        session['voter_id'] = voter.id
        session['voter_name'] = voter.name
        flash('Login successful!', 'success')
        return redirect(url_for('voter.voter_dashboard'))

    return render_template('voter/login.html')

@voter_bp.route('/voter/dashboard')
@voter_login_required
def voter_dashboard():
    """Voter dashboard showing eligible elections"""
    if 'voter_id' not in session:
        flash('Please login to access this page.', 'warning')
        return redirect(url_for('voter.voter_login'))
    
    voter_id = session['voter_id']
    
    # Get elections where this voter is eligible
    now = india_now_naive()
    eligible_elections = db.session.query(Election).join(
        VoterEligibility, VoterEligibility.election_id == Election.id
    ).filter(
        VoterEligibility.voter_id == voter_id,
        VoterEligibility.verified.is_(True),
        Election.status == 'OPEN',
        Election.start_time <= now,
        Election.end_time >= now
    ).all()
    
    return render_template('voter/dashboard.html', elections=eligible_elections)

@voter_bp.route('/voter/profile', methods=['GET', 'POST'])
@voter_login_required
def voter_profile():
    """Allow a voter to update their own name and phone number."""
    voter = User.query.filter_by(id=session['voter_id']).first_or_404()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        face_image = request.files.get('face_image')

        if (not name or not phone or not face_image or not face_image.filename or
                request.form.get('face_capture_method') != 'camera'):
            flash('Please provide your name and phone number and capture a live face image.', 'error')
            return render_template('voter/profile.html', voter=voter)

        if not validate_phone_number(phone):
            flash('Phone number must contain exactly 10 digits.', 'error')
            return render_template('voter/profile.html', voter=voter)

        existing_phone = User.query.filter_by(phone=phone).first()
        if existing_phone and existing_phone.id != voter.id:
            flash('This phone number is already used by another voter.', 'error')
            return render_template('voter/profile.html', voter=voter)

        try:
            face_image_filename = _save_face_image(face_image)
        except ValueError as error:
            flash(str(error), 'error')
            return render_template('voter/profile.html', voter=voter)

        voter.name = name
        voter.phone = phone
        voter.face_image_filename = face_image_filename
        voter.kyc_status = 'PENDING'
        voter.kyc_verified_at = None
        voter.kyc_rejection_reason = None
        voter.face_auth_status = 'PENDING'
        voter.face_verified_at = None
        db.session.commit()

        session.clear()
        flash('Profile updated. An administrator must verify your changes before you can log in and vote.', 'info')
        return redirect(url_for('voter.voter_login'))

    return render_template('voter/profile.html', voter=voter)

@voter_bp.route('/voter/logout')
def voter_logout():
    """Voter logout"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('voter.vote_entry'))
