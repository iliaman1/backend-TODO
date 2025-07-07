from celery.schedules import crontab
from tasks import app

app.conf.beat_schedule = {
    "send-email-every-2-hours": {
        "task": "tasks.send_email",
        "schedule": crontab(minute=0, hour="*/2"),
    },
}
app.conf.timezone = "UTC"
