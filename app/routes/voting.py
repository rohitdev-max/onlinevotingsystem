from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import Election, Candidate, Vote, VoterEligibility, User
from app import db
from datetime import datetime

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
    candidates = election.candidates
    
    # Check if user is logged in
    voter_id = session.get('voter_id')
    can_vote = False
    has_voted = False
    
    if voter_id:
        eligibility = VoterEligibility.query.filter_by(
            election_id=election.id,
            voter_id=voter_id
        ).first()
        
        if eligibility and eligibility.verified and not eligibility.has_voted:
            can_vote = True
        elif eligibility and eligibility.has_voted:
            has_voted = True
    
    return render_template('voting/election.html', 
                         election=election, 
                         candidates=candidates,
                         can_vote=can_vote,
                         has_voted=has_voted)

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
        vote = Vote(
            election_id=election.id,
            candidate_id=candidate_id
        )
        db.session.add(vote)
        
        # Mark voter as having voted
        eligibility.has_voted = True
        eligibility.voted_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Your vote has been cast successfully! Thank you for participating.', 'success')
        return redirect(url_for('voting.vote_confirmation', public_code=public_code))
        
    except Exception as e:
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
