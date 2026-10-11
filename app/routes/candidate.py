from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.models import Candidate, Election
from app.routes.admin import _save_face_image, _save_kyc_document
from app.services.time import india_now_naive

candidate_bp = Blueprint('candidate', __name__)


def validate_phone_number(phone):
    """Ensure a phone number contains only 10 digits."""
    return phone.isdigit() and len(phone) == 10


@candidate_bp.route('/candidate/register', methods=['GET', 'POST'])
def candidate_register():
    """Accept candidate applications, with an optional upcoming election."""
    now = india_now_naive()
    elections = Election.query.filter(
        Election.status == 'SCHEDULED',
        Election.start_time > now,
        Election.end_time > now,
    ).order_by(Election.start_time.asc()).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        identity_reference = request.form.get('identity_reference', '').strip()
        description = request.form.get('description', '').strip()
        election_id = request.form.get('election_id', '')
        kyc_document = request.files.get('kyc_document')
        face_image = request.files.get('face_image')

        if (not name or not phone or not identity_reference or
                not kyc_document or not kyc_document.filename or
                not face_image or not face_image.filename or
                request.form.get('face_capture_method') != 'camera'):
            flash('Complete all required fields and capture a live face image.', 'error')
            return render_template('candidate/register.html', elections=elections)

        if not validate_phone_number(phone):
            flash('Phone number must contain exactly 10 digits.', 'error')
            return render_template('candidate/register.html', elections=elections)

        election = None
        if election_id:
            election = next((item for item in elections if str(item.id) == election_id), None)
        if election_id and not election:
            flash('Choose an upcoming election that is accepting candidate applications.', 'error')
            return render_template('candidate/register.html', elections=elections)

        if Candidate.query.filter_by(identity_reference=identity_reference).first():
            flash('A candidate with this identity reference already exists.', 'error')
            return render_template('candidate/register.html', elections=elections)

        try:
            kyc_document_filename = _save_kyc_document(kyc_document)
            face_image_filename = _save_face_image(face_image)
        except ValueError as error:
            flash(str(error), 'error')
            return render_template('candidate/register.html', elections=elections)

        candidate = Candidate(
            name=name,
            phone=phone,
            identity_reference=identity_reference,
            description=description,
            kyc_document_filename=kyc_document_filename,
            face_image_filename=face_image_filename,
            kyc_submitted_at=datetime.utcnow(),
        )
        if election:
            candidate.elections.append(election)
        db.session.add(candidate)
        db.session.commit()

        if election:
            flash('Your application was submitted and is awaiting administrator verification.', 'success')
        else:
            flash('Your registration was submitted for administrator verification. An administrator can assign you to an election later.', 'success')
        return redirect(url_for('candidate.candidate_register'))

    return render_template('candidate/register.html', elections=elections)