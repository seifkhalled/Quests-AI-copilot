import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

celery_app = Celery(
    "ai_knowledge",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
)