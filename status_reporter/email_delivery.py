import logging
import smtplib
import ssl
import time
from dataclasses import dataclass
from email.message import EmailMessage

from .config import Settings
from .models import Report
from .rendering import render_report, render_subject

LOGGER = logging.getLogger(__name__)


class DeliveryError(RuntimeError):
    """Raised when a configured email could not be delivered."""


@dataclass(frozen=True)
class DeliveryResult:
    outcome: str
    accepted_count: int
    failed_count: int


def send_report(report: Report, settings: Settings) -> DeliveryResult:
    if not (
        settings.smtp_host and settings.smtp_sender and settings.smtp_recipients
    ):
        raise DeliveryError(
            "SMTP_HOST, SMTP_SENDER, and SMTP_RECIPIENTS are required to send email."
        )

    accepted_count = 0
    failed_count = 0
    for recipient in settings.smtp_recipients:
        message = EmailMessage()
        message["Subject"] = render_subject(report)
        message["From"] = settings.smtp_sender
        message["To"] = recipient
        message.set_content(render_report(report, settings.due_soon_days))
        delivered = False

        for attempt in range(1, settings.smtp_max_retries + 1):
            client = _connect(settings)
            try:
                with client:
                    if settings.smtp_use_ssl:
                        _authenticate(client, settings)
                    else:
                        if settings.smtp_starttls:
                            client.starttls(context=ssl.create_default_context())
                        _authenticate(client, settings)

                    try:
                        refused = client.send_message(
                            message, to_addrs=[recipient]
                        )
                    except smtplib.SMTPResponseException as error:
                        if (
                            400 <= error.smtp_code < 500
                            and attempt < settings.smtp_max_retries
                        ):
                            delay = min(2 ** (attempt - 1), 30)
                            LOGGER.warning(
                                "Temporary SMTP failure for one recipient "
                                "(status %s); retrying attempt %s/%s after %.1f seconds.",
                                error.smtp_code,
                                attempt + 1,
                                settings.smtp_max_retries,
                                delay,
                            )
                            time.sleep(delay)
                            continue
                        LOGGER.warning(
                            "SMTP rejected one recipient (status %s).",
                            error.smtp_code,
                        )
                        break
                    except smtplib.SMTPRecipientsRefused as error:
                        response_codes = [
                            response[0]
                            for response in error.recipients.values()
                            if isinstance(response, tuple)
                            and response
                            and isinstance(response[0], int)
                        ]
                        if (
                            response_codes
                            and all(400 <= code < 500 for code in response_codes)
                            and attempt < settings.smtp_max_retries
                        ):
                            delay = min(2 ** (attempt - 1), 30)
                            LOGGER.warning(
                                "Temporary SMTP rejection for one recipient; "
                                "retrying attempt %s/%s after %.1f seconds.",
                                attempt + 1,
                                settings.smtp_max_retries,
                                delay,
                            )
                            time.sleep(delay)
                            continue
                        LOGGER.warning(
                            "SMTP refused one recipient; continuing with remaining recipients."
                        )
                        break
                    except (OSError, smtplib.SMTPException) as error:
                        raise DeliveryError(
                            "Email delivery had an ambiguous transport failure; "
                            "not retrying to avoid duplicate messages."
                        ) from error

                    if refused:
                        LOGGER.warning(
                            "SMTP refused one recipient; continuing with remaining recipients."
                        )
                    else:
                        accepted_count += 1
                        delivered = True
                    break
            except DeliveryError:
                raise
            except (OSError, smtplib.SMTPException) as error:
                raise DeliveryError(
                    f"Email connection or authentication failed ({type(error).__name__})."
                ) from error

        if not delivered:
            failed_count += 1

    if accepted_count == 0:
        raise DeliveryError(
            f"Email delivery was refused for all {failed_count} configured recipient(s)."
        )
    outcome = "Success With Warnings" if failed_count else "Success"
    return DeliveryResult(outcome, accepted_count, failed_count)


def _connect(settings: Settings) -> smtplib.SMTP:
    for attempt in range(1, settings.smtp_max_retries + 1):
        try:
            if settings.smtp_use_ssl:
                return smtplib.SMTP_SSL(
                    settings.smtp_host,
                    settings.smtp_port,
                    timeout=20,
                    context=ssl.create_default_context(),
                )
            return smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=20
            )
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
    raise DeliveryError("Could not connect to the email server.")


def _authenticate(client: smtplib.SMTP, settings: Settings) -> None:
    if settings.smtp_username and settings.smtp_password:
        client.login(settings.smtp_username, settings.smtp_password)
