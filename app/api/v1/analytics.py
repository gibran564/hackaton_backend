from datetime import datetime
from typing import Any, AsyncGenerator, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.bubbles.meta_collapser import MetaCollapser
from app.db.session import COLECCIONES, obtener_db
from app.models import EstadoMesa, EstadoOrden, EstadoReservacion, Mesa, Orden, Piso, Reservacion
from app.schemas import SalidaInsightBubble, SolicitudAnaliticos

router = APIRouter(prefix="/analiticos", tags=["Analíticos"])
_collapser = MetaCollapser()


async def _mesas_restaurante(db, restaurant_id: str) -> list:
    pisos = await db.listar(COLECCIONES["floors"], Piso, [("restaurant_id", "==", restaurant_id)])
    ids_pisos = {p.id for p in pisos}
    if not ids_pisos:
        return []
    mesas = await db.listar(COLECCIONES["tables"], Mesa)
    return [m for m in mesas if m.floor_id in ids_pisos]


def _metricas_ordenes(ordenes: list) -> Dict[str, float]:
    if not ordenes:
        return {"avg_order_value": 0.40, "kitchen_queue_depth": 0.0,
                "avg_prep_time": 0.30, "order_error_rate": 0.05}
    TICKET_MAX = 500.0
    totales = [getattr(o, "total", 0.0) or 0.0 for o in ordenes]
    avg_valor = min(sum(totales) / (len(totales) * TICKET_MAX), 1.0)
    cola = len([o for o in ordenes if getattr(o, "status", None) in ("pending", "preparing")])
    return {
        "avg_order_value": round(avg_valor, 4),
        "kitchen_queue_depth": round(min(cola / 20.0, 1.0), 4),
        "avg_prep_time": 0.40,
        "order_error_rate": 0.05,
    }


def _metricas_reservaciones(reservaciones: list) -> Dict[str, float]:
    if not reservaciones:
        return {"cancellation_rate": 0.10, "return_rate": 0.40,
                "complaint_rate": 0.03, "avg_wait_time": 0.30}
    total = len(reservaciones)
    canceladas = len([r for r in reservaciones if getattr(r, "status", None) == "cancelled"])
    return {
        "cancellation_rate": round(min(canceladas / total, 1.0), 4),
        "return_rate": 0.45,
        "complaint_rate": 0.03,
        "avg_wait_time": 0.30,
    }


async def _construir_contexto(db, restaurant_id: str) -> Dict[str, Any]:
    ahora = datetime.utcnow()
    mesas = await _mesas_restaurante(db, restaurant_id)
    n_mesas = max(len(mesas), 1)
    ocupadas = sum(1 for m in mesas if m.status == EstadoMesa.ocupada)
    disponibles = sum(1 for m in mesas if m.status == EstadoMesa.disponible)
    tasa = ocupadas / n_mesas

    reservaciones = await db.listar(
        COLECCIONES["reservations"], Reservacion,
        [("restaurant_id", "==", restaurant_id)],
    )
    activas = [r for r in reservaciones if getattr(r, "status", None) in ("confirmed", "pending")]
    ordenes = await db.listar(
        COLECCIONES["orders"], Orden,
        [("status", "in", [EstadoOrden.pendiente.value, EstadoOrden.preparando.value])],
    )

    mo = _metricas_ordenes(ordenes)
    mr = _metricas_reservaciones(reservaciones)
    tod = (ahora.hour * 60 + ahora.minute) / 1440.0

    return {
        "time_of_day":           round(tod, 4),
        "day_of_week":           round(ahora.weekday() / 6.0, 4),
        "is_holiday":            0.0,
        "weather_score":         0.6,
        "local_events":          min(len(activas) / 30.0, 1.0),
        "avg_order_value":       mo["avg_order_value"],
        "top_category_ratio":    0.40,
        "alcohol_ratio":         0.20,
        "dessert_ratio":         0.15,
        "combo_rate":            0.25,
        "avg_prep_time":         mo["avg_prep_time"],
        "staff_load":            tasa,
        "kitchen_queue_depth":   mo["kitchen_queue_depth"],
        "order_error_rate":      mo["order_error_rate"],
        "table_turn_rate":       round(1.0 - disponibles / n_mesas, 4),
        "avg_rating":            0.80,
        "cancellation_rate":     mr["cancellation_rate"],
        "return_rate":           mr["return_rate"],
        "complaint_rate":        mr["complaint_rate"],
        "avg_wait_time":         mr["avg_wait_time"],
        "occupancy_ratio":       round(tasa, 4),
        "avg_table_utilization": round(tasa * 0.9, 4),
        "dead_zone_ratio":       0.10,
        "aisle_blockage":        0.05,
        "floor_score":           0.75,
    }


@router.post("/bubble-insight", response_model=SalidaInsightBubble)
async def obtener_insight_bubble(
    payload: SolicitudAnaliticos,
    db=Depends(obtener_db),
) -> SalidaInsightBubble:
    contexto = await _construir_contexto(db, payload.restaurant_id)
    return SalidaInsightBubble(**_collapser.ejecutar(contexto))


@router.post("/bubble-insight/stream",
             responses={200: {"content": {"text/event-stream": {}}}})
async def obtener_insight_bubble_stream(
    payload: SolicitudAnaliticos,
    db=Depends(obtener_db),
) -> StreamingResponse:
    contexto = await _construir_contexto(db, payload.restaurant_id)

    async def _gen() -> AsyncGenerator[str, None]:
        async for chunk in _collapser.ejecutar_stream(contexto):
            yield chunk

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/dashboard/{restaurant_id}")
async def resumen_dashboard(
    restaurant_id: str,
    db=Depends(obtener_db),
) -> dict:
    mesas = await _mesas_restaurante(db, restaurant_id)
    n = len(mesas)
    ocupadas = sum(1 for m in mesas if m.status == EstadoMesa.ocupada)
    disponibles = sum(1 for m in mesas if m.status == EstadoMesa.disponible)
    reservaciones = await db.listar(
        COLECCIONES["reservations"], Reservacion,
        [("restaurant_id", "==", restaurant_id),
         ("status", "!=", EstadoReservacion.cancelada.value)],
    )
    ordenes = await db.listar(
        COLECCIONES["orders"], Orden,
        [("status", "in", [EstadoOrden.pendiente.value, EstadoOrden.preparando.value])],
    )
    return {
        "restaurant_id":     restaurant_id,
        "mesas": {
            "total":          n,
            "ocupadas":       ocupadas,
            "disponibles":    disponibles,
            "tasa_ocupacion": round(ocupadas / max(n, 1), 2),
        },
        "reservaciones_hoy": len(reservaciones),
        "ordenes_activas":   len(ordenes),
        "timestamp":         datetime.utcnow().isoformat(),
    }
