import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

from app import create_app, db
from app.models import Admin, AuditLog, Candidate, Election, User, Vote, VoterEligibility
from app.services.live_election import get_live_election_stats
from app.services.time import india_now_naive


class LiveElectionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(self.temp_dir.name, 'live-election.sqlite')
        self.app = create_app('development', {
            'TESTING': True,
            'SECRET_KEY': 'live-election-test-secret',
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{database_path}',
            'WTF_CSRF_ENABLED': False,
        })
        with self.app.app_context():
            admin = Admin(username='test-admin')
            admin.set_password('test-password')
            db.session.add(admin)
            db.session.flush()

            now = india_now_naive()
            self.election = Election(
                public_code='LIVE-TEST',
                title='Live turnout test',
                status='OPEN',
                start_time=now - timedelta(hours=1),
                end_time=now + timedelta(hours=1),
                created_by=admin.id,
            )
            self.voter = User(
                name='Test Voter',
                phone='9000000000',
                identity_reference='TEST-VOTER-1',
                kyc_status='VERIFIED',
                face_auth_status='VERIFIED',
            )
            self.second_voter = User(
                name='Second Test Voter',
                phone='9000000001',
                identity_reference='TEST-VOTER-2',
                kyc_status='VERIFIED',
                face_auth_status='VERIFIED',
            )
            self.candidate = Candidate(
                name='Test Candidate',
                identity_reference='TEST-CANDIDATE-1',
                kyc_status='VERIFIED',
                face_auth_status='VERIFIED',
            )
            db.session.add_all([self.election, self.voter, self.second_voter, self.candidate])
            db.session.flush()
            self.election.candidates.append(self.candidate)
            db.session.add(VoterEligibility(
                election_id=self.election.id,
                voter_id=self.voter.id,
                verified=True,
            ))
            db.session.add(VoterEligibility(
                election_id=self.election.id,
                voter_id=self.second_voter.id,
                verified=True,
            ))
            db.session.commit()
            self.election_id = self.election.id
            self.voter_id = self.voter.id
            self.second_voter_id = self.second_voter.id
            self.candidate_id = self.candidate.id

        self.vote_url = '/election/LIVE-TEST/vote'

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        self.temp_dir.cleanup()

    def _voter_client(self, voter_id=None):
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['voter_id'] = voter_id or self.voter_id
            session['voter_name'] = 'Test Voter'
        return client

    def _submit_vote(self):
        client = self._voter_client()
        return client.post(self.vote_url, data={'candidate_id': str(self.candidate_id)})

    def test_duplicate_submission_creates_one_anonymous_vote(self):
        first_response = self._submit_vote()
        second_response = self._submit_vote()

        self.assertTrue(first_response.headers['Location'].endswith('/confirmation'))
        self.assertFalse(second_response.headers['Location'].endswith('/confirmation'))
        with self.app.app_context():
            self.assertEqual(Vote.query.filter_by(election_id=self.election_id).count(), 1)
            self.assertEqual(AuditLog.query.filter_by(action='ANONYMOUS_VOTE_ACCEPTED').count(), 1)
            vote = Vote.query.filter_by(election_id=self.election_id).one()
            self.assertFalse(hasattr(vote, 'voter_id'))
            eligibility = VoterEligibility.query.filter_by(
                election_id=self.election_id,
                voter_id=self.voter_id,
            ).one()
            self.assertIsNone(eligibility.voted_at)
            election = db.session.get(Election, self.election_id)
            stats = get_live_election_stats(election)
            self.assertEqual(sum(point['votes'] for point in stats['participation']), 1)

    def test_two_voters_can_vote_simultaneously(self):
        barrier = Barrier(2)

        def submit_as(voter_id):
            client = self._voter_client(voter_id)
            barrier.wait(timeout=5)
            return client.post(self.vote_url, data={'candidate_id': str(self.candidate_id)})

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(submit_as, [self.voter_id, self.second_voter_id]))

        self.assertTrue(all(response.headers['Location'].endswith('/confirmation') for response in responses))
        with self.app.app_context():
            self.assertEqual(Vote.query.filter_by(election_id=self.election_id).count(), 2)
            self.assertEqual(AuditLog.query.filter_by(action='ANONYMOUS_VOTE_ACCEPTED').count(), 2)

    def test_simultaneous_duplicate_submissions_count_once(self):
        barrier = Barrier(2)

        def submit_at_once():
            client = self._voter_client()
            barrier.wait(timeout=5)
            return client.post(self.vote_url, data={'candidate_id': str(self.candidate_id)})

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _: submit_at_once(), range(2)))

        confirmations = sum(response.headers['Location'].endswith('/confirmation') for response in responses)
        self.assertEqual(confirmations, 1)
        with self.app.app_context():
            self.assertEqual(Vote.query.filter_by(election_id=self.election_id).count(), 1)
            eligibility = VoterEligibility.query.filter_by(
                election_id=self.election_id,
                voter_id=self.voter_id,
            ).one()
            self.assertTrue(eligibility.has_voted)

    def test_zero_verified_voters_has_zero_turnout(self):
        with self.app.app_context():
            eligibility = VoterEligibility.query.filter_by(
                election_id=self.election_id,
                voter_id=self.voter_id,
            ).one()
            eligibility.verified = False
            second_eligibility = VoterEligibility.query.filter_by(
                election_id=self.election_id,
                voter_id=self.second_voter_id,
            ).one()
            second_eligibility.verified = False
            db.session.commit()

        client = self.app.test_client()
        with client.session_transaction() as session:
            session['admin_id'] = 1
        response = client.get(f'/admin/elections/{self.election_id}/live-stats')
        stats = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(stats['totalVerifiedVoters'], 0)
        self.assertEqual(stats['turnoutPercentage'], 0)
        self.assertEqual(stats['remainingVoters'], 0)

    def test_admin_and_voter_dashboards_render_live_turnout(self):
        admin_client = self.app.test_client()
        with admin_client.session_transaction() as session:
            session['admin_id'] = 1
        admin_page = admin_client.get('/admin/dashboard')
        self.assertEqual(admin_page.status_code, 200)
        self.assertIn(b'Election turnout tracking', admin_page.data)
        self.assertIn(b'live_election.js', admin_page.data)

        voter_client = self._voter_client()
        voter_page = voter_client.get('/voter/dashboard')
        self.assertEqual(voter_page.status_code, 200)
        self.assertIn(b'Live turnout', voter_page.data)
        self.assertIn(b'/election/LIVE-TEST/live-stats', voter_page.data)

    def test_admin_tracker_keeps_closed_election_visible(self):
        with self.app.app_context():
            election = db.session.get(Election, self.election_id)
            election.status = 'CLOSED'
            db.session.commit()

        client = self.app.test_client()
        with client.session_transaction() as session:
            session['admin_id'] = 1
        dashboard = client.get('/admin/dashboard')
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(f'/admin/elections/{self.election_id}/live-stats'.encode(), dashboard.data)

    def test_voter_stats_endpoint_returns_only_aggregate_data(self):
        response = self._voter_client().get('/election/LIVE-TEST/live-stats')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['totalVerifiedVoters'], 2)
        self.assertNotIn('voterId', payload)
        self.assertNotIn('voterName', payload)
        self.assertNotIn('candidateId', payload)
        self.assertNotIn('phone', payload)
        self.assertNotIn('identityReference', payload)

        anonymous_response = self.app.test_client().get('/election/LIVE-TEST/live-stats')
        self.assertEqual(anonymous_response.status_code, 401)

        with self.app.app_context():
            second_eligibility = VoterEligibility.query.filter_by(
                election_id=self.election_id,
                voter_id=self.second_voter_id,
            ).one()
            second_eligibility.verified = False
            db.session.commit()
        unverified_response = self._voter_client(self.second_voter_id).get(
            '/election/LIVE-TEST/live-stats'
        )
        self.assertEqual(unverified_response.status_code, 403)

    def test_live_stats_endpoint_does_not_accept_counter_writes(self):
        admin_client = self.app.test_client()
        with admin_client.session_transaction() as session:
            session['admin_id'] = 1
        response = admin_client.post(
            f'/admin/elections/{self.election_id}/live-stats',
            json={'votesCast': 999},
        )
        self.assertEqual(response.status_code, 405)
        with self.app.app_context():
            self.assertEqual(Vote.query.filter_by(election_id=self.election_id).count(), 0)

    def test_invalid_or_closed_election_vote_does_not_change_counts(self):
        invalid_candidate = self._voter_client().post(
            self.vote_url,
            data={'candidate_id': '999999'},
        )
        self.assertFalse(invalid_candidate.headers['Location'].endswith('/confirmation'))

        with self.app.app_context():
            election = db.session.get(Election, self.election_id)
            election.status = 'CLOSED'
            db.session.commit()
        closed_response = self._submit_vote()
        self.assertFalse(closed_response.headers['Location'].endswith('/confirmation'))

        with self.app.app_context():
            self.assertEqual(Vote.query.filter_by(election_id=self.election_id).count(), 0)
            eligibility = VoterEligibility.query.filter_by(
                election_id=self.election_id,
                voter_id=self.voter_id,
            ).one()
            self.assertFalse(eligibility.has_voted)

    def test_results_are_hidden_until_election_ends(self):
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['admin_id'] = 1

        before_end = client.get(f'/admin/results/{self.election_id}')
        self.assertEqual(before_end.status_code, 302)

        with self.app.app_context():
            election = db.session.get(Election, self.election_id)
            election.end_time = india_now_naive() - timedelta(minutes=1)
            db.session.commit()

        after_end = client.get(f'/admin/results/{self.election_id}')
        self.assertEqual(after_end.status_code, 200)
        results_page = client.get('/admin/results')
        self.assertEqual(results_page.status_code, 200)
        self.assertIn(b'Live turnout test', results_page.data)

    def test_expired_open_election_rejects_vote_without_claiming_eligibility(self):
        with self.app.app_context():
            election = db.session.get(Election, self.election_id)
            election.end_time = india_now_naive() - timedelta(seconds=1)
            db.session.commit()

        response = self._submit_vote()
        self.assertFalse(response.headers['Location'].endswith('/confirmation'))
        with self.app.app_context():
            self.assertEqual(Vote.query.filter_by(election_id=self.election_id).count(), 0)
            eligibility = VoterEligibility.query.filter_by(
                election_id=self.election_id,
                voter_id=self.voter_id,
            ).one()
            self.assertFalse(eligibility.has_voted)


if __name__ == '__main__':
    unittest.main()