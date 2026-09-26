from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import User, Election, Candidate, Vote, VoterEligibility
from app import db
from functools import wraps
from app.services.time import india_now_naive

voter_bp = Blueprint('voter', __name__)

def voter_login_required(f):
    """Decorator to require voter login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'voter_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('voter.voter_login'))
        return f(*args, **kwargs)
    return decorated_function

@voter_bp.route('/vote')
def vote_entry():
    """Main voter entry point - choose login method"""
    return render_template('voter/entry.html')

@voter_bp.route('/voter/login', methods=['GET', 'POST'])
def voter_login():
    """Voter login using phone number"""
    if request.method == 'POST':
        phone = request.form.get('phone')
        
        if not phone:
            flash('Please provide your phone number.', 'error')
            return render_template('voter/login.html')
        
        voter = User.query.filter_by(phone=phone).first()
        
        if voter:
            session['voter_id'] = voter.id
            session['voter_name'] = voter.name
            flash('Login successful!', 'success')
            return redirect(url_for('voter.voter_dashboard'))
        else:
            flash('Phone number not found. Please contact administrator.', 'error')
    
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
        Election.status.in_(['OPEN', 'SCHEDULED']),
        Election.start_time <= now,
        Election.end_time >= now
    ).all()
    
    return render_template('voter/dashboard.html', elections=eligible_elections)

@voter_bp.route('/voter/logout')
def voter_logout():
    """Voter logout"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('voter.vote_entry'))
