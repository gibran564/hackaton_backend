"""Endpoints de gestión de reservaciones de mesa."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import obtener_usuario_actual, requerir_mesero
from app.db.session import COLECCIONES, obtener_db
from app.models import EstadoReservacion, Reservacion, Usuario
from app.schemas import ActualizarReservacion, CrearReservacion, SalidaReservacion
from app.services.reservation_service import buscar_mesa_disponible, obtener_posicion_lista_espera
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/reservaciones", tags=["Reservaciones"])


@router.post("/", response_model=SalidaReservacion, status_code=status.HTTP_201_CREATED)
async def crear_reservacion(
    payload: CrearReservacion,
    db=Depends(obtener_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> SalidaReservacion:
    mesa = await buscar_mesa_disponible(
        db,
        payload.restaurant_id,
        payload.party_size,
        payload.scheduled_at,
        payload.duration_minutes,
    )
    posicion_espera = None if mesa else await obtener_posicion_lista_espera(db, payload.restaurant_id)
    reservacion = Reservacion(
        restaurant_id=payload.restaurant_id,
        user_id=usuario_actual.id,
        table_id=mesa.id if mesa else None,
        party_size=payload.party_size,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        notes=payload.notes,
        status=EstadoReservacion.confirmada if mesa else EstadoReservacion.pendiente,
        waitlist_position=posicion_espera,
    )
    reservacion = await db.crear(COLECCIONES["reservations"], reservacion)
    await ws_manager.difundir(
        "reservaciones",
        {
            "evento": "reservacion_creada",
            "reservacion_id": reservacion.id,
            "estado": reservacion.status.value,
        },
    )
    return reservacion


@router.get("/{reservation_id}", response_model=SalidaReservacion)
async def obtener_reservacion(
    reservation_id: str,
    db=Depends(obtener_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> SalidaReservacion:
    reservacion = await db.obtener(COLECCIONES["reservations"], reservation_id, Reservacion)
    if not reservacion:
        raise HTTPException(status_code=404, detail="Reservación no encontrada")
    return reservacion


@router.get("/", response_model=List[SalidaReservacion])
async def listar_mis_reservaciones(
    db=Depends(obtener_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> List[SalidaReservacion]:
    return await db.listar(
        COLECCIONES["reservations"],
        Reservacion,
        [("user_id", "==", usuario_actual.id)],
        ordenar_por="scheduled_at",
        descendente=True,
    )


@router.patch("/{reservation_id}", response_model=SalidaReservacion)
async def actualizar_reservacion(
    reservation_id: str,
    payload: ActualizarReservacion,
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_mesero),
) -> SalidaReservacion:
    reservacion = await db.obtener(COLECCIONES["reservations"], reservation_id, Reservacion)
    if not reservacion:
        raise HTTPException(status_code=404, detail="Reservación no encontrada")
    return await db.actualizar(
        COLECCIONES["reservations"],
        reservacion,
        payload.model_dump(exclude_none=True),
    )


@router.delete("/{reservation_id}", status_code=204)
async def cancelar_reservacion(
    reservation_id: str,
    db=Depends(obtener_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> None:
    reservacion = await db.obtener(COLECCIONES["reservations"], reservation_id, Reservacion)
    if not reservacion:
        raise HTTPException(status_code=404, detail="Reservación no encontrada")
    if reservacion.user_id != usuario_actual.id:
        raise HTTPException(status_code=403, detail="No tiene permiso para cancelar esta reservación")
    await db.actualizar(
        COLECCIONES["reservations"],
        reservacion,
        {"status": EstadoReservacion.cancelada},
    )
