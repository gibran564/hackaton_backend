"""
Configuración de la aplicación Celery para tareas asíncronas y programadas.

Define la instancia del worker, la serialización de mensajes y
el calendario de tareas periódicas (beat schedule).
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "restaurant_bi",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "reentrenar-burbujas-diario": {
            "task": "app.tasks.tasks.reentrenar_modelos_bubble",
            "schedule": 86400,
        },
        "generar-reporte-diario": {
            "task": "app.tasks.tasks.generar_reporte_diario",
            "schedule": 86400,
        },
    },
)
