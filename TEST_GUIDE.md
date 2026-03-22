# MockTest Auth Service - Testing Guide

This guide will walk you through setting up and running comprehensive tests for the authentication service.

## Prerequisites

- Python 3.11+
- Docker and Docker Compose (for full environment)
- Virtual environment (recommended)

## Setup Instructions

### Step 1: Install Dependencies

```bash
# Install main application dependencies
pip install -r requirements.txt

# Install test dependencies
pip install -r requirements-test.txt
```

### Step 2: Start the Database (Choose One Option)

#### Option A: Using Docker Compose (Recommended)
```bash
# Start PostgreSQL and Redis
docker-compose up -d db redis

# Wait for services to be healthy
docker-compose ps
```

#### Option B: Using Local SQLite (For Quick Tests)
```bash
# No setup needed - SQLite will be created automatically
# Tests will use test.db by default
```

### Step 3: Set Environment Variables

Create a `.env.test` file:

```bash
# For PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mocktest_auth
REDIS_URL=redis://localhost:6379/0

# For SQLite (simpler option)
# DATABASE_URL=sqlite+aiosqlite:///./test.db
# REDIS_URL=redis://localhost:6379/0

SECRET_KEY=your-secret-key-here
SESSION_SECRET=your-session-secret-here
ENVIRONMENT=testing
LOG_LEVEL=INFO
```

### Step 4: Initialize the Database

```bash
# Create database tables
python create_tables.py
```

## Running Tests

### Level 1: Health Checks (Basic Connectivity)
Test that the API is running and accessible.

```bash
pytest tests/test_level_1_health.py -v
```

**Expected Output:** 5 tests checking API availability, health endpoints, and documentation.

### Level 2: User Registration
Test user registration for students and teachers.

```bash
pytest tests/test_level_2_registration.py -v
```

**Expected Output:** 6 tests covering successful registration, duplicate checks, and validation.

### Level 3: Authentication & Login
Test login, logout, and token management.

```bash
pytest tests/test_level_3_authentication.py -v
```

**Expected Output:** 8 tests covering login flows, token refresh, and access control.

### Level 4: Session Management
Test session handling, exam sessions, and multi-device support.

```bash
pytest tests/test_level_4_sessions.py -v
```

**Expected Output:** 7 tests covering session lifecycle and exam session controls.

### Level 5: Admin Operations
Test admin invitations and user management.

```bash
pytest tests/test_level_5_admin.py -v
```

**Expected Output:** 8 tests covering admin privileges, invitations, and user account management.

### Level 6: Security & Edge Cases
Test security features and edge cases.

```bash
pytest tests/test_level_6_security.py -v
```

**Expected Output:** 9 tests covering password changes, token invalidation, and security controls.

### Run All Tests

```bash
# Run all tests with detailed output
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=app --cov-report=html

# Run specific test level
pytest tests/test_level_3_authentication.py -v
```

## Test Results Documentation

### Creating a Test Report

```bash
# Generate detailed test report
pytest tests/ -v --html=test_report.html --self-contained-html

# Generate JSON report
pytest tests/ -v --json-report --json-report-file=test_results.json
```

### Manual Results Collection

For each test level, document:

1. **Test Name**: Name of the test function
2. **Status**: PASSED / FAILED / SKIPPED
3. **Duration**: Time taken to execute
4. **Error Details**: If failed, copy the error message
5. **Response Data**: Note any important data from print statements

### Example Documentation Template

```
=== TEST LEVEL 1: Health Checks ===
Date: 2024-01-XX
Environment: Docker / Local

test_root_endpoint: PASSED (0.05s)
  - Service: MockTest Auth Service
  - Version: 2.0.0

test_liveness_probe: PASSED (0.03s)
  - Status: ok

test_readiness_probe: PASSED (0.04s)
  - Database: healthy
  - Redis: healthy

... (continue for all tests)
```

## Troubleshooting Common Issues

### Database Connection Errors

```bash
# Check if PostgreSQL is running
docker-compose ps db

# Check database connection
docker-compose exec db psql -U postgres -c "SELECT 1"

# Recreate database
docker-compose down -v
docker-compose up -d db redis
python create_tables.py
```

### Redis Connection Errors

```bash
# Check if Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping
```

### Import Errors

```bash
# Ensure you're in the project root
export PYTHONPATH=$PWD

# Reinstall dependencies
pip install -r requirements.txt -r requirements-test.txt
```

### Test Database Issues

```bash
# Remove test database
rm test.db

# Clear pytest cache
rm -rf .pytest_cache
```

## Progressive Testing Strategy

Follow this sequence to ensure each level works before proceeding:

1. **Level 1** - Verify basic connectivity ✓
2. **Level 2** - Test user registration ✓
3. **Level 3** - Test authentication flows ✓
4. **Level 4** - Test session management ✓
5. **Level 5** - Test admin features ✓
6. **Level 6** - Test security controls ✓

If any level fails, **STOP** and fix issues before proceeding to the next level.

## Sending Results

After running each test level, provide:

1. Full console output
2. List of passed/failed tests
3. Any error messages
4. Screenshots of test reports (optional)
5. Test duration

Example:
```
LEVEL 3 RESULTS:
- Total: 8 tests
- Passed: 7 tests
- Failed: 1 test (test_refresh_token)
- Duration: 2.3s

Error: test_refresh_token - AssertionError: Token not refreshed
Full traceback: ...
```

## Next Steps

Once you run the tests and document the results:
1. Share the output with me
2. I'll analyze any failures
3. I'll provide specific fixes for failing tests
4. We'll re-run and verify fixes
5. Continue to the next level

Good luck with testing! 🚀
