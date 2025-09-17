import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# Sample user data
users = [
    {"name": "Alice", "email": "alice@example.com", "expiry_date": "2025-10-20"},
    {"name": "Bob", "email": "bob@example.com", "expiry_date": "2025-09-22"},
    {"name": "Charlie", "email": "charlie@example.com", "expiry_date": "2025-09-18"},
]

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "your_email@gmail.com"
SENDER_PASSWORD = "your_app_password"  # Use app-specific password for Gmail

def get_alert_level(days_left):
    if days_left > 30:
        return "Green", "🟢 No immediate action needed."
    elif 7 <= days_left <= 30:
        return "Yellow", "🟡 Please review soon."
    else:
        return "Red", "🔴 Action required! Expiring or expired."

def send_email(to_email, subject, message):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        print(f"Email sent to {to_email}")

def main():
    today = datetime.today()

    for user in users:
        expiry_date = datetime.strptime(user["expiry_date"], "%Y-%m-%d")
        days_left = (expiry_date - today).days

        color, alert_message = get_alert_level(days_left)

        email_subject = f"[{color}] Expiry Alert for {user['name']}"
        email_body = (
            f"Hello {user['name']},\n\n"
            f"Your expiry date is on {expiry_date.strftime('%Y-%m-%d')} "
            f"({days_left} days left).\n"
            f"{alert_message}\n\n"
            "Please take necessary action.\n\n"
            "Best regards,\nAlert System"
        )

        send_email(user["email"], email_subject, email_body)

if _name_ == "_main_":
    main()