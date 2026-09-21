import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "devpulse.settings")

app = Celery("devpulse")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()