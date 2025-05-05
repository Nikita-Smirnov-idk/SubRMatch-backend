from fastapi_mail import FastMail, ConnectionConfig, MessageSchema, MessageType
from core.config import settings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USERNAME,
    MAIL_PASSWORD=settings.SMTP_PASSWORD,
    MAIL_FROM=settings.SMTP_USERNAME,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_HOST,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=Path(BASE_DIR, "../../templates"),
)

mail = FastMail(config=mail_config)


def create_message(recipients: list[str], subject: str, body: dict):

    message = MessageSchema(
        recipients=recipients, subject=subject, template_body=body, subtype=MessageType.html
    )

    return message