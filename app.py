import os

from app import create_app

# Use development defaults locally; set FLASK_CONFIG=production when deployed.
app = create_app(os.getenv('FLASK_CONFIG', 'development'))

if __name__ == '__main__':
    app.run(debug=app.config.get('DEBUG', False), host='0.0.0.0', port=5000)