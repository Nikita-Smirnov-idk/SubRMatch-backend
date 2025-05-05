from celery import Celery
from services.email.mail import create_message, mail
from asgiref.sync import async_to_sync

c_app = Celery()

c_app.config_from_object("core.config")


@c_app.task()
def send_email(recipients: list[str], subject: str, body: dict, template_name: str):

    message = create_message(recipients=recipients, subject=subject, body=body)

    async_to_sync(mail.send_message)(message, template_name=template_name)