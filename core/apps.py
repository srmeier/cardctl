from celery.app.task import Task
from django.apps import AppConfig
from django.db.models.signals import post_migrate

from .tasks import update_references


def trigger_update_references(sender: AppConfig, **kwargs):
    if not isinstance(sender, CoreConfig):
        return

    update_references.delay()


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        post_migrate.connect(trigger_update_references)
