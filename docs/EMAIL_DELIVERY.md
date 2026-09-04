# OWNEX Email Delivery Guide

## Overview

OWNEX uses SMTP for transactional email delivery with priority headers, retry logic, and delivery tracking.

## Configuration

Set these environment variables in `.env`:

```bash
# SMTP Configuration
OWNEX_SMTP_HOST=smtp.gmail.com          # Your SMTP server
OWNEX_SMTP_PORT=587                      # SMTP port (587 for TLS, 465 for SSL)
OWNEX_SMTP_USER=your-email@gmail.com    # SMTP username
OWNEX_SMTP_PASSWORD=your-app-password    # SMTP password or app password
OWNEX_SMTP_FROM=OWNEX <your@email.com>  # From address

# Recipient (configurable)
OWNEX_NOTIFICATION_EMAIL=user@example.com  # Where notifications are sent
```

## Priority Headers

OWNEX includes these headers for priority emails:

| Priority | Importance | X-Priority | X-MSMail-Priority |
|----------|------------|------------|-------------------|
| critical | high | 1 | High |
| high | high | 1 | High |
| medium | normal | 3 | Normal |
| low | low | 5 | Low |

**Important:** These are RFC-compliant headers. The email client (Gmail, Outlook, Apple Mail) decides how to display priority. OWNEX cannot force any client to show an "Important" label.

## Deliverability: SPF + DKIM + DMARC

For maximum deliverability, configure these DNS records on your email domain:

### SPF (Sender Policy Framework)

Add this TXT record to your DNS:

```
v=spf1 include:_spf.google.com ~all
```

For Gmail/Google Workspace:
```
v=spf1 include:_spf.google.com ~all
```

For custom SMTP:
```
v=spf1 ip4:your.smtp.server.ip ~all
```

### DKIM (DomainKeys Identified Mail)

1. Generate a DKIM key pair
2. Add the public key as a TXT record:
```
selector._domainkey.yourdomain.com TXT "v=DKIM1; k=rsa; p=YOUR_PUBLIC_KEY"
```

### DMARC (Domain-based Message Authentication)

Add this TXT record:
```
_dmarc.yourdomain.com TXT "v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com"
```

## Gmail Setup

For Gmail, you need an App Password:

1. Enable 2-Factor Authentication on your Google account
2. Go to https://myaccount.google.com/apppasswords
3. Create an app password for "Mail"
4. Use that password in `OWNEX_SMTP_PASSWORD`

## Testing

### Test Email Delivery

```python
from cores.notifications.email import get_email_adapter

adapter = get_email_adapter()
if adapter.is_enabled:
    success = adapter.send(
        title="Test Notification",
        message="<p>This is a test email from OWNEX.</p>",
        priority="high",
    )
    print(f"Delivery: {'OK' if success else 'FAILED'}")
    print(f"Stats: {adapter.get_delivery_stats()}")
else:
    print("Email not configured — set OWNEX_SMTP_HOST and OWNEX_NOTIFICATION_EMAIL")
```

### Check Delivery History

```python
adapter = get_email_adapter()
history = adapter.get_delivery_history(limit=10)
for record in history:
    print(f"{record['subject']} -> {record['to']}: {'✓' if record['success'] else '✗'}")
```

## Retry Logic

OWNEX retries failed emails up to 3 times with exponential backoff:
- Attempt 1: immediate
- Attempt 2: 5 seconds
- Attempt 3: 10 seconds

## Audit Trail

All email deliveries are tracked in memory with:
- Recipient
- Subject
- Priority
- Success/failure status
- Error message (if failed)
- Timestamp

## Troubleshooting

### "Email disabled"
- Set `OWNEX_SMTP_HOST` and `OWNEX_NOTIFICATION_EMAIL`

### "Connection refused"
- Check SMTP host and port
- Verify firewall allows outbound SMTP

### "Authentication failed"
- Check username and password
- For Gmail, use App Password (not regular password)

### "Emails going to spam"
- Configure SPF, DKIM, DMARC
- Use a consistent "From" address
- Avoid spam-trigger words in subject

## Architecture

```
NotificationService
        │
        ├── EmailAdapter (SMTP)
        │       ├── Priority Headers
        │       ├── Retry Logic
        │       └── Delivery Tracking
        │
        ├── InApp (NotificationHub)
        │
        └── Future: WhatsApp, Telegram, etc.
```
