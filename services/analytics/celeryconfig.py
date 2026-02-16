from celery.schedules import crontab

beat_schedule = {
    # "collect_user_analytics_every_minute": {
    #     "task": "tasks.collect_user_analytics",
    #     "schedule": crontab(minute="*"),  # Каждую минуту для тестирования
    # },
}
