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
def send_email(token: str = ""):
    msg = MIMEText(
        f"Привет! Это письмо отправлено из Docker-контейнера. "
        f"Для подтверждения почты перейдите по ссылке. "
        f"http://localhost:8080/api/auth/verify-email?token={token}"
    )
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


@app.task
def send_password_reset_email(email: str, token: str):
    msg = MIMEText(
        f"Здравствуйте,\n\nВы получили это письмо, потому что запросили сброс пароля для вашей учетной записи.\n"
        f"Пожалуйста, перейдите по следующей ссылке, чтобы сбросить пароль: \n"
        f"http://localhost:8080/api/auth/password-reset?token={token}\n\n"
        f"Если вы не запрашивали сброс пароля, проигнорируйте это письмо.\n\n"
        f"С уважением,\nКоманда поддержки"
    )
    msg["Subject"] = "Сброс пароля"
    msg["From"] = getenv("EMAIL_ADDRESS")
    msg["To"] = getenv("EMAIL_ADDRESS")

    try:
        with smtplib.SMTP(getenv("SMTP_SERVER"), getenv("SMTP_PORT")) as server:
            server.starttls()
            server.login(getenv("EMAIL_ADDRESS"), getenv("EMAIL_PASSWORD"))
            server.send_message(msg)
            return "Письмо для сброса пароля отправлено!"
    except Exception as e:
        return f"Ошибка: {e}"
