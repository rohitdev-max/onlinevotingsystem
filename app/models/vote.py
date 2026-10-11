from app import db

class Vote(db.Model):
    """Vote model for recorded votes.
    
    Important: This table does NOT store voter_id to protect ballot secrecy.
    The voter-candidate relationship is tracked separately in voter_eligibility.
    """
    __tablename__ = 'votes'
    
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id', ondelete='CASCADE'), nullable=False, index=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id', ondelete='RESTRICT'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)
    
    def __repr__(self):
        return f'<Vote {self.id}>'


class VoterEligibility(db.Model):
    """VoterEligibility model tracks which voters are eligible for which elections.
    
    This table enforces one-person-one-vote at the database level through:
    - UNIQUE(election_id, voter_id) constraint
    - has_voted flag that cannot be reset once set
    """
    __tablename__ = 'voter_eligibility'
    
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id', ondelete='CASCADE'), nullable=False, index=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    verified = db.Column(db.Boolean, default=False)
    has_voted = db.Column(db.Boolean, default=False, index=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    voted_at = db.Column(db.DateTime, nullable=True)
    
    # Unique constraint ensures one voter cannot be registered twice for same election
    __table_args__ = (
        db.UniqueConstraint('election_id', 'voter_id', name='unique_election_voter'),
    )
    
    def can_vote(self):
        """Check if voter can cast a vote."""
        return self.verified and not self.has_voted
    
    def mark_as_voted(self):
        """Mark voter as having voted. This is irreversible."""
        if self.has_voted:
            raise ValueError("Voter has already voted")
        self.has_voted = True
        self.voted_at = None
    
    def __repr__(self):
        return f'<VoterEligibility voter_id={self.voter_id} election_id={self.election_id}>'


class AuditLog(db.Model):
    """AuditLog model records security-sensitive events.
    
    Never logs:
    - Passwords
    - OTPs
    - Raw Aadhaar numbers
    - Biometric data
    """
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id', ondelete='SET NULL'), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    target_type = db.Column(db.String(50))
    target_id = db.Column(db.Integer)
    ip_hash = db.Column(db.String(255))
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, server_default=db.func.now(), index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action}>'
