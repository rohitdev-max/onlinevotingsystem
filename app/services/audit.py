"""
Audit logging service.
Records security-sensitive events for accountability.
"""
from app import db
from app.models import AuditLog
from flask import request
import hashlib

def log_audit_event(admin_id, action, target_type=None, target_id=None, details=None):
    """
    Log an audit event.
    
    Args:
        admin_id: ID of the admin performing the action
        action: Description of the action
        target_type: Type of target (e.g., 'ELECTION', 'VOTER')
        target_id: ID of the target
        details: Additional details about the event
    """
    # Hash IP address for privacy
    ip_address = request.remote_addr if request else '127.0.0.1'
    ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()
    
    audit_log = AuditLog(
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip_hash=ip_hash,
        details=details
    )
    
    db.session.add(audit_log)
    db.session.commit()
