-- ROHIT VOTING SYSTEM - Seed Data for Testing
-- This file contains sample data for development and testing

-- Note: Default admin is already created in schema.sql
-- Username: admin
-- Password: admin123

-- Sample candidates
INSERT INTO candidates (name, photo, description) VALUES
('Rahul Sharma', NULL, 'Computer Science Department - 3rd Year'),
('Priya Patel', NULL, 'Electrical Engineering Department - 2nd Year'),
('Amit Kumar', NULL, 'Mechanical Engineering Department - 4th Year'),
('Sneha Reddy', NULL, 'Civil Engineering Department - 3rd Year'),
('Vikram Singh', NULL, 'Business Administration - 2nd Year');

-- Sample test voters
-- In development, we use test identity numbers (not real Aadhaar)
-- identity_reference is a hash of: TEST-0001, TEST-0002, etc.
INSERT INTO users (name, phone, identity_reference) VALUES
('Test Voter 1', '9000000001', 'test-identity-0001-hash'),
('Test Voter 2', '9000000002', 'test-identity-0002-hash'),
('Test Voter 3', '9000000003', 'test-identity-0003-hash'),
('Test Voter 4', '9000000004', 'test-identity-0004-hash'),
('Test Voter 5', '9000000005', 'test-identity-0005-hash');

-- Sample election (DRAFT status)
INSERT INTO elections (public_code, title, description, status, start_time, end_time, created_by) VALUES
('DEMO2024', 'Student Council Election 2024', 'Vote for your student council representatives for the academic year 2024-25', 'DRAFT', '2024-09-01 09:00:00', '2024-09-30 18:00:00', 1);

-- Link candidates to the sample election
INSERT INTO election_candidates (election_id, candidate_id) VALUES
(1, 1),  -- Rahul Sharma
(1, 2),  -- Priya Patel
(1, 3),  -- Amit Kumar
(1, 4),  -- Sneha Reddy
(1, 5);  -- Vikram Singh

-- Make test voters eligible for the sample election
INSERT INTO voter_eligibility (election_id, voter_id, verified, has_voted) VALUES
(1, 1, TRUE, FALSE),
(1, 2, TRUE, FALSE),
(1, 3, TRUE, FALSE),
(1, 4, TRUE, FALSE),
(1, 5, TRUE, FALSE);

-- Sample audit log entries
INSERT INTO audit_logs (admin_id, action, target_type, target_id, ip_hash, details) VALUES
(1, 'SYSTEM_INITIALIZED', 'SYSTEM', NULL, '127.0.0.1', 'Database initialized with seed data'),
(1, 'ELECTION_CREATED', 'ELECTION', 1, '127.0.0.1', 'Created election: Student Council Election 2024');
