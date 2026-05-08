"""Endpoints de gestión de usuarios del sistema."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import obtener_usuario_actual, requerir_gerente
from app.db.session import COLECCIONES, obtener_db
from app.models import Usuario
from app.schemas import SalidaUsuario

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("/yo", response_model=SalidaUsuario)
async def obtener_perfil(usuario_actual: Usuario = Depends(obtener_usuario_actual)) -> SalidaUsuario:
    return usuario_actual


@router.get("/", response_model=List[SalidaUsuario])
async def listar_usuarios(
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_gerente),
) -> List[SalidaUsuario]:
    return await db.listar(COLECCIONES["users"], Usuario, [("is_active", "==", True)])


@router.delete("/{user_id}", status_code=204)
async def desactivar_usuario(
    user_id: str,
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_gerente),
) -> None:
    usuario = await db.obtener(COLECCIONES["users"], user_id, Usuario)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    await db.actualizar(COLECCIONES["users"], usuario, {"is_active": False})
