"""Endpoints de gestión de restaurantes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import requerir_admin
from app.db.session import COLECCIONES, obtener_db
from app.models import Restaurante, Usuario
from app.schemas import CrearRestaurante, SalidaRestaurante

router = APIRouter(prefix="/restaurantes", tags=["Restaurantes"])


@router.post("/", response_model=SalidaRestaurante, status_code=status.HTTP_201_CREATED)
async def crear_restaurante(
    payload: CrearRestaurante,
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_admin),
) -> SalidaRestaurante:
    restaurante = Restaurante(**payload.model_dump())
    return await db.crear(COLECCIONES["restaurants"], restaurante)


@router.get("/", response_model=List[SalidaRestaurante])
async def listar_restaurantes(db=Depends(obtener_db)) -> List[SalidaRestaurante]:
    return await db.listar(
        COLECCIONES["restaurants"],
        Restaurante,
        [("is_active", "==", True)],
    )


@router.get("/{restaurant_id}", response_model=SalidaRestaurante)
async def obtener_restaurante(
    restaurant_id: str,
    db=Depends(obtener_db),
) -> SalidaRestaurante:
    restaurante = await db.obtener(COLECCIONES["restaurants"], restaurant_id, Restaurante)
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")
    return restaurante


@router.delete("/{restaurant_id}", status_code=204)
async def eliminar_restaurante(
    restaurant_id: str,
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_admin),
) -> None:
    restaurante = await db.obtener(COLECCIONES["restaurants"], restaurant_id, Restaurante)
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")
    await db.actualizar(COLECCIONES["restaurants"], restaurante, {"is_active": False})
