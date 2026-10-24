import logging
import smtplib
import ssl
import time
from email.message import EmailMessage

from .config import Settings
from .models import Report
from .rendering import render_report, render_subject

LOGGER = logging.getLogger(__name__)


class DeliveryError(RuntimeError):
    """Raised when a configured email could not be delivered."""


def send_report(report: Report, settings: Settings) -> None:
    if not (
        settings.smtp_host and settings.smtp_sender and settings.smtp_recipients
    ):
        raise DeliveryError(
            "SMTP_HOST, SMTP_SENDER, and SMTP_RECIPIENTS are required to send email."
        )
    message = EmailMessage()
    message["Subject"] = render_subject(report)
    message["From"] = settings.smtp_sender
    message["To"] = ", ".join(settings.smtp_recipients)
    message.set_content(render_report(report, settings.due_soon_days))

    for attempt in range(1, settings.smtp_max_retries + 1):
        try:
            if settings.smtp_use_ssl:
                client = smtplib.SMTP_SSL(
                    settings.smtp_host,
                    settings.smtp_port,
                    context=ssl.create_default_context(),
                )
            else:
                client = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
        except (OSError, smtplib.SMTPConnectError) as error:
            if attempt >= settings.smtp_max_retries:
                raise DeliveryError(
                    "Could not connect to the email server after transient retries."
                ) from error
            delay = min(2 ** (attempt - 1), 30)
            LOGGER.warning(
                "Email connection failed; retrying attempt %s/%s after %.1f seconds.",
                attempt + 1,
                settings.smtp_max_retries,
                delay,
            )
            time.sleep(delay)
            continue

        accepted = False
        try:
            with client:
                if settings.smtp_use_ssl:
                    _authenticate(client, settings)
                    refused = client.send_message(message)
                else:
                    if settings.smtp_starttls:
                        client.starttls(context=ssl.create_default_context())
                    _authenticate(client, settings)
                    refused = client.send_message(message)
                accepted = not refused
        except smtplib.SMTPResponseException as error:
            if accepted:
                LOGGER.warning(
                    "Email server accepted the report, but connection cleanup returned SMTP %s.",
                    error.smtp_code,
                )
                return
            if 400 <= error.smtp_code < 500 and attempt < settings.smtp_max_retries:
                delay = min(2 ** (attempt - 1), 30)
                LOGGER.warning(
                    "Email server returned SMTP %s; retrying attempt %s/%s after %.1f seconds.",
                    error.smtp_code,
                    attempt + 1,
                    settings.smtp_max_retries,
                    delay,
                )
                time.sleep(delay)
                continue
            raise DeliveryError(
                f"Email server returned SMTP status {error.smtp_code}."
            ) from error
        except (OSError, smtplib.SMTPException) as error:
            if accepted:
                LOGGER.warning(
                    "Email server accepted the report, but connection cleanup failed (%s).",
                    type(error).__name__,
                )
                return
            raise DeliveryError(
                f"Email delivery failed ({type(error).__name__})."
            ) from error
        if refused:
            raise DeliveryError(
                "Email server refused delivery to: " + ", ".join(sorted(refused))
            )
        return


def _authenticate(client: smtplib.SMTP, settings: Settings) -> None:
    if settings.smtp_username and settings.smtp_password:
        client.login(settings.smtp_username, settings.smtp_password)
