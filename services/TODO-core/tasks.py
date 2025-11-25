import smtplib
from email.mime.text import MIMEText
from os import getenv

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Инициализация Celery
app = Celery(
    "todo_core_tasks",
    broker=f'redis://{getenv("REDIS_HOST")}:{getenv("REDIS_PORT")}/0',
    backend=f'redis://{getenv("REDIS_HOST")}:{getenv("REDIS_PORT")}/0',
)


@app.task
def send_invitation_email(recipient_email: str, project_name: str, token: str):
    """
    Задача Celery для отправки письма с приглашением на проект.
    """
    msg_body = (
        f"Здравствуйте!\n\n"
        f"Вас пригласили присоединиться к проекту '{project_name}'.\n"
        f"Для принятия приглашения отправьте POST-запрос к нашему API, используя следующий токен:\n\n"
        f"API Endpoint: POST http://localhost:8080/api/core/invitations/accept/\n"
        f"Content-Type: application/json\n"
        f"Body: {{\n"
        f'    "token": "{token}"\n'
        f"}}\n\n"
        f"Если вы не ожидали этого приглашения, просто проигнорируйте это письмо.\n\n"
        f"С уважением,\nВаша команда"
    )

    msg = MIMEText(msg_body)
    msg["Subject"] = f"Приглашение в проект '{project_name}'"
    msg["From"] = getenv("EMAIL_ADDRESS")
    msg["To"] = getenv("EMAIL_ADDRESS")

    try:
        with smtplib.SMTP(getenv("SMTP_SERVER"), int(getenv("SMTP_PORT"))) as server:
            server.starttls()
            server.login(getenv("EMAIL_ADDRESS"), getenv("EMAIL_PASSWORD"))
            server.send_message(msg)
            return f"Письмо с приглашением отправлено на {recipient_email}"
    except Exception as e:
        return f"Ошибка: {e}"
