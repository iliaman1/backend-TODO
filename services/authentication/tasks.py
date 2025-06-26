from celery import Celery
import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

app = Celery(
    'email_task',
    broker=f'redis://{os.getenv("REDIS_HOST")}:{os.getenv("REDIS_PORT")}/0',
    backend=f'redis://{os.getenv("REDIS_HOST")}:{os.getenv("REDIS_PORT")}/0'
)

@app.task
def send_email():
    msg = MIMEText("Привет! Это письмо отправлено из Docker-контейнера.")
    msg['Subject'] = 'Уведомление (Celery + Docker)'
    msg['From'] = os.getenv("EMAIL_ADDRESS")
    msg['To'] = os.getenv("RECIPIENT_EMAIL")

    try:
        with smtplib.SMTP(os.getenv("SMTP_SERVER"), os.getenv("SMTP_PORT")) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_PASSWORD"))
            server.send_message(msg)
            return "Письмо отправлено!"
    except Exception as e:
        return f"Ошибка: {e}"