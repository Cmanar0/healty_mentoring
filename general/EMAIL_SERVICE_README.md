# Email Service Documentation

## Overview

The `general/email_service.py` module provides a universal email service for sending transactional emails throughout the Django application. All emails use consistent branding and templates located in `general/templates/emails/`.

## Email Configuration

Email settings are configured in `.env`:

- `EMAIL_HOST`: SMTP server (e.g., `smtppro.zoho.eu`)
- `EMAIL_PORT`: SMTP port (e.g., `465`)
- `EMAIL_HOST_USER`: SMTP username
- `EMAIL_HOST_PASSWORD`: SMTP password
- `EMAIL_USE_TLS`: Use TLS (True/False)
- `EMAIL_USE_SSL`: Use SSL (True/False)
- `DEFAULT_FROM_EMAIL`: Default sender email address
- `SITE_DOMAIN`: Base URL for building absolute links in emails

## Usage

### Basic Usage

```python
from general.email_service import EmailService

# Send a custom email
EmailService.send_email(
    subject="Your Subject",
    recipient_email="user@example.com",
    template_name="verification",  # Uses general/templates/emails/verification.html
    context={
        'user': user,
        'custom_variable': 'value',
    }
)
```

### Pre-built Email Methods

#### Email Verification

```python
from general.email_service import EmailService

verify_url = "https://example.com/verify/token/"
EmailService.send_verification_email(user, verify_url)
```

#### Password Reset

```python
from general.email_service import EmailService

reset_url = "https://example.com/reset/token/"
EmailService.send_password_reset_email(user, reset_url)
```

#### Welcome Email

```python
from general.email_service import EmailService

EmailService.send_welcome_email(user)
```

## Email Templates

All email templates are located in `general/templates/emails/`:

- **base.html**: Base template with branding and styling
- **verification.html**: Email verification template
- **password_reset.html**: Password reset template
- **welcome.html**: Welcome email template

### Creating New Email Templates

1. Create a new template in `general/templates/emails/your_template.html`
2. Extend the base template: `{% extends "emails/base.html" %}`
3. Override the `content` block with your email content
4. Use the email service to send:

```python
EmailService.send_email(
    subject="Your Subject",
    recipient_email="user@example.com",
    template_name="your_template",
    context={'variable': 'value'}
)
```

## Template Context

The following context variables are automatically available in all email templates:

- `site_domain`: Base URL from `SITE_DOMAIN` env variable
- `site_name`: "Healthy Mentoring"

Additional context can be passed via the `context` parameter when calling `send_email()`.

## Current Implementation

The email service is currently used for:

- ✅ Email verification on user registration (`accounts/views.py`)

Future enhancements could include:

- Password reset emails (currently using Django's default)
- Welcome emails after verification
- Session reminders
- Account notifications
