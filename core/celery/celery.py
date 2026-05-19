from celery import Celery

celery = Celery(
    "worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

celery.conf.timezone = "Asia/Kolkata"

celery.conf.beat_schedule = {
    "generate-monthly-bills-daily": {
        "task": "tasks.generate_monthly_bills",
        "schedule": 86400.0,   # every day
    },
}