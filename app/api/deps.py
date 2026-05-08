"""Dependencias de FastAPI para autenticación y control de acceso por roles."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decodificar_token
from app.db.session import COLECCIONES, obtener_db
from app.models import RolUsuario, Usuario

esquema_bearer = HTTPBearer()


async def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(esquema_bearer),
    db=Depends(obtener_db),
) -> Usuario:
    token = credenciales.credentials
    payload = decodificar_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )

    usuario = await db.obtener(COLECCIONES["users"], payload.get("sub"), Usuario)
    if not usuario or not usuario.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )
    return usuario


def requerir_roles(*roles: RolUsuario):
    async def verificador_rol(usuario_actual: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
        if usuario_actual.role not in roles and usuario_actual.role != RolUsuario.administrador:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El rol '{usuario_actual.role}' no está autorizado para esta acción",
            )
        return usuario_actual

    return verificador_rol


requerir_admin = requerir_roles(RolUsuario.administrador)
requerir_gerente = requerir_roles(RolUsuario.gerente, RolUsuario.administrador)
requerir_mesero = requerir_roles(RolUsuario.mesero, RolUsuario.gerente, RolUsuario.administrador)
requerir_cocina = requerir_roles(RolUsuario.cocina, RolUsuario.gerente, RolUsuario.administrador)
requerir_cajero = requerir_roles(RolUsuario.cajero, RolUsuario.gerente, RolUsuario.administrador)
