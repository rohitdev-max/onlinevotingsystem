from datetime import datetime
from app import db
from app.services.time import india_now_naive

class Election(db.Model):
    """Election model for voting events."""
    __tablename__ = 'elections'
    
    id = db.Column(db.Integer, primary_key=True)
    public_code = db.Column(db.String(16), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(
        db.Enum('DRAFT', 'SCHEDULED', 'OPEN', 'CLOSED', 'RESULTS_PUBLISHED'),
        nullable=False,
        default='DRAFT',
        index=True
    )
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    created_by = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    
    # Relationships
    candidates = db.relationship('Candidate', secondary='election_candidates', backref='elections')
    voter_eligibilities = db.relationship('VoterEligibility', backref='election', lazy=True)
    votes = db.relationship('Vote', backref='election', lazy=True)
    
    def is_open(self):
        """Check if election is currently open for voting."""
        now = india_now_naive()
        return (
            self.status == 'OPEN' and
            self.start_time <= now and
            self.end_time >= now
        )
    
    def can_be_modified(self):
        """Check if election can be modified (only in DRAFT or SCHEDULED status)."""
        return self.status in ['DRAFT', 'SCHEDULED']
    
    def get_voter_count(self):
        """Get total eligible voters for this election."""
        return len(self.voter_eligibilities)
    
    def get_verified_count(self):
        """Get count of verified voters."""
        return sum(1 for ve in self.voter_eligibilities if ve.verified)
    
    def get_votes_cast(self):
        """Get count of votes cast."""
        return len(self.votes)
    
    def get_turnout_percentage(self):
        """Calculate turnout percentage."""
        total = self.get_voter_count()
        if total == 0:
            return 0
        return round((self.get_votes_cast() / total) * 100, 2)
    
    def __repr__(self):
        return f'<Election {self.title}>'
