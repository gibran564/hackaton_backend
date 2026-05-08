"""Endpoints del módulo de cocina: creación y seguimiento de órdenes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import requerir_cocina, requerir_mesero
from app.db.session import COLECCIONES, obtener_db
from app.models import ArticuloMenu, ArticuloOrden, EstadoOrden, Orden, Usuario
from app.schemas import CrearOrden, SalidaOrden
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/ordenes", tags=["Cocina"])


@router.post("/", response_model=SalidaOrden, status_code=201)
async def crear_orden(
    payload: CrearOrden,
    db=Depends(obtener_db),
    usuario_actual: Usuario = Depends(requerir_mesero),
) -> SalidaOrden:
    total = 0.0
    orden = Orden(table_id=payload.table_id, waiter_id=usuario_actual.id, notes=payload.notes)
    articulos_orden: List[ArticuloOrden] = []

    for dato_articulo in payload.items:
        articulo_menu = await db.obtener(COLECCIONES["menu_items"], dato_articulo.menu_item_id, ArticuloMenu)
        if not articulo_menu or not articulo_menu.available:
            raise HTTPException(
                status_code=404,
                detail=f"Artículo {dato_articulo.menu_item_id} no encontrado o no disponible",
            )
        total += articulo_menu.price * dato_articulo.quantity
        articulos_orden.append(
            ArticuloOrden(
                order_id=orden.id,
                menu_item_id=dato_articulo.menu_item_id,
                quantity=dato_articulo.quantity,
                unit_price=articulo_menu.price,
                notes=dato_articulo.notes,
            )
        )

    orden.total = total
    orden.items = articulos_orden
    orden = await db.crear(COLECCIONES["orders"], orden)
    for articulo in articulos_orden:
        await db.crear(COLECCIONES["order_items"], articulo)

    await ws_manager.difundir(
        "ordenes",
        {"evento": "orden_creada", "orden_id": orden.id, "mesa_id": payload.table_id},
    )
    return orden


@router.get("/", response_model=List[SalidaOrden])
async def listar_ordenes_activas(
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_cocina),
) -> List[SalidaOrden]:
    ordenes = await db.listar(
        COLECCIONES["orders"],
        Orden,
        [("status", "in", [EstadoOrden.pendiente.value, EstadoOrden.preparando.value])],
        ordenar_por="created_at",
    )
    for orden in ordenes:
        orden.items = await db.listar(
            COLECCIONES["order_items"],
            ArticuloOrden,
            [("order_id", "==", orden.id)],
        )
    return ordenes


@router.patch("/{order_id}/estado")
async def actualizar_estado_orden(
    order_id: str,
    nuevo_estado: EstadoOrden,
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_cocina),
) -> dict:
    orden = await db.obtener(COLECCIONES["orders"], order_id, Orden)
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    await db.actualizar(COLECCIONES["orders"], orden, {"status": nuevo_estado})
    await ws_manager.difundir(
        "ordenes",
        {"evento": "estado_orden_actualizado", "orden_id": orden.id, "estado": nuevo_estado.value},
    )
    return {"orden_id": order_id, "estado": nuevo_estado}
