"""Endpoints del módulo de analíticos con Bubble Intelligence."""

from datetime import datetime
from typing import Any, AsyncGenerator, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import requerir_gerente
from app.bubbles.meta_collapser import MetaCollapser
from app.db.session import COLECCIONES, obtener_db
from app.models import EstadoMesa, EstadoOrden, EstadoReservacion, Mesa, Orden, Piso, Reservacion, Usuario
from app.schemas import SalidaInsightBubble, SolicitudAnaliticos

router = APIRouter(prefix="/analiticos", tags=["Analíticos"])

_collapser = MetaCollapser()


def _construir_contexto_bd(
    conteo_reservaciones: int,
    conteo_ordenes: int,
    total_mesas: int,
    mesas_ocupadas: int,
) -> Dict[str, Any]:
    ahora = datetime.utcnow()
    tasa_ocupacion = mesas_ocupadas / max(total_mesas, 1)
    return {
        "time_of_day": ahora.hour / 23.0,
        "day_of_week": ahora.weekday() / 6.0,
        "is_holiday": 0.0,
        "weather_score": 0.6,
        "local_events": 0.3,
        "avg_order_value": 0.5,
        "top_category_ratio": 0.4,
        "alcohol_ratio": 0.2,
        "dessert_ratio": 0.15,
        "combo_rate": 0.25,
        "avg_prep_time": 0.5,
        "staff_load": tasa_ocupacion,
        "kitchen_queue_depth": min(conteo_ordenes / 20.0, 1.0),
        "order_error_rate": 0.05,
        "table_turn_rate": 0.6,
        "avg_rating": 0.80,
        "cancellation_rate": 0.1,
        "return_rate": 0.45,
        "complaint_rate": 0.03,
        "avg_wait_time": 0.3,
        "occupancy_ratio": tasa_ocupacion,
        "avg_table_utilization": tasa_ocupacion * 0.9,
        "dead_zone_ratio": 0.1,
        "aisle_blockage": 0.05,
        "floor_score": 0.75,
    }


async def _mesas_restaurante(db, restaurant_id: str) -> list[Mesa]:
    pisos = await db.listar(COLECCIONES["floors"], Piso, [("restaurant_id", "==", restaurant_id)])
    ids_pisos = {piso.id for piso in pisos}
    if not ids_pisos:
        return []
    mesas = await db.listar(COLECCIONES["tables"], Mesa)
    return [mesa for mesa in mesas if mesa.floor_id in ids_pisos]


async def _construir_contexto(db, restaurant_id: str) -> Dict[str, Any]:
    """Consulta Firestore y construye el contexto para el MetaCollapser."""
    reservaciones = await db.listar(
        COLECCIONES["reservations"],
        Reservacion,
        [
            ("restaurant_id", "==", restaurant_id),
            ("status", "==", EstadoReservacion.confirmada.value),
        ],
    )
    ordenes = await db.listar(
        COLECCIONES["orders"],
        Orden,
        [("status", "in", [EstadoOrden.pendiente.value, EstadoOrden.preparando.value])],
    )
    mesas = await _mesas_restaurante(db, restaurant_id)
    mesas_ocupadas = sum(1 for mesa in mesas if mesa.status == EstadoMesa.ocupada)
    return _construir_contexto_bd(len(reservaciones), len(ordenes), len(mesas), mesas_ocupadas)


# ---------------------------------------------------------------------------
# Endpoint: resultado completo (sin stream) — para clientes que no soporten SSE
# ---------------------------------------------------------------------------

@router.post("/bubble-insight", response_model=SalidaInsightBubble)
async def obtener_insight_bubble(
    payload: SolicitudAnaliticos,
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_gerente),
) -> SalidaInsightBubble:
    """Retorna el resultado completo del MetaCollapser en una sola respuesta JSON."""
    contexto = await _construir_contexto(db, payload.restaurant_id)
    return SalidaInsightBubble(**_collapser.ejecutar(contexto))


# ---------------------------------------------------------------------------
# Endpoint: stream SSE — emite cada burbuja en tiempo real
# ---------------------------------------------------------------------------

@router.post(
    "/bubble-insight/stream",
    summary="Bubble Intelligence — stream SSE",
    response_description="Server-Sent Events: bubble_result × 5 → final_result → done",
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def obtener_insight_bubble_stream(
    payload: SolicitudAnaliticos,
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_gerente),
) -> StreamingResponse:
    """
    Ejecuta el análisis Bubble Intelligence y emite resultados vía SSE.

    Secuencia de eventos:
    - **bubble_result** (×5): resultado de cada burbuja al terminar su inferencia.
    - **final_result** (×1): predicción consolidada del MetaCollapser.
    - **done** (×1): señal de cierre del stream.

    Ejemplo de consumo en el cliente:
    ```js
    const es = new EventSource('/api/v1/analiticos/bubble-insight/stream');
    es.addEventListener('bubble_result', e => console.log(JSON.parse(e.data)));
    es.addEventListener('final_result', e => console.log(JSON.parse(e.data)));
    es.addEventListener('done', () => es.close());
    ```
    """
    contexto = await _construir_contexto(db, payload.restaurant_id)

    async def _generar() -> AsyncGenerator[str, None]:
        async for chunk in _collapser.ejecutar_stream(contexto):
            yield chunk

    return StreamingResponse(
        _generar(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # desactiva el buffer de nginx
        },
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard/{restaurant_id}")
async def resumen_dashboard(
    restaurant_id: str,
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_gerente),
) -> dict:
    mesas = await _mesas_restaurante(db, restaurant_id)
    total_mesas = len(mesas)
    ocupadas = sum(1 for mesa in mesas if mesa.status == EstadoMesa.ocupada)
    disponibles = sum(1 for mesa in mesas if mesa.status == EstadoMesa.disponible)
    reservaciones = await db.listar(
        COLECCIONES["reservations"],
        Reservacion,
        [
            ("restaurant_id", "==", restaurant_id),
            ("status", "!=", EstadoReservacion.cancelada.value),
        ],
    )
    ordenes = await db.listar(
        COLECCIONES["orders"],
        Orden,
        [("status", "in", [EstadoOrden.pendiente.value, EstadoOrden.preparando.value])],
    )
    return {
        "restaurant_id": restaurant_id,
        "mesas": {
            "total": total_mesas,
            "ocupadas": ocupadas,
            "disponibles": disponibles,
            "tasa_ocupacion": round(ocupadas / max(total_mesas, 1), 2),
        },
        "reservaciones_hoy": len(reservaciones),
        "ordenes_activas": len(ordenes),
        "timestamp": datetime.utcnow().isoformat(),
    }
