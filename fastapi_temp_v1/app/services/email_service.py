import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PermanentEmailError(Exception):
    """The email cannot be delivered without changing configuration or input."""


class TemporaryEmailError(Exception):
    """The email delivery failure may be resolved by retrying."""


def build_verification_url(token: str) -> str:
    base_url = settings.email_verification_base_url.rstrip("/")
    query = urlencode({"token": token})
    return f"{base_url}/verify-email?{query}"


def send_verification_email(
    *,
    recipient: str,
    full_name: str,
    token: str,
) -> None:
    verification_url = build_verification_url(token)

    subject = "Verify your email address"
    body = (
        f"Hello {full_name},\n\n"
        "Thank you for registering.\n"
        "Please verify your email address using this link:\n\n"
        f"{verification_url}\n\n"
        f"This link expires in "
        f"{settings.email_verification_token_minutes} minutes.\n\n"
        "If you did not create this account, you can ignore this email."
    )

    if settings.email_provider == "console":
        # Never print the raw token or verification URL.
        logger.info(
            "Console email provider selected for recipient=%s. "
            "Email content is not sent to an actual mailbox.",
            recipient,
        )
        print(
            "\n--- DEVELOPMENT EMAIL ---\n"
            f"To: {recipient}\n"
            f"Subject: {subject}\n"
            f"Body:\n{body}\n"
            "--- END DEVELOPMENT EMAIL ---\n"
        )
        return

    if settings.email_provider != "smtp":
        raise PermanentEmailError("Unsupported email provider.")

    if not settings.smtp_host:
        raise PermanentEmailError("SMTP_HOST is not configured.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.email_from
    message["To"] = recipient
    message.set_content(body)

    try:
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=15,
        ) as smtp:
            smtp.ehlo()

            if settings.smtp_use_tls:
                smtp.starttls()
                smtp.ehlo()

            if settings.smtp_username:
                if not settings.smtp_password:
                    raise PermanentEmailError(
                        "SMTP_PASSWORD is required when SMTP_USERNAME is set."
                    )

                smtp.login(
                    settings.smtp_username,
                    settings.smtp_password.get_secret_value(),
                )

            smtp.send_message(message)

    except PermanentEmailError:
        raise
    except smtplib.SMTPAuthenticationError as exc:
        raise PermanentEmailError(
            "SMTP authentication failed; check provider credentials."
        ) from exc
    except smtplib.SMTPRecipientsRefused as exc:
        raise PermanentEmailError(
            "The email provider refused the recipient."
        ) from exc
    except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected,
            TimeoutError, OSError) as exc:
        raise TemporaryEmailError(
            "The email provider is temporarily unreachable."
        ) from exc
    except smtplib.SMTPResponseException as exc:
        if 400 <= exc.smtp_code < 500:
            raise TemporaryEmailError(
                "The email provider returned a temporary error."
            ) from exc

        raise PermanentEmailError(
            "The email provider rejected the message."
        ) from exc