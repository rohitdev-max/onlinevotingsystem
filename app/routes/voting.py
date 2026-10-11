from flask import Blueprint, jsonify, render_template, request, redirect, url_for, session, flash
from app.models import AuditLog, Election, Candidate, Vote, VoterEligibility, User
from app import db
from datetime import datetime, timezone
from app.services.live_election import get_live_election_stats
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError

voting_bp = Blueprint('voting', __name__)

@voting_bp.route('/election/code', methods=['GET', 'POST'])
def election_code_entry():
    """Enter election code to access voting"""
    if request.method == 'POST':
        public_code = request.form.get('public_code')
        
        if not public_code:
            flash('Please enter an election code.', 'error')
            return render_template('voting/code_entry.html')
        
        election = Election.query.filter_by(public_code=public_code).first()
        
        if election:
            return redirect(url_for('voting.election_page', public_code=public_code))
        else:
            flash('Invalid election code. Please check and try again.', 'error')
    
    return render_template('voting/code_entry.html')

@voting_bp.route('/election/<public_code>')
def election_page(public_code):
    """Election voting page"""
    election = Election.query.filter_by(public_code=public_code).first()
    
    if not election:
        flash('Election not found.', 'error')
        return redirect(url_for('voter.vote_entry'))
    
    # Get candidates for this election
    candidates = [
        candidate for candidate in election.candidates
        if candidate.kyc_status == 'VERIFIED' and candidate.face_auth_status == 'VERIFIED'
    ]
    
    # Check if user is logged in
    voter_id = session.get('voter_id')
    voter = db.session.get(User, voter_id) if voter_id else None
    can_vote = False
    has_voted = False
    can_view_stats = False
    
    if voter and voter.kyc_status == 'VERIFIED' and voter.face_auth_status == 'VERIFIED':
        eligibility = VoterEligibility.query.filter_by(
            election_id=election.id,
            voter_id=voter_id
        ).first()
        
        can_view_stats = bool(eligibility and eligibility.verified)
        if eligibility and eligibility.verified and not eligibility.has_voted and election.is_open():
            can_vote = True
        elif eligibility and eligibility.has_voted:
            has_voted = True
    
    return render_template('voting/election.html', 
                         election=election, 
                         candidates=candidates,
                         can_vote=can_vote,
                         has_voted=has_voted,
                         can_view_stats=can_view_stats)


@voting_bp.route('/election/<public_code>/live-stats')
def election_live_stats(public_code):
    election = Election.query.filter_by(public_code=public_code).first_or_404()
    voter_id = session.get('voter_id')
    voter = db.session.get(User, voter_id) if voter_id else None
    if not voter or voter.kyc_status != 'VERIFIED' or voter.face_auth_status != 'VERIFIED':
        return jsonify({'error': 'Voter authentication is required.'}), 401

    eligibility = VoterEligibility.query.filter_by(
        election_id=election.id,
        voter_id=voter.id,
        verified=True,
    ).first()
    if not eligibility:
        return jsonify({'error': 'Verified election eligibility is required.'}), 403

    response = jsonify(get_live_election_stats(election))
    response.headers['Cache-Control'] = 'no-store'
    return response

@voting_bp.route('/election/<public_code>/vote', methods=['POST'])
def cast_vote(public_code):
    """Cast a vote in an election"""
    if 'voter_id' not in session:
        flash('Please login to vote.', 'warning')
        return redirect(url_for('voter.voter_login'))
    
    election = Election.query.filter_by(public_code=public_code).first()
    if not election:
        flash('Election not found.', 'error')
        return redirect(url_for('voter.vote_entry'))
    
    candidate_id = request.form.get('candidate_id')
    
    if not candidate_id:
        flash('Please select a candidate to vote for.', 'error')
        return redirect(url_for('voting.election_page', public_code=public_code))
    
    voter_id = session['voter_id']
    voter = db.session.get(User, voter_id)
    if not voter or voter.kyc_status != 'VERIFIED' or voter.face_auth_status != 'VERIFIED':
        session.clear()
        flash('Your voter profile must be verified before you can vote.', 'warning')
        return redirect(url_for('voter.voter_login'))
    
    # Check eligibility
    eligibility = VoterEligibility.query.filter_by(
        election_id=election.id,
        voter_id=voter_id
    ).first()
    
    if not eligibility or not eligibility.verified:
        flash('You are not eligible to vote in this election.', 'error')
        return redirect(url_for('voting.election_page', public_code=public_code))
    
    if eligibility.has_voted:
        flash('You have already voted in this election.', 'error')
        return redirect(url_for('voting.election_page', public_code=public_code))
    
    # Check that the selected candidate belongs to this election.
    candidate = Candidate.query.filter(
        Candidate.id == candidate_id,
        Candidate.kyc_status == 'VERIFIED',
        Candidate.face_auth_status == 'VERIFIED',
        Candidate.elections.any(Election.id == election.id)
    ).first()
    if not candidate:
        flash('Please select a valid candidate for this election.', 'error')
        return redirect(url_for('voting.election_page', public_code=public_code))

    # Check if election is open
    if not election.is_open():
        flash('This election is not currently open for voting.', 'error')
        return redirect(url_for('voting.election_page', public_code=public_code))
    
    # Cast the vote
    try:
        claim = db.session.execute(
            update(VoterEligibility)
            .where(
                VoterEligibility.id == eligibility.id,
                VoterEligibility.verified.is_(True),
                VoterEligibility.has_voted.is_(False),
            )
            .values(has_voted=True, voted_at=None)
        )
        if claim.rowcount != 1:
            db.session.rollback()
            flash('You have already voted in this election.', 'error')
            return redirect(url_for('voting.election_page', public_code=public_code))

        current_election = Election.query.filter_by(id=election.id).with_for_update().first()
        if not current_election or not current_election.is_open():
            db.session.rollback()
            flash('This election is not currently open for voting.', 'error')
            return redirect(url_for('voting.election_page', public_code=public_code))

        valid_candidate = Candidate.query.filter(
            Candidate.id == candidate.id,
            Candidate.kyc_status == 'VERIFIED',
            Candidate.face_auth_status == 'VERIFIED',
            Candidate.elections.any(Election.id == current_election.id),
        ).first()
        if not valid_candidate:
            db.session.rollback()
            flash('Please select a valid candidate for this election.', 'error')
            return redirect(url_for('voting.election_page', public_code=public_code))

        vote = Vote(
            election_id=current_election.id,
            candidate_id=valid_candidate.id,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.session.add(vote)
        db.session.add(AuditLog(
            action='ANONYMOUS_VOTE_ACCEPTED',
            target_type='ELECTION',
            target_id=election.id,
            details='Accepted an anonymous ballot.',
        ))
        db.session.commit()
        
        flash('Your vote has been cast successfully! Thank you for participating.', 'success')
        return redirect(url_for('voting.vote_confirmation', public_code=public_code))
        
    except SQLAlchemyError:
        db.session.rollback()
        flash('An error occurred while casting your vote. Please try again.', 'error')
        return redirect(url_for('voting.election_page', public_code=public_code))

@voting_bp.route('/election/<public_code>/confirmation')
def vote_confirmation(public_code):
    """Vote confirmation page"""
    election = Election.query.filter_by(public_code=public_code).first()
    if not election:
        flash('Election not found.', 'error')
        return redirect(url_for('voter.vote_entry'))
    
    return render_template('voting/confirmation.html', election=election)
