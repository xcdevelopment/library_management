# Email Reminder Setup Guide

## Overview
The library management system now includes automated email reminders for:
1. **Book borrowing confirmation** - Sent immediately when a book is borrowed
2. **Due date reminder** - Sent 3 days before the return due date
3. **Reservation available** - Sent to the first person in queue when a reserved book is returned

## Email Configuration

### Environment Variables
Make sure these are set in your `.env` file:
```bash
# Email settings
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@domain.com
MAIL_PASSWORD=your-password
MAIL_DEFAULT_SENDER=your-email@domain.com
```

### Dependencies
Flask-Mail is included in requirements.txt and will be installed automatically.

## Running Email Reminders

### Automatic Due Date Reminders
To send reminder emails for books due in 3 days, run:
```bash
# Using the run_scheduler.py script
docker-compose exec web python run_scheduler.py

# Or directly
docker-compose exec -e PYTHONPATH=/app web python scheduler.py
```

### Setting up Cron Job (for production)
Add this to your system crontab to run daily at 9 AM:
```bash
0 9 * * * cd /path/to/library_management && docker-compose exec web python run_scheduler.py
```

## Email Templates
Email templates are located in `templates/emails/`:
- `borrow_confirmation.html/.txt` - Book borrowing confirmation
- `due_date_reminder.html/.txt` - Return due date reminder
- `reservation_available.html/.txt` - Reservation available notification

## Automatic Triggering
- **Borrowing emails**: Automatically sent when a book is borrowed
- **Return emails**: Automatically sent to next person in reservation queue when book is returned
- **Due date reminders**: Run scheduler manually or via cron job

## Testing
To test email functionality:
1. Ensure email credentials are correct in `.env`
2. Borrow a book (should trigger borrowing confirmation email)
3. Return a book that has reservations (should trigger reservation notification)
4. Run scheduler to test due date reminders

## Troubleshooting
- Check Docker logs: `docker-compose logs web`
- Check scheduler logs: `logs/scheduled_tasks.log`
- Verify email credentials and server settings
- Make sure the user has a valid email address in their profile