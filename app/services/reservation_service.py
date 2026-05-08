"""Servicio de negocio para disponibilidad de mesas y lista de espera."""

from datetime import datetime, timedelta
from typing import Optional

from app.db.session import COLECCIONES
from app.models import EstadoMesa, EstadoReservacion, Mesa, Piso, Reservacion


async def buscar_mesa_disponible(
    db,
    restaurant_id: str,
    party_size: int,
    scheduled_at: datetime,
    duration_minutes: int,
) -> Optional[Mesa]:
    hora_fin = scheduled_at + timedelta(minutes=duration_minutes)
    pisos = await db.listar(
        COLECCIONES["floors"],
        Piso,
        [("restaurant_id", "==", restaurant_id), ("is_active", "==", True)],
    )
    ids_pisos = {piso.id for piso in pisos}
    if not ids_pisos:
        return None

    mesas = await db.listar(COLECCIONES["tables"], Mesa, [("is_active", "==", True)])
    candidatas = [
        mesa
        for mesa in mesas
        if mesa.floor_id in ids_pisos
        and mesa.capacity >= party_size
        and mesa.status != EstadoMesa.mantenimiento
    ]

    reservaciones = await db.listar(
        COLECCIONES["reservations"],
        Reservacion,
        [("status", "in", [EstadoReservacion.confirmada.value, EstadoReservacion.pendiente.value])],
    )
    for mesa in candidatas:
        solapada = False
        for reservacion in reservaciones:
            if reservacion.table_id != mesa.id:
                continue
            fin_existente = reservacion.scheduled_at + timedelta(minutes=reservacion.duration_minutes)
            if reservacion.scheduled_at < hora_fin and fin_existente > scheduled_at:
                solapada = True
                break
        if not solapada:
            return mesa
    return None


async def obtener_posicion_lista_espera(db, restaurant_id: str) -> int:
    existentes = await db.listar(
        COLECCIONES["reservations"],
        Reservacion,
        [
            ("restaurant_id", "==", restaurant_id),
            ("status", "==", EstadoReservacion.pendiente.value),
        ],
    )
    posiciones = [r.waitlist_position for r in existentes if r.waitlist_position is not None]
    return max(posiciones, default=0) + 1
