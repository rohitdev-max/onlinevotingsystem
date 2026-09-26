# ROHIT VOTING SYSTEM

A secure, private, and transparent web-based voting application for college/community/demo elections.

## IMPORTANT DISCLAIMER

**This project is a prototype/college/community voting system.**
**It is NOT certified for government or legally binding elections.**

**Real Aadhaar authentication requires an authorized integration and applicable legal/security compliance.**

---

## Technology Stack

### Frontend
- HTML5
- CSS3
- JavaScript
- Bootstrap 5

### Backend
- Python
- Flask

### Database
- MySQL
- PyMySQL / SQLAlchemy

### Security
- HTTPS-ready architecture
- Password hashing (bcrypt)
- Secure sessions
- CSRF protection
- Server-side validation
- SQL injection protection
- Rate limiting
- Secure cookies
- Audit logging

---

## Project Structure

```
Rohit-voting-system/
│
├── app.py                      # Main application entry point
├── config.py                   # Configuration management
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not in git)
├── .gitignore                  # Git ignore rules
├── test_db_connection.py       # Database connection test
│
├── app/
│   ├── __init__.py            # Application factory
│   │
│   ├── models/                # Database models
│   │   ├── __init__.py
│   │   ├── user.py           # Admin, User models
│   │   ├── election.py       # Election model
│   │   ├── candidate.py      # Candidate model
│   │   └── vote.py           # Vote, VoterEligibility, VerificationRecord, AuditLog
│   │
│   ├── routes/                # Flask routes
│   │   ├── auth.py            # Authentication routes
│   │   ├── voter.py           # Voter routes
│   │   ├── voting.py          # Voting routes
│   │   └── admin.py           # Admin routes
│   │
│   ├── services/              # Business logic
│   │   ├── verification.py    # Identity verification
│   │   ├── voting_service.py  # Voting logic
│   │   └── audit.py           # Audit logging
│   │
│   ├── templates/             # HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── voter/
│   │   └── admin/
│   │
│   └── static/                # Static assets
│       ├── css/
│       ├── js/
│       └── images/
│
├── database/
│   ├── schema.sql             # Database schema
│   ├── seed.sql               # Seed data
│   └── init_db.py             # Database initialization script
│
└── README.md                  # This file
```

---

## Installation

### Prerequisites

1. Python 3.8 or higher
2. MySQL 5.7 or higher
3. pip (Python package manager)

### Step 1: Clone the repository

```bash
cd "C:\Users\kv707\rohit voting app"
```

### Step 2: Create a virtual environment

```bash
python -m venv venv
```

### Step 3: Activate the virtual environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### Step 4: Install dependencies

```bash
pip install -r requirements.txt
```

---

## MySQL Setup

### Step 1: Configure environment variables

Edit the `.env` file with your database credentials:

```env
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=rohit_voting_system
DATABASE_USER=root
DATABASE_PASSWORD=your_password_here
SECRET_KEY=your-secret-key-change-this-in-production
```

**IMPORTANT:** Generate a secure SECRET_KEY for production:
```python
import secrets
print(secrets.token_hex(32))
```

### Step 2: Test database connection

```bash
python test_db_connection.py
```

You should see:
```
✓ Successfully connected to MySQL database!
✓ MySQL version: X.X.XX
✓ Connection test completed successfully!
```

### Step 3: Initialize the database

```bash
python database/init_db.py
```

This will:
- Create the database if it doesn't exist
- Create all tables with proper constraints and indexes
- Insert seed data (default admin account, sample candidates, test voters)

**Default admin credentials:**
- Username: `admin`
- Password: `admin123`

**IMPORTANT:** Change the default admin password immediately after first login!

---

## Database Schema

### Tables

1. **admins** - Administrator accounts
   - id, username, password_hash, created_at, last_login

2. **users** - Voter information
   - id, name, phone, identity_reference (hashed), created_at, updated_at

3. **elections** - Election information
   - id, public_code, title, description, status, start_time, end_time, created_at, created_by

4. **candidates** - Candidate information
   - id, name, photo, description, created_at

5. **election_candidates** - Links candidates to elections
   - id, election_id, candidate_id
   - UNIQUE(election_id, candidate_id)

6. **voter_eligibility** - Tracks voter eligibility and voting status
   - id, election_id, voter_id, verified, has_voted, verified_at, voted_at
   - UNIQUE(election_id, voter_id) - **Enforces one-person-one-vote**

7. **votes** - Recorded votes
   - id, election_id, candidate_id, created_at
   - **Does NOT store voter_id for ballot secrecy**

8. **verification_records** - Identity verification attempts
   - id, user_id, election_id, verification_method, status, attempt_count, created_at, updated_at

9. **audit_logs** - Security event logging
   - id, admin_id, action, target_type, target_id, ip_hash, details, timestamp

### Key Security Features

- **UNIQUE constraints** prevent duplicate voting
- **Foreign keys** ensure referential integrity
- **Indexes** on frequently queried columns
- **Ballot secrecy** - votes table does not link to voters
- **Aadhaar privacy** - identity_reference is a hash, not raw number

---

## Running the Application

### Development mode

```bash
python app.py
```

The application will be available at: `http://localhost:5000`

### Production mode

Use Gunicorn instead of Flask's development server:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## Phase 1 Complete ✓

**What has been implemented:**
- Project structure created
- Flask application factory pattern
- Configuration management with environment variables
- MySQL connection setup
- Basic route blueprints (auth, voter, voting, admin)
- Database connection test script
- Virtual environment setup instructions

---

## Phase 2 Complete ✓

**What has been implemented:**
- Complete MySQL database schema with all required tables
- Database constraints (UNIQUE, FOREIGN KEY, NOT NULL)
- Proper indexes for performance
- SQLAlchemy ORM models mapping to database tables
- Database initialization script (init_db.py)
- Seed data for testing (admin, candidates, voters, sample election)
- Views for election statistics and results
- Security-focused design (ballot secrecy, Aadhaar privacy)

**Database features:**
- Normalized schema with proper relationships
- UNIQUE(election_id, voter_id) constraint enforces one-person-one-vote
- Votes table does not store voter_id for ballot secrecy
- Identity reference is hashed, not raw Aadhaar number
- Audit logging for security events
- Views for statistics and results

**Next Steps:**
- Phase 3: Admin authentication
- Phase 4: Election management
- Phase 5: Candidate management
- Phase 6: Voter registration
- Phase 7: Mock identity verification
- Phase 8: Voting system
- Phase 9: One-person-one-vote protection
- Phase 10: Election locking
- Phase 11: Results
- Phase 12: Audit logs
- Phase 13: Security testing
- Phase 14: Deployment

---

## Security Model

### Key Security Features

1. **Server-Side Validation**: All critical checks happen on the backend
2. **Database Constraints**: UNIQUE constraints prevent duplicate voting
3. **Transactions**: Vote recording uses database transactions
4. **Password Hashing**: Admin passwords are hashed with bcrypt
5. **CSRF Protection**: All forms are protected with CSRF tokens
6. **Session Security**: Secure cookies with HttpOnly flag
7. **SQL Injection Protection**: Parameterized queries via SQLAlchemy
8. **Audit Logging**: All security-sensitive events are logged

### Privacy Model

1. **Aadhaar Privacy**: Aadhaar numbers are never stored in plaintext
2. **Ballot Secrecy**: Voter-candidate relationship is not stored
3. **Data Minimization**: Only
