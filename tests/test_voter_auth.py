import os
import tempfile
import unittest
from io import BytesIO
from unittest.mock import patch

from app import create_app, db
from app.models import User


class VoterAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(self.temp_dir.name, 'voter-auth.sqlite')
        self.app = create_app('development', {
            'TESTING': True,
            'SECRET_KEY': 'voter-auth-test-secret',
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{database_path}',
            'WTF_CSRF_ENABLED': False,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        self.temp_dir.cleanup()

    def _registration_data(self, password='voter-password-123', confirmation=None):
        return {
            'name': 'Test Voter',
            'phone': '9000000000',
            'identity_reference': 'ABCDE1234F',
            'password': password,
            'password_confirmation': confirmation if confirmation is not None else password,
            'face_capture_method': 'camera',
            'kyc_document': (BytesIO(b'identity document'), 'identity.pdf'),
            'face_image': (BytesIO(b'face image'), 'face.jpg'),
        }

    def _register(self, data=None):
        with patch('app.routes.voter._save_kyc_document', return_value='identity.pdf'), \
                patch('app.routes.voter._save_face_image', return_value='face.jpg'):
            return self.client.post(
                '/voter/register',
                data=data or self._registration_data(),
                content_type='multipart/form-data',
            )

    def test_registration_stores_a_hash_and_password_can_log_in_after_verification(self):
        response = self._register()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers['Location'].endswith('/voter/login'))

        with self.app.app_context():
            voter = User.query.filter_by(phone='9000000000').one()
            self.assertNotEqual(voter.password_hash, 'voter-password-123')
            self.assertTrue(voter.check_password('voter-password-123'))
            self.assertFalse(voter.check_password('incorrect-password'))
            voter.kyc_status = 'VERIFIED'
            voter.face_auth_status = 'VERIFIED'
            db.session.commit()

        failed_login = self.client.post('/voter/login', data={
            'phone': '9000000000',
            'password': 'incorrect-password',
        })
        self.assertEqual(failed_login.status_code, 200)
        with self.client.session_transaction() as session:
            self.assertNotIn('voter_id', session)

        successful_login = self.client.post('/voter/login', data={
            'phone': '9000000000',
            'password': 'voter-password-123',
        })
        self.assertEqual(successful_login.status_code, 302)
        self.assertTrue(successful_login.headers['Location'].endswith('/voter/dashboard'))
        with self.client.session_transaction() as session:
            self.assertIn('voter_id', session)

    def test_registration_rejects_mismatched_passwords(self):
        response = self._register(self._registration_data(confirmation='different-password'))

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Passwords do not match.', response.data)
        with self.app.app_context():
            self.assertEqual(User.query.count(), 0)

    def test_registration_rejects_passwords_shorter_than_eight_characters(self):
        response = self._register(self._registration_data(password='short'))

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Password must be at least 8 characters', response.data)
        with self.app.app_context():
            self.assertEqual(User.query.count(), 0)


if __name__ == '__main__':
    unittest.main()
