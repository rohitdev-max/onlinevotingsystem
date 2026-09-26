-- ROHIT VOTING SYSTEM - Database Schema
-- This schema implements a secure, normalized database for the voting system

-- Drop tables if they exist (for clean setup)
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS votes;
DROP TABLE IF EXISTS voter_eligibility;
DROP TABLE IF EXISTS verification_records;
DROP TABLE IF EXISTS election_candidates;
DROP TABLE IF EXISTS candidates;
DROP TABLE IF EXISTS elections;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS admins;

-- Admins table - stores administrator accounts
CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Users table - stores voter information
-- identity_reference is a secure hash of the Aadhaar number, not the raw number
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    identity_reference VARCHAR(255) NOT NULL UNIQUE,
    kyc_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    kyc_document_filename VARCHAR(255) NULL,
    kyc_submitted_at TIMESTAMP NULL,
    kyc_verified_at TIMESTAMP NULL,
    kyc_rejection_reason VARCHAR(500) NULL,
    face_image_filename VARCHAR(255) NULL,
    face_auth_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    face_verified_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_phone (phone),
    INDEX idx_identity_reference (identity_reference)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Elections table - stores election information
CREATE TABLE elections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    public_code VARCHAR(16) NOT NULL UNIQUE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status ENUM('DRAFT', 'SCHEDULED', 'OPEN', 'CLOSED', 'RESULTS_PUBLISHED') NOT NULL DEFAULT 'DRAFT',
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INT NOT NULL,
    FOREIGN KEY (created_by) REFERENCES admins(id) ON DELETE RESTRICT,
    INDEX idx_public_code (public_code),
    INDEX idx_status (status),
    INDEX idx_start_time (start_time),
    INDEX idx_end_time (end_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Candidates table - stores candidate information
CREATE TABLE candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NULL,
    identity_reference VARCHAR(255) NULL UNIQUE,
    photo VARCHAR(255),
    description TEXT,
    kyc_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    kyc_document_filename VARCHAR(255) NULL,
    kyc_submitted_at TIMESTAMP NULL,
    kyc_verified_at TIMESTAMP NULL,
    kyc_rejection_reason VARCHAR(500) NULL,
    face_image_filename VARCHAR(255) NULL,
    face_auth_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    face_verified_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Election-Candidates junction table - links candidates to elections
CREATE TABLE election_candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    election_id INT NOT NULL,
    candidate_id INT NOT NULL,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    UNIQUE KEY unique_election_candidate (election_id, candidate_id),
    INDEX idx_election_id (election_id),
    INDEX idx_candidate_id (candidate_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Voter Eligibility table - tracks which voters are eligible for which elections
-- This table enforces one-person-one-vote at the database level
CREATE TABLE voter_eligibility (
    id INT AUTO_INCREMENT PRIMARY KEY,
    election_id INT NOT NULL,
    voter_id INT NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    has_voted BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP NULL,
    voted_at TIMESTAMP NULL,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
    FOREIGN KEY (voter_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_election_voter (election_id, voter_id),
    INDEX idx_election_id (election_id),
    INDEX idx_voter_id (voter_id),
    INDEX idx_has_voted (has_voted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Votes table - stores actual votes
-- Important: This table does NOT store voter_id to protect ballot secrecy
CREATE TABLE votes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    election_id INT NOT NULL,
    candidate_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE RESTRICT,
    INDEX idx_election_id (election_id),
    INDEX idx_candidate_id (candidate_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Verification Records table - stores identity verification attempts
-- Stores minimal information for audit purposes only
CREATE TABLE verification_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    election_id INT NOT NULL,
    verification_method VARCHAR(50) NOT NULL,
    status ENUM('PENDING', 'SUCCESS', 'FAILED') NOT NULL DEFAULT 'PENDING',
    attempt_count INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_election_id (election_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Audit Logs table - records security-sensitive events
-- Never logs passwords, OTPs, raw Aadhaar numbers, or biometric data
CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NULL,
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id INT,
    ip_hash VARCHAR(255),
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE SET NULL,
    INDEX idx_admin_id (admin_id),
    INDEX idx_action (action),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert a default admin user (password: admin123)
-- In production, this should be changed immediately
INSERT INTO admins (username, password_hash) 
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7vRfTzKJ9i');

-- View for election statistics
CREATE VIEW election_statistics AS
SELECT 
    e.id AS election_id,
    e.title,
    e.status,
    e.start_time,
    e.end_time,
    COUNT(DISTINCT ve.voter_id) AS total_eligible_voters,
    SUM(CASE WHEN ve.verified = TRUE THEN 1 ELSE 0 END) AS verified_voters,
    SUM(CASE WHEN ve.has_voted = TRUE THEN 1 ELSE 0 END) AS votes_cast,
    COUNT(DISTINCT ve.voter_id) - SUM(CASE WHEN ve.has_voted = TRUE THEN 1 ELSE 0 END) AS remaining_voters,
    CASE 
        WHEN COUNT(DISTINCT ve.voter_id) > 0 
        THEN ROUND((SUM(CASE WHEN ve.has_voted = TRUE THEN 1 ELSE 0 END) / COUNT(DISTINCT ve.voter_id)) * 100, 2)
        ELSE 0 
    END AS turnout_percentage
FROM elections e
LEFT JOIN voter_eligibility ve ON e.id = ve.election_id
GROUP BY e.id, e.title, e.status, e.start_time, e.end_time;

-- View for election results
CREATE VIEW election_results AS
SELECT 
    e.id AS election_id,
    e.title,
    c.id AS candidate_id,
    c.name AS candidate_name,
    c.photo,
    c.description,
    COUNT(v.id) AS vote_count,
    CASE 
        WHEN (SELECT COUNT(*) FROM votes WHERE election_id = e.id) > 0 
        THEN ROUND((COUNT(v.id) / (SELECT COUNT(*) FROM votes WHERE election_id = e.id)) * 100, 2)
        ELSE 0 
    END AS vote_percentage
FROM elections e
LEFT JOIN election_candidates ec ON e.id = ec.election_id
LEFT JOIN candidates c ON ec.candidate_id = c.id
LEFT JOIN votes v ON e.id = v.election_id AND c.id = v.candidate_id
GROUP BY e.id, e.title, c.id, c.name, c.photo, c.description
ORDER BY vote_count DESC;
