from datetime import datetime
from app import db

# Association table for many-to-many relationship between elections and candidates
election_candidates = db.Table('election_candidates',
    db.Column('id', db.Integer, primary_key=True),
    db.Column('election_id', db.Integer, db.ForeignKey('elections.id', ondelete='CASCADE'), nullable=False),
    db.Column('candidate_id', db.Integer, db.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False),
    db.UniqueConstraint('election_id', 'candidate_id', name='unique_election_candidate'),
    db.Index('idx_election_id', 'election_id'),
    db.Index('idx_candidate_id', 'candidate_id')
)

class Candidate(db.Model):
    """Candidate model for election candidates."""
    __tablename__ = 'candidates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    identity_reference = db.Column(db.String(255), unique=True, nullable=True, index=True)
    photo = db.Column(db.String(255))
    description = db.Column(db.Text)
    kyc_status = db.Column(db.String(20), nullable=False, default='PENDING')
    kyc_document_filename = db.Column(db.String(255), nullable=True)
    kyc_submitted_at = db.Column(db.DateTime, nullable=True)
    kyc_verified_at = db.Column(db.DateTime, nullable=True)
    kyc_rejection_reason = db.Column(db.String(500), nullable=True)
    face_image_filename = db.Column(db.String(255), nullable=True)
    face_auth_status = db.Column(db.String(20), nullable=False, default='PENDING')
    face_verified_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    def get_vote_count(self, election_id):
        """Get vote count for this candidate in a specific election."""
        from app.models.vote import Vote
        return Vote.query.filter_by(
            election_id=election_id,
            candidate_id=self.id
        ).count()
    
    def __repr__(self):
        return f'<Candidate {self.name}>'
