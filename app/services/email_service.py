"""
Email Service

Handles sending emails via SMTP with configurable settings.
Configuration is managed through SystemSettings in super admin.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from flask import current_app

from app.models import SystemSetting


class EmailService:
    """Service for sending emails via configured SMTP"""

    @staticmethod
    def get_smtp_config():
        """
        Get SMTP configuration from system settings.

        Returns:
            dict with smtp_host, smtp_port, smtp_username, smtp_password,
            smtp_use_tls, smtp_use_ssl, from_email, from_name
        """
        config = {
            "smtp_host": SystemSetting.get_value("smtp_host"),
            "smtp_port": SystemSetting.get_value("smtp_port", default=587),
            "smtp_username": SystemSetting.get_value("smtp_username"),
            "smtp_password": SystemSetting.get_value("smtp_password"),
            "smtp_use_tls": SystemSetting.get_bool("smtp_use_tls", default=True),
            "smtp_use_ssl": SystemSetting.get_bool("smtp_use_ssl", default=False),
            "from_email": SystemSetting.get_value("smtp_from_email"),
            "from_name": SystemSetting.get_value("smtp_from_name", default="CISK Navigator"),
        }

        return config

    @staticmethod
    def is_configured():
        """Check if email service is configured"""
        config = EmailService.get_smtp_config()
        return bool(
            config["smtp_host"] and config["smtp_username"] and config["smtp_password"] and config["from_email"]
        )

    @staticmethod
    def send_email(
        to_emails: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
    ) -> bool:
        """
        Send an email via configured SMTP.

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body_text: Plain text body
            body_html: Optional HTML body
            cc_emails: Optional list of CC recipients
            bcc_emails: Optional list of BCC recipients

        Returns:
            True if sent successfully, False otherwise
        """
        if not EmailService.is_configured():
            current_app.logger.error("Email service not configured")
            return False

        config = EmailService.get_smtp_config()

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{config['from_name']} <{config['from_email']}>"
            msg["To"] = ", ".join(to_emails)
            msg["Subject"] = subject

            if cc_emails:
                msg["Cc"] = ", ".join(cc_emails)

            # Attach plain text
            msg.attach(MIMEText(body_text, "plain"))

            # Attach HTML if provided
            if body_html:
                msg.attach(MIMEText(body_html, "html"))

            # Combine all recipients
            all_recipients = to_emails.copy()
            if cc_emails:
                all_recipients.extend(cc_emails)
            if bcc_emails:
                all_recipients.extend(bcc_emails)

            # Connect to SMTP server
            smtp_port = int(config["smtp_port"])

            if config["smtp_use_ssl"]:
                # SSL connection (port 465)
                server = smtplib.SMTP_SSL(config["smtp_host"], smtp_port)
            else:
                # Regular connection with optional TLS (port 587 or 25)
                server = smtplib.SMTP(config["smtp_host"], smtp_port)
                if config["smtp_use_tls"]:
                    server.starttls()

            # Login
            server.login(config["smtp_username"], config["smtp_password"])

            # Send email
            server.sendmail(config["from_email"], all_recipients, msg.as_string())

            # Close connection
            server.quit()

            current_app.logger.info(f"Email sent successfully to {to_emails}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            current_app.logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            current_app.logger.error(f"SMTP error sending email: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Error sending email: {e}")
            return False

    @staticmethod
    def send_test_email(to_email: str) -> bool:
        """
        Send a test email to verify configuration.

        Args:
            to_email: Email address to send test to

        Returns:
            True if sent successfully, False otherwise
        """
        subject = "CISK Navigator - Test Email"
        body_text = """
This is a test email from CISK Navigator.

If you received this email, your email configuration is working correctly!

Best regards,
CISK Navigator Team
        """

        body_html = """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #3182ce;">CISK Navigator - Test Email</h2>
    <p>This is a test email from CISK Navigator.</p>
    <p>If you received this email, your email configuration is working correctly! ✅</p>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
    <p style="color: #666; font-size: 0.9em;">
        Best regards,<br>
        <strong>CISK Navigator Team</strong>
    </p>
</body>
</html>
        """

        return EmailService.send_email([to_email], subject, body_text, body_html)

    @staticmethod
    def send_mention_notification(user_email: str, user_name: str, comment_text: str, kpi_name: str, comment_url: str):
        """
        Send notification when user is mentioned in a comment.

        Args:
            user_email: Email of mentioned user
            user_name: Name of mentioned user
            comment_text: Comment text
            kpi_name: KPI name where comment was made
            comment_url: URL to view the comment
        """
        # Check if mention notifications are enabled
        if not SystemSetting.get_bool("email_mention_notifications", default=False):
            return False

        subject = f"CISK Navigator - You were mentioned in {kpi_name}"

        body_text = f"""
Hi {user_name},

You were mentioned in a comment on {kpi_name}:

"{comment_text}"

View the comment: {comment_url}

Best regards,
CISK Navigator
        """

        body_html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #3182ce;">You were mentioned in a comment</h2>
    <p>Hi <strong>{user_name}</strong>,</p>
    <p>You were mentioned in a comment on <strong>{kpi_name}</strong>:</p>
    <blockquote style="border-left: 4px solid #3182ce; padding-left: 15px; margin: 20px 0; color: #555;">
        {comment_text}
    </blockquote>
    <p>
        <a href="{comment_url}" style="background: #3182ce; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
            View Comment
        </a>
    </p>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
    <p style="color: #666; font-size: 0.9em;">
        Best regards,<br>
        <strong>CISK Navigator</strong>
    </p>
</body>
</html>
        """

        return EmailService.send_email([user_email], subject, body_text, body_html)

    @staticmethod
    def send_action_item_assigned(
        user_email: str, user_name: str, action_title: str, action_description: str, due_date: str, action_url: str
    ):
        """
        Send notification when action item is assigned to user.

        Args:
            user_email: Email of assigned user
            user_name: Name of assigned user
            action_title: Action item title
            action_description: Action item description
            due_date: Due date string
            action_url: URL to view action item
        """
        # Check if action notifications are enabled
        if not SystemSetting.get_bool("email_action_notifications", default=False):
            return False

        subject = f"CISK Navigator - Action Item Assigned: {action_title}"

        body_text = f"""
Hi {user_name},

You have been assigned a new action item:

Title: {action_title}
Due Date: {due_date}

Description:
{action_description}

View action item: {action_url}

Best regards,
CISK Navigator
        """

        body_html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #3182ce;">Action Item Assigned</h2>
    <p>Hi <strong>{user_name}</strong>,</p>
    <p>You have been assigned a new action item:</p>
    <div style="background: #f8f9fa; border-left: 4px solid #3182ce; padding: 15px; margin: 20px 0;">
        <h3 style="margin-top: 0; color: #3182ce;">{action_title}</h3>
        <p><strong>Due Date:</strong> {due_date}</p>
        <p>{action_description}</p>
    </div>
    <p>
        <a href="{action_url}" style="background: #3182ce; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
            View Action Item
        </a>
    </p>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
    <p style="color: #666; font-size: 0.9em;">
        Best regards,<br>
        <strong>CISK Navigator</strong>
    </p>
</body>
</html>
        """

        return EmailService.send_email([user_email], subject, body_text, body_html)
