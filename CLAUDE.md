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
├── email_service.py
└── notifications.py

forms/              # WTForms for input validation
utils/              # Utility functions and decorators
templates/          # Jinja2 HTML templates
static/             # CSS, JS, and static assets
```

### Database Models
- **User**: Authentication, profiles, admin flags
- **Book**: Title, author, categories, status, availability  
- **LoanHistory**: Borrowing records with due dates and return tracking
- **Reservation**: Queue-based book reservation system
- **OperationLog**: Audit trail for all system operations

### Key Features
- Argon2 password hashing for security
- Flask-Login for session management
- Flask-Migrate for database versioning
- Rate limiting with Flask-Limiter
- Security headers via Flask-Talisman
- Email notifications for due dates and reservations
- CSV import/export functionality
- Comprehensive audit logging

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
- Default admin user: `admin` / `change_me_immediately`
- Password can be reset via CLI command or environment variable

## Common Development Patterns

### Adding New Features
1. Create/update models in `models.py`
2. Generate and apply database migration
3. Create forms in `forms/` directory
4. Implement business logic in `services/`
5. Add routes in appropriate blueprint (`routes/`)
6. Create templates in `templates/`

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