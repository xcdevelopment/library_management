# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based library management system with comprehensive book tracking, user management, and reservation functionality. The application uses Docker for containerization and MySQL for data persistence.

## Development Environment Setup

### Required Tools
- Docker Desktop (must be installed and running)
- The application runs entirely in containers

### Quick Start Commands
```bash
# Build and start all services (run from project root)
docker-compose up --build -d

# Initialize database with admin user (first time only)
docker-compose exec web flask db init
docker-compose exec web flask db migrate -m "Initial migration"
docker-compose exec web flask db upgrade
docker-compose exec web flask init-db

# Access application
# Browser: http://localhost:8080
```

### Daily Development Workflow
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Execute commands in container (use service name 'web', not container name)
docker-compose exec web <command>

# Database migrations after model changes
docker-compose exec web flask db migrate -m "Description of changes"
docker-compose exec web flask db upgrade

# Reset admin password
docker-compose exec web flask reset-admin-password

# Run scheduled tasks manually (for testing)
docker-compose exec web python scheduler.py
```

### Container Command Execution
- Always use service name `web` (not container name `library_web`)
- For Python scripts that import app modules, use: `docker-compose exec -e PYTHONPATH=/app web python script.py`

## Architecture Overview

### Application Structure
```
app.py              # Application factory and main entry point
config.py           # Environment-based configuration (dev/test/prod)
models.py           # SQLAlchemy models (User, Book, LoanHistory, Reservation, OperationLog)
scheduler.py        # Background tasks (email reminders, cleanup)

routes/             # Flask blueprints for different feature areas
├── auth.py         # Authentication (login/logout/signup)
├── books.py        # Book management (CRUD, search, import)
├── users.py        # User management and profiles
├── admin.py        # Admin panel functionality
├── reservations.py # Book reservation system
└── api.py          # REST API endpoints

services/           # Business logic layer
├── auth_service.py
├── book_service.py
├── user_service.py
├── reservation_service.py
├── loan_service.py
├── email_service.py
├── slack_service.py
└── notifications.py

forms/              # WTForms for input validation
utils/              # Utility functions and decorators
templates/          # Jinja2 HTML templates
static/             # CSS, JS, and static assets
```

### Database Models
- **User**: Authentication, profiles, admin flags, max loan limits
- **Book**: Title, author, categories, status, availability, management numbers, images
- **LoanHistory**: Borrowing records with due dates, return tracking, extension history
- **Reservation**: Queue-based book reservation system
- **OperationLog**: Audit trail for all system operations
- **Announcement**: Admin announcements and notices
- **CategoryLocationMapping**: Automatic location assignment based on book categories
- **BookImage**: Multiple image storage for books (covers, table of contents, etc.)

### Key Features
- Argon2 password hashing for security
- Flask-Login for session management
- Flask-Migrate for database versioning
- Rate limiting with Flask-Limiter
- Security headers via Flask-Talisman
- Email notifications for due dates and reservations
- Slack integration for reminders and notifications
- CSV import/export functionality
- Comprehensive audit logging
- **Maximum simultaneous loan limits (default: 3 books per user)**
- **Book extension system (1-week/2-week options, max 1 extension)**
- **Home dashboard with personalized information**
- **Automatic book management number generation (BO-yyyy-001 format)**
- **Category-based automatic location assignment**
- **Multi-image support for books with size limitations**

## Configuration Management

The application uses environment-based configuration:
- **Development**: Uses `development` config with debug enabled
- **Testing**: Uses `testing` config with CSRF disabled
- **Production**: Uses `production` config with security features enabled

Environment variables are loaded from `.env` file and Docker environment.

### Important Environment Variables
- `FLASK_ENV`: Determines configuration (development/testing/production)
- `ADMIN_PASSWORD`: Sets initial admin user password
- `SECRET_KEY`: Flask session encryption key
- Database URLs for different environments
- `SLACK_BOT_TOKEN`: Slack bot token for sending notifications
- `SLACK_ENABLED`: Enable/disable Slack notifications (true/false)
- `ADMIN_SLACK_EMAIL`: Admin email for system error notifications

## Security Features

- **Flask-Talisman**: CSP headers, HTTPS redirection (production only)
- **Rate Limiting**: 200 requests/day, 50 requests/hour default limits
- **Session Security**: Secure cookies, SameSite=Lax, 1-hour lifetime
- **HTTPS Enforcement**: Production environments only
- **CSRF Protection**: Enabled by default via Flask-WTF

## Database Operations

### Migrations
```bash
# Create new migration after model changes
docker-compose exec web flask db migrate -m "Description"

# Apply migrations
docker-compose exec web flask db upgrade

# Rollback if needed
docker-compose exec web flask db downgrade
```

### Admin Management
- Default admin user: `Development@xcap.co.jp` / `adminpass`
- Password can be reset via CLI command or environment variable

## Feature Implementation Plan

The system is being enhanced with new features in the following phases:

### Phase 1: Core Restrictions and Extensions
- **Maximum loan limits**: Users can borrow up to 3 books simultaneously (configurable by admin)
- **Loan restrictions**: No new loans if user has overdue books or exceeds limits
- **Extension system**: 1-week or 2-week extensions (maximum 1 extension per loan)
- **Extension restrictions**: Cannot extend if book has pending reservations

### Phase 2: Enhanced User Experience
- **Home dashboard**: Personalized view with current loans, due dates, alerts, and popular books
- **Enhanced Slack notifications**: 3-day advance reminders with extension guidance
- **Reservation notifications**: Immediate alerts when someone reserves a currently borrowed book
- **Due date alerts**: 3-day advance warnings for upcoming returns

### Phase 3: Administrative Improvements
- **Automatic management numbers**: BO-yyyy-001 format with year-based sequencing
- **Smart location assignment**: Category-based automatic location filling
- **Admin announcement system**: System-wide notices and updates

### Phase 4: Media Enhancement (Lowest Priority)
- **Multi-image support**: Book covers, table of contents, multiple views
- **Size optimization**: 2MB per book limit to stay within storage constraints

## Slack Notification System

The system includes comprehensive Slack integration for real-time notifications:

### Configuration
- `SLACK_BOT_TOKEN`: Bot token for Slack API access
- `SLACK_ENABLED`: Toggle notifications on/off
- `ADMIN_SLACK_EMAIL`: Admin email for error notifications
- User Slack IDs are automatically discovered and cached via email lookup

### Notification Types and Timing

#### 📅 **Scheduled Notifications** (via `scheduler.py`)
- **Due Date Reminders**: Sent 3 days before return deadline
  - Includes extension availability information
  - Warns if reservations prevent extension
  - Provides direct links to extend loan

#### 📚 **Book Transaction Notifications**
- **Loan Confirmation**: When user borrows a book
- **Return Confirmation**: When user returns a book
- **Extension Confirmation**: When loan period is extended

#### 📋 **Reservation System Notifications**
- **Reservation Created**: Confirmation to user who made reservation
- **Reservation Alert**: Warns current borrower of new reservation (prevents extension)
- **Book Available**: Notifies next reservation holder when book becomes available
- **Reservation Cancelled**: Confirmation of cancellation

#### 🚨 **System Notifications**
- **Error Alerts**: Critical system errors sent to admin
- **Overdue Warnings**: Included in due date reminders

### Message Features
- **Direct Messages**: All notifications sent as personal DMs
- **Rich Formatting**: Slack markdown with emojis and formatting
- **Action Links**: Direct URLs to relevant pages (book details, extension forms)
- **Contextual Information**: Due dates, queue positions, borrower names
- **Bilingual Support**: Messages in Japanese for user-friendly experience

### Background Tasks
The scheduler runs automated tasks including:
- Due date reminder processing (3-day advance)
- Expired reservation cleanup (7-day grace period)
- Slack notification delivery with retry logic

## Common Development Patterns

### Adding New Features
1. Create/update models in `models.py`
2. Generate and apply database migration
3. Create forms in `forms/` directory
4. Implement business logic in `services/`
5. Add routes in appropriate blueprint (`routes/`)
6. Create templates in `templates/`

### Loan System Business Rules
- **Loan limit enforcement**: Check current loans + reservations ≤ max_loan_limit
- **Overdue restrictions**: Block new loans if user has any overdue books  
- **Extension validation**: Verify no pending reservations before allowing extension
- **Due date options**: Default 2 weeks, with custom date selection available

### Error Handling
- 404/500 error pages are customized
- Database rollback on errors
- Comprehensive logging to `logs/library.log`

## Troubleshooting

### HTTPS Redirect Issues
If HTTP is being redirected to HTTPS in development:
- Check `FLASK_ENV` is set to `development`
- Clear browser cache/try incognito mode
- Verify `force_https=is_production` in Talisman configuration

### Docker Issues
- Restart Docker Desktop if commands fail
- Use `docker-compose ps` to check container status
- Ensure commands run from project root directory

### Module Import Errors
- Use `PYTHONPATH=/app` when running custom scripts in container
- Ensure proper imports from project modules