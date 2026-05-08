"""Endpoints de autenticación: registro, inicio de sesión y refresco de token."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import (
    cifrar_contrasena,
    crear_token_acceso,
    crear_token_refresco,
    decodificar_token,
    verificar_contrasena,
)
from app.db.session import COLECCIONES, obtener_db
from app.models import Usuario
from app.schemas import CrearUsuario, RespuestaToken, SalidaUsuario, SolicitudLogin, SolicitudRefresco

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/registro", response_model=SalidaUsuario, status_code=status.HTTP_201_CREATED)
async def registrar(payload: CrearUsuario, db=Depends(obtener_db)) -> SalidaUsuario:
    usuario_existente = await db.primero(
        COLECCIONES["users"],
        Usuario,
        [("email", "==", payload.email)],
    )
    if usuario_existente:
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")

    usuario = Usuario(
        email=payload.email,
        hashed_password=cifrar_contrasena(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role=payload.role,
    )
    return await db.crear(COLECCIONES["users"], usuario)


@router.post("/login", response_model=RespuestaToken)
async def iniciar_sesion(payload: SolicitudLogin, db=Depends(obtener_db)) -> RespuestaToken:
    usuario = await db.primero(
        COLECCIONES["users"],
        Usuario,
        [("email", "==", payload.email)],
    )

    if not usuario or not verificar_contrasena(payload.password, usuario.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    if not usuario.is_active:
        raise HTTPException(status_code=403, detail="La cuenta está deshabilitada")

    return RespuestaToken(
        access_token=crear_token_acceso(usuario.id),
        refresh_token=crear_token_refresco(usuario.id),
    )


@router.post("/refresco", response_model=RespuestaToken)
async def refrescar_token(payload: SolicitudRefresco, db=Depends(obtener_db)) -> RespuestaToken:
    datos_token = decodificar_token(payload.refresh_token)
    if not datos_token or datos_token.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token de refresco inválido")

    usuario = await db.obtener(COLECCIONES["users"], datos_token.get("sub"), Usuario)
    if not usuario or not usuario.is_active:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    return RespuestaToken(
        access_token=crear_token_acceso(usuario.id),
        refresh_token=crear_token_refresco(usuario.id),
    )
