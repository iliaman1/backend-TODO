import smtplib
from email.mime.text import MIMEText
from os import getenv

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

app = Celery(
    "email_task",
    broker=f'redis://{getenv("REDIS_HOST")}:{getenv("REDIS_PORT")}/0',
    backend=f'redis://{getenv("REDIS_HOST")}:{getenv("REDIS_PORT")}/0',
)


@app.task
def send_email():
    msg = MIMEText("Привет! Это письмо отправлено из Docker-контейнера.")
    msg["Subject"] = "Уведомление (Celery + Docker)"
    msg["From"] = getenv("EMAIL_ADDRESS")
    msg["To"] = getenv("RECIPIENT_EMAIL")

    try:
        with smtplib.SMTP(getenv("SMTP_SERVER"), getenv("SMTP_PORT")) as server:
            server.starttls()
            server.login(getenv("EMAIL_ADDRESS"), getenv("EMAIL_PASSWORD"))
            server.send_message(msg)
            return "Письмо отправлено!"
    except Exception as e:
        return f"Ошибка: {e}"
