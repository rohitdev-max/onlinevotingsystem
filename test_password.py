from app import create_app, db
from app.models import Admin

app = create_app()
with app.app_context():
    admin = Admin.query.filter_by(username='admin').first()
    if admin:
        print('Admin found, checking password...')
        print('Password check:', admin.check_password('admin123'))
    else:
        print('Admin not found')
