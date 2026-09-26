from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import Admin
from app.services.audit import log_audit_event
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    """Decorator to require admin login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please provide both username and password.', 'error')
            return render_template('admin/login.html')
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username
            
            # Update last login
            from datetime import datetime
            admin.last_login = datetime.utcnow()
            
            from app import db
            db.session.commit()
            
            # Log the login event
            log_audit_event(
                admin_id=admin.id,
                action='ADMIN_LOGIN',
                details=f'Admin {username} logged in'
            )
            
            flash('Login successful!', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('admin/login.html')

@auth_bp.route('/admin/logout')
def admin_logout():
    """Admin logout."""
    admin_id = session.get('admin_id')
    admin_username = session.get('admin_username')
    
    if admin_id:
        log_audit_event(
            admin_id=admin_id,
            action='ADMIN_LOGOUT',
            details=f'Admin {admin_username} logged out'
        )
    
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.admin_login'))
