import smtplib
from datetime import date
from email.mime.text import MIMEText
from os import getenv

import requests
from celery import Celery
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Инициализация Celery
app = Celery(
    "todo_core_tasks",
    broker=f'redis://{getenv("REDIS_HOST")}:{getenv("REDIS_PORT")}/0',
    backend=f'redis://{getenv("REDIS_HOST")}:{getenv("REDIS_PORT")}/0',
)
# Указываем Django как источник конфигурации
app.config_from_object("django.conf:settings", namespace="CELERY")


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


@app.task
def send_email_task(recipient_email: str, subject: str, body: str):
    """
    Общая задача для отправки email.
    """
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = getenv("EMAIL_ADDRESS")
    msg["To"] = getenv("EMAIL_ADDRESS")  # recipient_email

    try:
        with smtplib.SMTP(getenv("SMTP_SERVER"), int(getenv("SMTP_PORT"))) as server:
            server.starttls()
            server.login(getenv("EMAIL_ADDRESS"), getenv("EMAIL_PASSWORD")),
            server.send_message(msg)
            return f"Письмо на тему '{subject}' отправлено на {recipient_email}"
    except Exception as e:
        print(f"Ошибка при отправке письма: {e}")
        raise


@app.task
def send_invitation_email(recipient_email: str, project_name: str, token: str):
    """
    Задача для отправки письма с приглашением на проект.
    """
    subject = f"Приглашение в проект '{project_name}'"
    body = (
        f"Здравствуйте!\n\n"
        f"Вас пригласили присоединиться к проекту '{project_name}'.\n"
        f"Для принятия приглашения отправьте POST-запрос к нашему API, используя следующий токен:\n\n"
        f"API Endpoint: POST http://localhost:8080/api/core/invitations/accept/\n"
        f"Content-Type: application/json\n"
        f'Body: {{ "token": "{token}" }}\n\n'
        f"С уважением,\nВаша команда"
    )
    send_email_task.delay(recipient_email=recipient_email, subject=subject, body=body)


@app.task
def send_deadline_notification(
    task_title: str, project_name: str, recipient_email: str
):
    """
    Задача для отправки уведомления о дедлайне.
    """
    subject = f"Напоминание о дедлайне: {task_title}"
    body = (
        f"Здравствуйте!\n\n"
        f"Напоминаем, что сегодня в 17:00 истекает срок выполнения задачи "
        f"'{task_title}' в проекте '{project_name}'.\n\n"
        f"Пожалуйста, убедитесь, что задача будет выполнена вовремя.\n\n"
        f"С уважением,\nВаша команда"
    )
    send_email_task.delay(recipient_email=recipient_email, subject=subject, body=body)


@app.task
def check_upcoming_deadlines():
    """
    Периодическая задача для проверки дедлайнов.
    Находит все задачи, у которых дедлайн сегодня, и отправляет уведомление владельцу и участникам проекта.
    """
    # Импортируем модели Django внутри задачи, чтобы избежать циклических импортов
    from apps.project.models import Task

    today = date.today()
    tasks_due_today = Task.objects.filter(due_date=today).select_related("project")

    if not tasks_due_today:
        print("No tasks due today.")
        return

    # Собираем ID всех пользователей, которых нужно уведомить
    all_user_ids = set()
    for task in tasks_due_today:
        all_user_ids.add(task.project.owner_id)
        all_user_ids.update(task.project.members)

    if not all_user_ids:
        print("No users to notify.")
        return

    # Получаем SERVICE_TOKEN для внутреннего запроса
    service_token = getenv("SERVICE_TOKEN")
    if not service_token:
        print("SERVICE_TOKEN not found, cannot fetch user emails.")
        return

    headers = {"Authorization": f"Bearer {service_token}"}
    auth_service_url = getenv("AUTH_SERVICE_URL")

    try:
        response = requests.post(
            f"{auth_service_url}/internal/users/by_ids",
            json={"user_ids": list(all_user_ids)},
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        users_data = {user["id"]: user["email"] for user in response.json()}
    except requests.RequestException as e:
        print(f"Could not fetch user emails from auth service: {e}")
        return

    # Рассылаем уведомления
    for task in tasks_due_today:
        recipients_ids = {task.project.owner_id} | set(task.project.members)
        for user_id in recipients_ids:
            recipient_email = users_data.get(user_id)
            if recipient_email:
                send_deadline_notification.delay(
                    task_title=task.title,
                    project_name=task.project.name,
                    recipient_email=recipient_email,
                )
            else:
                print(f"Could not find email for user_id {user_id}")
