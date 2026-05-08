"""Endpoints de gestión de pisos y mesas del restaurante."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import requerir_gerente, requerir_mesero
from app.db.session import COLECCIONES, obtener_db
from app.models import Mesa, Piso, Usuario
from app.schemas import ActualizarMesa, CrearMesa, CrearPiso, SalidaMesa, SalidaPiso
from app.websocket.manager import ws_manager

router = APIRouter(tags=["Mesas"])


@router.post("/restaurantes/{restaurant_id}/pisos", response_model=SalidaPiso, status_code=201)
async def crear_piso(
    restaurant_id: str,
    payload: CrearPiso,
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_gerente),
) -> SalidaPiso:
    piso = Piso(restaurant_id=restaurant_id, **payload.model_dump())
    return await db.crear(COLECCIONES["floors"], piso)


@router.get("/restaurantes/{restaurant_id}/pisos", response_model=List[SalidaPiso])
async def listar_pisos(
    restaurant_id: str,
    db=Depends(obtener_db),
) -> List[SalidaPiso]:
    return await db.listar(
        COLECCIONES["floors"],
        Piso,
        [("restaurant_id", "==", restaurant_id), ("is_active", "==", True)],
    )


@router.post("/pisos/{floor_id}/mesas", response_model=SalidaMesa, status_code=201)
async def crear_mesa(
    floor_id: str,
    payload: CrearMesa,
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_gerente),
) -> SalidaMesa:
    mesa = Mesa(floor_id=floor_id, **payload.model_dump())
    return await db.crear(COLECCIONES["tables"], mesa)


@router.get("/pisos/{floor_id}/mesas", response_model=List[SalidaMesa])
async def listar_mesas(
    floor_id: str,
    db=Depends(obtener_db),
) -> List[SalidaMesa]:
    return await db.listar(
        COLECCIONES["tables"],
        Mesa,
        [("floor_id", "==", floor_id), ("is_active", "==", True)],
    )


@router.patch("/mesas/{table_id}", response_model=SalidaMesa)
async def actualizar_mesa(
    table_id: str,
    payload: ActualizarMesa,
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_mesero),
) -> SalidaMesa:
    mesa = await db.obtener(COLECCIONES["tables"], table_id, Mesa)
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")

    mesa = await db.actualizar(
        COLECCIONES["tables"],
        mesa,
        payload.model_dump(exclude_none=True),
    )
    await ws_manager.difundir(
        "mesas",
        {"evento": "mesa_actualizada", "mesa_id": mesa.label, "estado": str(mesa.status.value)},
    )
    return mesa
