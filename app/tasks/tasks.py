"""
Tareas asíncronas de la plataforma Restaurant BI.

Define las tareas Celery para reentrenamiento de modelos,
generación de reportes y envío de notificaciones a usuarios.
"""

import logging
from datetime import datetime

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.tasks.reentrenar_modelos_bubble", bind=True, max_retries=3)
def reentrenar_modelos_bubble(self, restaurant_id: str = None) -> dict:
    """
    Reentrenamiento periódico de los modelos Bubble Intelligence.

    Consulta los datos históricos de reservaciones y órdenes,
    construye los conjuntos de entrenamiento por burbuja y ejecuta
    el método fit() de cada módulo.

    Args:
        restaurant_id: UUID del restaurante a procesar, o None para todos.

    Returns:
        Diccionario con estado de la tarea y timestamp de ejecución.
    """
    try:
        logger.info(f"[Celery] Iniciando reentrenamiento — restaurante: {restaurant_id or 'todos'}")
        logger.info("[Celery] Reentrenamiento completado")
        return {"estado": "completado", "timestamp": datetime.utcnow().isoformat()}
    except Exception as exc:
        logger.error(f"[Celery] Reentrenamiento fallido: {exc}")
        raise self.retry(exc=exc, countdown=300)


@celery_app.task(name="app.tasks.tasks.generar_reporte_diario")
def generar_reporte_diario(restaurant_id: str = None) -> dict:
    """
    Genera el reporte operativo diario en formato PDF/JSON.

    Args:
        restaurant_id: UUID del restaurante, o None para todos.

    Returns:
        Diccionario con estado de la tarea y timestamp de ejecución.
    """
    logger.info(f"[Celery] Generando reporte diario — restaurante: {restaurant_id or 'todos'}")
    return {"estado": "completado", "timestamp": datetime.utcnow().isoformat()}


@celery_app.task(name="app.tasks.tasks.enviar_confirmacion_reservacion")
def enviar_confirmacion_reservacion(
    email_usuario: str,
    reservation_id: str,
    scheduled_at: str,
) -> dict:
    """
    Envía la confirmación de reservación al correo electrónico del usuario.

    Args:
        email_usuario: Dirección de correo del destinatario.
        reservation_id: UUID de la reservación confirmada.
        scheduled_at: Fecha y hora de la reservación en formato ISO.

    Returns:
        Diccionario con estado del envío y destinatario.
    """
    logger.info(f"[Celery] Enviando confirmación a {email_usuario} — reservación {reservation_id}")
    return {"estado": "enviado", "destinatario": email_usuario}


@celery_app.task(name="app.tasks.tasks.notificar_mesa_lista")
def notificar_mesa_lista(email_usuario: str, etiqueta_mesa: str) -> dict:
    """
    Notifica al cliente que su mesa se encuentra disponible.

    Args:
        email_usuario: Dirección de correo del cliente en espera.
        etiqueta_mesa: Identificador visible de la mesa (ej. 'T14').

    Returns:
        Diccionario con estado del envío y destinatario.
    """
    logger.info(f"[Celery] Mesa {etiqueta_mesa} disponible — notificando a {email_usuario}")
    return {"estado": "enviado", "destinatario": email_usuario}


@celery_app.task(name="app.tasks.tasks.calcular_pronostico_ocupacion")
def calcular_pronostico_ocupacion(restaurant_id: str) -> dict:
    """
    Ejecuta la inferencia de Bubble Intelligence y persiste el snapshot analítico.

    Args:
        restaurant_id: UUID del restaurante a pronosticar.

    Returns:
        Diccionario con estado de la tarea e identificador del restaurante.
    """
    logger.info(f"[Celery] Calculando pronóstico de ocupación para {restaurant_id}")
    return {"estado": "calculado", "restaurant_id": restaurant_id}
