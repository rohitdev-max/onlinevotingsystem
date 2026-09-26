from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, send_from_directory
from app.models import Admin, Election, Candidate, User, Vote, VoterEligibility, AuditLog
from app.services.audit import log_audit_event
from app.routes.auth import login_required
from app import db
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import uuid

admin_bp = Blueprint('admin', __name__)
ALLOWED_CANDIDATE_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
ALLOWED_KYC_DOCUMENT_EXTENSIONS = {'jpg', 'jpeg', 'png', 'pdf'}
ALLOWED_FACE_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png'}

def _save_candidate_photo(photo_file):
    """Validate and save an uploaded candidate image."""
    filename = secure_filename(photo_file.filename or '')
    if not filename or '.' not in filename:
        raise ValueError('Please select a valid image file.')

    extension = filename.rsplit('.', 1)[1].lower()
    if extension not in ALLOWED_CANDIDATE_IMAGE_EXTENSIONS:
        raise ValueError('Candidate images must be JPG, JPEG, PNG, GIF, or WEBP files.')

    upload_directory = os.path.join(current_app.static_folder, 'uploads', 'candidates')
    os.makedirs(upload_directory, exist_ok=True)
    saved_filename = f'{uuid.uuid4().hex}.{extension}'
    photo_file.save(os.path.join(upload_directory, saved_filename))
    return url_for('static', filename=f'uploads/candidates/{saved_filename}')

def _delete_candidate_photo(photo_url):
    """Delete an image previously saved by this application."""
    prefix = '/static/uploads/candidates/'
    if not photo_url or not photo_url.startswith(prefix):
        return
    filename = photo_url[len(prefix):]
    photo_path = os.path.join(current_app.static_folder, 'uploads', 'candidates', filename)
    if os.path.isfile(photo_path):
        os.remove(photo_path)

def _save_kyc_document(document_file):
    """Store a KYC document outside the public static directory."""
    filename = secure_filename(document_file.filename or '')
    if not filename or '.' not in filename:
        raise ValueError('Please select a valid KYC document.')

    extension = filename.rsplit('.', 1)[1].lower()
    if extension not in ALLOWED_KYC_DOCUMENT_EXTENSIONS:
        raise ValueError('KYC documents must be JPG, JPEG, PNG, or PDF files.')

    upload_directory = os.path.join(current_app.instance_path, 'kyc')
    os.makedirs(upload_directory, exist_ok=True)
    saved_filename = f'{uuid.uuid4().hex}.{extension}'
    document_file.save(os.path.join(upload_directory, saved_filename))
    return saved_filename

def _save_face_image(face_file):
    """Store a face image outside the public static directory."""
    filename = secure_filename(face_file.filename or '')
    if not filename or '.' not in filename:
        raise ValueError('Please select a valid face image.')

    extension = filename.rsplit('.', 1)[1].lower()
    if extension not in ALLOWED_FACE_IMAGE_EXTENSIONS:
        raise ValueError('Face images must be JPG, JPEG, or PNG files.')

    upload_directory = os.path.join(current_app.instance_path, 'faces')
    os.makedirs(upload_directory, exist_ok=True)
    saved_filename = f'{uuid.uuid4().hex}.{extension}'
    face_file.save(os.path.join(upload_directory, saved_filename))
    return saved_filename

def _set_kyc_review(entity, status, reason=None):
    entity.kyc_status = status
    entity.kyc_rejection_reason = reason if status == 'REJECTED' else None
    entity.kyc_verified_at = datetime.utcnow() if status == 'VERIFIED' else None
    entity.face_auth_status = status
    entity.face_verified_at = datetime.utcnow() if status == 'VERIFIED' else None

@admin_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard with statistics."""
    stats = {
        'total_elections': Election.query.count(),
        'active_elections': Election.query.filter_by(status='OPEN').count(),
        'total_voters': User.query.count(),
        'total_votes': Vote.query.count()
    }
    
    recent_elections = Election.query.order_by(Election.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', stats=stats, recent_elections=recent_elections)

@admin_bp.route('/admin/elections')
@login_required
def elections():
    """Manage elections page."""
    elections = Election.query.order_by(Election.created_at.desc()).all()
    return render_template('admin/elections.html', elections=elections)

@admin_bp.route('/admin/elections/<int:election_id>/clear-votes', methods=['POST'])
@login_required
def clear_election_votes(election_id):
    """Clear every ballot in an election and reset voter eligibility."""
    election = Election.query.get_or_404(election_id)
    vote_count = Vote.query.filter_by(election_id=election.id).count()

    try:
        Vote.query.filter_by(election_id=election.id).delete(synchronize_session=False)
        VoterEligibility.query.filter_by(election_id=election.id).update(
            {
                'has_voted': False,
                'voted_at': None,
            },
            synchronize_session=False,
        )
        log_audit_event(
            admin_id=session.get('admin_id'),
            action='CLEAR_ELECTION_VOTES',
            target_type='ELECTION',
            target_id=election.id,
            details=f'Cleared {vote_count} vote(s) from election: {election.title}'
        )
        flash(f'Cleared {vote_count} vote(s). Eligible voters can vote again.', 'success')
    except Exception:
        db.session.rollback()
        flash('Could not clear the election votes.', 'error')

    return redirect(url_for('admin.elections'))

@admin_bp.route('/admin/elections/<int:election_id>')
@login_required
def view_election(election_id):
    """View election details and participation information."""
    election = Election.query.get_or_404(election_id)
    return render_template('admin/view_election.html', election=election)

@admin_bp.route('/admin/elections/<int:election_id>/status', methods=['POST'])
@login_required
def update_election_status(election_id):
    """Open or close an election from the admin panel."""
    election = Election.query.get_or_404(election_id)
    new_status = request.form.get('status')

    if new_status not in {'OPEN', 'CLOSED'}:
        flash('Invalid election status.', 'error')
        return redirect(url_for('admin.elections'))

    if new_status == 'OPEN' and not election.candidates:
        flash('Add at least one candidate before opening the election.', 'error')
        return redirect(url_for('admin.elections'))

    election.status = new_status
    db.session.commit()
    log_audit_event(
        admin_id=session.get('admin_id'),
        action=f'{new_status}_ELECTION',
        target_type='ELECTION',
        target_id=election.id,
        details=f'{new_status.title()} election: {election.title}'
    )
    flash(f'Election {new_status.lower()} successfully.', 'success')
    return redirect(url_for('admin.elections'))

@admin_bp.route('/admin/elections/<int:election_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_election(election_id):
    """Edit an election before voting begins."""
    election = Election.query.get_or_404(election_id)

    if not election.can_be_modified():
        flash('Only draft or scheduled elections can be edited.', 'error')
        return redirect(url_for('admin.view_election', election_id=election.id))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        start_time = request.form.get('start_time', '')
        end_time = request.form.get('end_time', '')

        if not title or not start_time or not end_time:
            flash('Please fill in all required fields.', 'error')
            return render_template('admin/edit_election.html', election=election)

        try:
            parsed_start_time = datetime.fromisoformat(start_time)
            parsed_end_time = datetime.fromisoformat(end_time)
        except ValueError:
            flash('Please provide valid start and end times.', 'error')
            return render_template('admin/edit_election.html', election=election)

        if parsed_end_time <= parsed_start_time:
            flash('The end time must be after the start time.', 'error')
            return render_template('admin/edit_election.html', election=election)

        election.title = title
        election.description = description
        election.start_time = parsed_start_time
        election.end_time = parsed_end_time
        db.session.commit()

        log_audit_event(
            admin_id=session.get('admin_id'),
            action='EDIT_ELECTION',
            target_type='ELECTION',
            target_id=election.id,
            details=f'Edited election: {title}'
        )
        flash('Election updated successfully!', 'success')
        return redirect(url_for('admin.view_election', election_id=election.id))

    return render_template('admin/edit_election.html', election=election)

@admin_bp.route('/admin/elections/<int:election_id>/delete', methods=['POST'])
@login_required
def delete_election(election_id):
    """Delete an election and all data belonging to it."""
    election = Election.query.get_or_404(election_id)
    election_title = election.title

    try:
        Vote.query.filter_by(election_id=election.id).delete(synchronize_session=False)
        VoterEligibility.query.filter_by(election_id=election.id).delete(synchronize_session=False)
        db.session.delete(election)

        log_audit_event(
            admin_id=session.get('admin_id'),
            action='DELETE_ELECTION',
            target_type='ELECTION',
            target_id=election_id,
            details=f'Deleted election: {election_title}'
        )
        flash(f'Election "{election_title}" was deleted.', 'success')
    except Exception:
        db.session.rollback()
        flash('Could not delete the election.', 'error')

    return redirect(url_for('admin.elections'))

@admin_bp.route('/admin/elections/create', methods=['GET', 'POST'])
@login_required
def create_election():
    """Create new election page."""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
        if not title or not start_time or not end_time:
            flash('Please fill in all required fields.', 'error')
            return render_template('admin/create_election.html')
        
        try:
            parsed_start_time = datetime.fromisoformat(start_time)
            parsed_end_time = datetime.fromisoformat(end_time)
        except ValueError:
            flash('Please provide valid start and end times.', 'error')
            return render_template('admin/create_election.html')

        if parsed_end_time <= parsed_start_time:
            flash('The end time must be after the start time.', 'error')
            return render_template('admin/create_election.html')

        public_code = ''.join([str(datetime.now().timestamp()).replace('.', '')[-6:]])
        
        election = Election(
            title=title,
            description=description,
            start_time=parsed_start_time,
            end_time=parsed_end_time,
            public_code=public_code,
            status='SCHEDULED',
            created_by=session.get('admin_id')
        )
        
        db.session.add(election)
        db.session.commit()
        
        log_audit_event(
            admin_id=session.get('admin_id'),
            action='CREATE_ELECTION',
            target_type='ELECTION',
            target_id=election.id,
            details=f'Created election: {title}'
        )
        
        flash('Election created successfully!', 'success')
        return redirect(url_for('admin.elections'))
    
    return render_template('admin/create_election.html')

@admin_bp.route('/admin/candidates')
@login_required
def candidates():
    """Manage candidates page."""
    candidates = Candidate.query.order_by(Candidate.created_at.desc()).all()
    return render_template('admin/candidates.html', candidates=candidates)

@admin_bp.route('/admin/candidates/add', methods=['GET', 'POST'])
@login_required
def add_candidate():
    """Add a candidate and optionally assign the candidate to an election."""
    elections = Election.query.order_by(Election.created_at.desc()).all()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        identity_reference = request.form.get('identity_reference', '').strip()
        description = request.form.get('description', '').strip()
        photo_file = request.files.get('photo')
        kyc_document = request.files.get('kyc_document')
        face_image = request.files.get('face_image')
        face_capture_method = request.form.get('face_capture_method')
        election_id = request.form.get('election_id')

        if (not name or not phone or not identity_reference or
                not kyc_document or not kyc_document.filename or
            not face_image or not face_image.filename or
            face_capture_method != 'camera'):
            flash('Name, phone, identity reference, KYC document, and face image are required.', 'error')
            return render_template('admin/add_candidate.html', elections=elections)

        if Candidate.query.filter_by(identity_reference=identity_reference).first():
            flash('A candidate with this identity reference already exists.', 'error')
            return render_template('admin/add_candidate.html', elections=elections)

        photo = None
        if photo_file and photo_file.filename:
            try:
                photo = _save_candidate_photo(photo_file)
            except ValueError as error:
                flash(str(error), 'error')
                return render_template('admin/add_candidate.html', elections=elections)

        try:
            kyc_document_filename = _save_kyc_document(kyc_document)
            face_image_filename = _save_face_image(face_image)
        except ValueError as error:
            flash(str(error), 'error')
            return render_template('admin/add_candidate.html', elections=elections)

        candidate = Candidate(
            name=name,
            phone=phone,
            identity_reference=identity_reference,
            description=description,
            photo=photo,
            kyc_document_filename=kyc_document_filename,
            face_image_filename=face_image_filename,
            kyc_submitted_at=datetime.utcnow(),
        )
        if election_id:
            election = Election.query.get_or_404(election_id)
            candidate.elections.append(election)
        db.session.add(candidate)
        db.session.commit()
        log_audit_event(
            admin_id=session.get('admin_id'),
            action='ADD_CANDIDATE',
            target_type='CANDIDATE',
            target_id=candidate.id,
            details=f'Added candidate: {name}'
        )
        flash('Candidate added successfully!', 'success')
        return redirect(url_for('admin.candidates'))

    return render_template('admin/add_candidate.html', elections=elections)

@admin_bp.route('/admin/candidates/<int:candidate_id>')
@login_required
def view_candidate(candidate_id):
    """View candidate details and election vote totals."""
    candidate = Candidate.query.get_or_404(candidate_id)
    return render_template('admin/view_candidate.html', candidate=candidate)

@admin_bp.route('/admin/candidates/<int:candidate_id>/kyc', methods=['POST'])
@login_required
def review_candidate_kyc(candidate_id):
    """Approve or reject a candidate's KYC submission."""
    candidate = Candidate.query.get_or_404(candidate_id)
    status = request.form.get('status')
    reason = request.form.get('reason', '').strip()
    if status not in {'VERIFIED', 'REJECTED'} or status == 'REJECTED' and not reason:
        flash('Choose a valid KYC decision and provide a rejection reason when rejecting.', 'error')
        return redirect(url_for('admin.view_candidate', candidate_id=candidate.id))
    _set_kyc_review(candidate, status, reason)
    db.session.commit()
    log_audit_event(
        admin_id=session.get('admin_id'),
        action=f'{status}_CANDIDATE_KYC',
        target_type='CANDIDATE',
        target_id=candidate.id,
        details=f'{status.title()} KYC for candidate: {candidate.name}'
    )
    flash(f'Candidate KYC {status.lower()} successfully.', 'success')
    return redirect(url_for('admin.view_candidate', candidate_id=candidate.id))

@admin_bp.route('/admin/kyc/<filename>')
@login_required
def download_kyc_document(filename):
    """Download a KYC document only for an authenticated administrator."""
    return send_from_directory(
        os.path.join(current_app.instance_path, 'kyc'),
        filename,
        as_attachment=True,
    )

@admin_bp.route('/admin/faces/<filename>')
@login_required
def download_face_image(filename):
    """Download a face image only for an authenticated administrator."""
    return send_from_directory(
        os.path.join(current_app.instance_path, 'faces'),
        filename,
        as_attachment=True,
    )

@admin_bp.route('/admin/candidates/<int:candidate_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_candidate(candidate_id):
    """Edit candidate details and election assignments."""
    candidate = Candidate.query.get_or_404(candidate_id)
    elections = Election.query.order_by(Election.created_at.desc()).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        photo_file = request.files.get('photo')
        election_ids = request.form.getlist('election_ids')

        if not name:
            flash('Candidate name is required.', 'error')
            return render_template('admin/edit_candidate.html', candidate=candidate, elections=elections)

        candidate.name = name
        candidate.description = description
        if request.form.get('remove_photo') == 'on':
            _delete_candidate_photo(candidate.photo)
            candidate.photo = None
        if photo_file and photo_file.filename:
            try:
                new_photo = _save_candidate_photo(photo_file)
            except ValueError as error:
                flash(str(error), 'error')
                return render_template('admin/edit_candidate.html', candidate=candidate, elections=elections)
            _delete_candidate_photo(candidate.photo)
            candidate.photo = new_photo
        candidate.elections = [
            election for election in elections if str(election.id) in election_ids
        ]
        db.session.commit()
        log_audit_event(
            admin_id=session.get('admin_id'),
            action='EDIT_CANDIDATE',
            target_type='CANDIDATE',
            target_id=candidate.id,
            details=f'Edited candidate: {name}'
        )
        flash('Candidate updated successfully!', 'success')
        return redirect(url_for('admin.view_candidate', candidate_id=candidate.id))

    return render_template('admin/edit_candidate.html', candidate=candidate, elections=elections)

@admin_bp.route('/admin/candidates/<int:candidate_id>/delete', methods=['POST'])
@login_required
def delete_candidate(candidate_id):
    """Delete a candidate only when no ballot references the candidate."""
    candidate = Candidate.query.get_or_404(candidate_id)
    if Vote.query.filter_by(candidate_id=candidate.id).first():
        flash('This candidate cannot be deleted because votes have been cast for them.', 'error')
        return redirect(url_for('admin.candidates'))

    candidate_name = candidate.name
    _delete_candidate_photo(candidate.photo)
    db.session.delete(candidate)
    db.session.commit()
    log_audit_event(
        admin_id=session.get('admin_id'),
        action='DELETE_CANDIDATE',
        target_type='CANDIDATE',
        target_id=candidate_id,
        details=f'Deleted candidate: {candidate_name}'
    )
    flash('Candidate deleted successfully!', 'success')
    return redirect(url_for('admin.candidates'))

@admin_bp.route('/admin/voters')
@login_required
def voters():
    """Manage voters page."""
    voters = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/voters.html', voters=voters)

@admin_bp.route('/admin/voters/<int:voter_id>')
@login_required
def view_voter(voter_id):
    """View voter details and election eligibility."""
    voter = User.query.get_or_404(voter_id)
    return render_template('admin/view_voter.html', voter=voter)

@admin_bp.route('/admin/voters/<int:voter_id>/kyc', methods=['POST'])
@login_required
def review_voter_kyc(voter_id):
    """Approve or reject a voter's KYC submission."""
    voter = User.query.get_or_404(voter_id)
    status = request.form.get('status')
    reason = request.form.get('reason', '').strip()
    if status not in {'VERIFIED', 'REJECTED'} or status == 'REJECTED' and not reason:
        flash('Choose a valid KYC decision and provide a rejection reason when rejecting.', 'error')
        return redirect(url_for('admin.view_voter', voter_id=voter.id))
    _set_kyc_review(voter, status, reason)
    db.session.commit()
    log_audit_event(
        admin_id=session.get('admin_id'),
        action=f'{status}_VOTER_KYC',
        target_type='VOTER',
        target_id=voter.id,
        details=f'{status.title()} KYC for voter: {voter.name}'
    )
    flash(f'Voter KYC {status.lower()} successfully.', 'success')
    return redirect(url_for('admin.view_voter', voter_id=voter.id))

@admin_bp.route('/admin/voters/add', methods=['GET', 'POST'])
@login_required
def add_voter():
    """Add new voter page."""
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        identity_reference = request.form.get('identity_reference')
        kyc_document = request.files.get('kyc_document')
        face_image = request.files.get('face_image')
        face_capture_method = request.form.get('face_capture_method')
        
        if (not name or not phone or not identity_reference or
                not kyc_document or not kyc_document.filename or
            not face_image or not face_image.filename or
            face_capture_method != 'camera'):
            flash('Name, phone, identity reference, KYC document, and face image are required.', 'error')
            return render_template('admin/add_voter.html')
        
        # Check if phone number already exists
        existing_voter = User.query.filter_by(phone=phone).first()
        if existing_voter:
            flash('A voter with this phone number already exists.', 'error')
            return render_template('admin/add_voter.html')
        
        # Check if identity reference already exists
        existing_identity = User.query.filter_by(identity_reference=identity_reference).first()
        if existing_identity:
            flash('A voter with this identity reference already exists.', 'error')
            return render_template('admin/add_voter.html')

        try:
            kyc_document_filename = _save_kyc_document(kyc_document)
            face_image_filename = _save_face_image(face_image)
        except ValueError as error:
            flash(str(error), 'error')
            return render_template('admin/add_voter.html')
        
        voter = User(
            name=name,
            phone=phone,
            identity_reference=identity_reference,
            kyc_document_filename=kyc_document_filename,
            face_image_filename=face_image_filename,
            kyc_submitted_at=datetime.utcnow(),
        )
        
        db.session.add(voter)
        db.session.commit()
        
        log_audit_event(
            admin_id=session.get('admin_id'),
            action='ADD_VOTER',
            target_type='VOTER',
            target_id=voter.id,
            details=f'Added voter: {name} ({phone})'
        )
        
        flash('Voter added successfully!', 'success')
        return redirect(url_for('admin.voters'))
    
    return render_template('admin/add_voter.html')

@admin_bp.route('/admin/voters/<int:voter_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_voter(voter_id):
    """Edit voter page."""
    voter = User.query.get_or_404(voter_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        identity_reference = request.form.get('identity_reference')
        
        if not name or not phone or not identity_reference:
            flash('Please fill in all required fields.', 'error')
            return render_template('admin/edit_voter.html', voter=voter)
        
        # Check if phone number is used by another voter
        existing_phone = User.query.filter_by(phone=phone).first()
        if existing_phone and existing_phone.id != voter_id:
            flash('This phone number is already used by another voter.', 'error')
            return render_template('admin/edit_voter.html', voter=voter)
        
        # Check if identity reference is used by another voter
        existing_identity = User.query.filter_by(identity_reference=identity_reference).first()
        if existing_identity and existing_identity.id != voter_id:
            flash('This identity reference is already used by another voter.', 'error')
            return render_template('admin/edit_voter.html', voter=voter)
        
        voter.name = name
        voter.phone = phone
        voter.identity_reference = identity_reference
        
        db.session.commit()
        
        log_audit_event(
            admin_id=session.get('admin_id'),
            action='EDIT_VOTER',
            target_type='VOTER',
            target_id=voter.id,
            details=f'Edited voter: {name} ({phone})'
        )
        
        flash('Voter updated successfully!', 'success')
        return redirect(url_for('admin.voters'))
    
    return render_template('admin/edit_voter.html', voter=voter)

@admin_bp.route('/admin/voters/<int:voter_id>/delete', methods=['POST'])
@login_required
def delete_voter(voter_id):
    """Delete voter."""
    voter = User.query.get_or_404(voter_id)
    
    log_audit_event(
        admin_id=session.get('admin_id'),
        action='DELETE_VOTER',
        target_type='VOTER',
        target_id=voter.id,
        details=f'Deleted voter: {voter.name} ({voter.phone})'
    )
    
    db.session.delete(voter)
    db.session.commit()
    
    flash('Voter deleted successfully!', 'success')
    return redirect(url_for('admin.voters'))

@admin_bp.route('/admin/voters/<int:voter_id>/eligibility', methods=['GET', 'POST'])
@login_required
def manage_voter_eligibility(voter_id):
    """Manage voter eligibility for elections."""
    voter = User.query.get_or_404(voter_id)
    elections = Election.query.all()
    
    if request.method == 'POST':
        election_id = request.form.get('election_id')
        action = request.form.get('action')  # 'add' or 'remove'
        
        if not election_id:
            flash('Please select an election.', 'error')
            return render_template('admin/voter_eligibility.html', voter=voter, elections=elections)
        
        election = Election.query.get_or_404(election_id)
        
        if action == 'add':
            # Check if already eligible
            existing = VoterEligibility.query.filter_by(
                election_id=election_id,
                voter_id=voter_id
            ).first()
            
            if existing:
                flash('Voter is already eligible for this election.', 'warning')
            else:
                eligibility = VoterEligibility(
                    election_id=election_id,
                    voter_id=voter_id,
                    verified=False,
                    has_voted=False
                )
                db.session.add(eligibility)
                db.session.commit()
                
                log_audit_event(
                    admin_id=session.get('admin_id'),
                    action='ADD_VOTER_ELIGIBILITY',
                    target_type='VOTER_ELIGIBILITY',
                    target_id=eligibility.id,
                    details=f'Added {voter.name} to {election.title}'
                )
                
                flash('Voter made eligible for election successfully!', 'success')
        
        elif action == 'remove':
            eligibility = VoterEligibility.query.filter_by(
                election_id=election_id,
                voter_id=voter_id
            ).first()
            
            if eligibility:
                if eligibility.has_voted:
                    flash('Cannot remove voter who has already voted.', 'error')
                else:
                    db.session.delete(eligibility)
                    db.session.commit()
                    
                    log_audit_event(
                        admin_id=session.get('admin_id'),
                        action='REMOVE_VOTER_ELIGIBILITY',
                        target_type='VOTER_ELIGIBILITY',
                        target_id=eligibility.id,
                        details=f'Removed {voter.name} from {election.title}'
                    )
                    
                    flash('Voter removed from election successfully!', 'success')
            else:
                flash('Voter is not eligible for this election.', 'warning')
        
        return redirect(url_for('admin.manage_voter_eligibility', voter_id=voter_id))
    
    # Get current eligibility
    eligibility_map = {}
    for election in elections:
        eligibility = VoterEligibility.query.filter_by(
            election_id=election.id,
            voter_id=voter_id
        ).first()
        eligibility_map[election.id] = eligibility
    
    return render_template('admin/voter_eligibility.html', 
                         voter=voter, 
                         elections=elections,
                         eligibility_map=eligibility_map)

@admin_bp.route('/admin/voters/<int:voter_id>/verify/<int:election_id>', methods=['POST'])
@login_required
def verify_voter(voter_id, election_id):
    """Verify voter for election."""
    voter = User.query.get_or_404(voter_id)
    election = Election.query.get_or_404(election_id)
    
    eligibility = VoterEligibility.query.filter_by(
        election_id=election_id,
        voter_id=voter_id
    ).first()
    
    if not eligibility:
        flash('Voter is not eligible for this election.', 'error')
        return redirect(url_for('admin.manage_voter_eligibility', voter_id=voter_id))
    
    eligibility.verified = True
    eligibility.verified_at = datetime.utcnow()
    db.session.commit()
    
    log_audit_event(
        admin_id=session.get('admin_id'),
        action='VERIFY_VOTER',
        target_type='VOTER_ELIGIBILITY',
        target_id=eligibility.id,
        details=f'Verified {voter.name} for {election.title}'
    )
    
    flash('Voter verified successfully!', 'success')
    return redirect(url_for('admin.manage_voter_eligibility', voter_id=voter_id))

@admin_bp.route('/admin/results')
@login_required
def results():
    """View election results page."""
    elections = Election.query.filter(Election.status.in_(['CLOSED', 'RESULTS_PUBLISHED'])).order_by(Election.end_time.desc()).all()
    results_by_election = {
        election.id: _calculate_election_results(election)
        for election in elections
    }
    return render_template(
        'admin/results.html',
        elections=elections,
        results_by_election=results_by_election
    )

def _calculate_election_results(election):
    """Return candidate totals, percentages, and the winner label."""
    total_votes = Vote.query.filter_by(election_id=election.id).count()
    candidate_results = []

    for candidate in election.candidates:
        vote_count = Vote.query.filter_by(
            election_id=election.id,
            candidate_id=candidate.id
        ).count()
        percentage = round((vote_count / total_votes) * 100, 2) if total_votes else 0
        candidate_results.append({
            'candidate': candidate,
            'vote_count': vote_count,
            'percentage': percentage,
        })

    highest_count = max(
        (result['vote_count'] for result in candidate_results),
        default=0
    )
    winners = [
        result['candidate'].name
        for result in candidate_results
        if result['vote_count'] == highest_count and highest_count > 0
    ]

    if not winners:
        winner = 'No votes'
    elif len(winners) == 1:
        winner = winners[0]
    else:
        winner = f"Tie: {', '.join(winners)}"

    return {
        'total_votes': total_votes,
        'winner': winner,
        'candidate_results': sorted(
            candidate_results,
            key=lambda result: result['vote_count'],
            reverse=True
        ),
    }

@admin_bp.route('/admin/results/<int:election_id>')
@login_required
def result_details(election_id):
    """View detailed results for a closed election."""
    election = Election.query.get_or_404(election_id)
    if election.status not in ['CLOSED', 'RESULTS_PUBLISHED']:
        flash('Results are available after the election is closed.', 'warning')
        return redirect(url_for('admin.results'))

    result = _calculate_election_results(election)
    return render_template(
        'admin/result_details.html',
        election=election,
        result=result
    )

@admin_bp.route('/admin/audit')
@login_required
def audit():
    """View audit logs page."""
    audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('admin/audit.html', audit_logs=audit_logs)
