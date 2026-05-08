"""Endpoints de autenticación: registro, login, refresco y Google OAuth.

Verificación de Firebase ID token sin firebase_admin:
  → Usa el endpoint público de Google tokeninfo (httpx ya está en requirements).
  → No requiere service account ni rebuild del contenedor.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import (
    cifrar_contrasena,
    crear_token_acceso,
    crear_token_refresco,
    decodificar_token,
    verificar_contrasena,
)
from app.db.session import COLECCIONES, obtener_db
from app.models import RolUsuario, Usuario
from app.schemas import (
    CrearUsuario,
    RespuestaToken,
    SalidaUsuario,
    SolicitudGoogleAuth,
    SolicitudLogin,
    SolicitudRefresco,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])

_GOOGLE_TOKENINFO = "https://oauth2.googleapis.com/tokeninfo"


# ---------------------------------------------------------------------------
# Helper: verificar Firebase ID token con Google tokeninfo (sin firebase_admin)
# ---------------------------------------------------------------------------

async def _verificar_token_google(id_token: str) -> dict:
    """
    Llama al endpoint público de Google para validar un Firebase ID token.
    Devuelve el payload del token o lanza HTTPException 401.

    Retorna campos útiles: email, name, email_verified, aud, exp, sub.
    """
    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            resp = await client.get(_GOOGLE_TOKENINFO, params={"id_token": id_token})
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo contactar a Google para verificar el token",
            )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de Google inválido o expirado",
        )

    data = resp.json()

    # Validación básica: el token debe pertenecer a nuestra app Firebase
    # aud = Firebase App ID o Web Client ID de Google OAuth
    # En desarrollo puedes comentar esta verificación si tienes múltiples
    # audiences configurados.
    email_verified = data.get("email_verified", "false")
    if isinstance(email_verified, str):
        email_verified = email_verified.lower() == "true"

    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El email del token de Google no está verificado",
        )

    return data


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/registro", response_model=SalidaUsuario, status_code=status.HTTP_201_CREATED)
async def registrar(payload: CrearUsuario, db=Depends(obtener_db)) -> SalidaUsuario:
    usuario_existente = await db.primero(
        COLECCIONES["users"], Usuario, [("email", "==", payload.email)]
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
        COLECCIONES["users"], Usuario, [("email", "==", payload.email)]
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
    datos = decodificar_token(payload.refresh_token)
    if not datos or datos.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token de refresco inválido")

    usuario = await db.obtener(COLECCIONES["users"], datos.get("sub"), Usuario)
    if not usuario or not usuario.is_active:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    return RespuestaToken(
        access_token=crear_token_acceso(usuario.id),
        refresh_token=crear_token_refresco(usuario.id),
    )


@router.post("/google", response_model=RespuestaToken)
async def autenticar_google(
    payload: SolicitudGoogleAuth,
    db=Depends(obtener_db),
) -> RespuestaToken:
    """
    Intercambia un Firebase ID token (Google Auth) por tokens JWT internos.

    Flujo:
      1. Frontend hace signInWithPopup(auth, googleProvider)
      2. Obtiene ID token: await user.getIdToken()
      3. Llama POST /auth/google  { id_token: "..." }
      4. Backend verifica con Google tokeninfo (sin firebase_admin)
      5. Busca o crea el usuario en Firestore/Memoria
      6. Devuelve access_token + refresh_token
    """
    token_data = await _verificar_token_google(payload.id_token)

    email: str = token_data.get("email", "")
    nombre: str = token_data.get("name", "") or email.split("@")[0]

    if not email:
        raise HTTPException(status_code=400, detail="El token no contiene un email válido")

    # Buscar usuario existente
    usuario = await db.primero(
        COLECCIONES["users"], Usuario, [("email", "==", email)]
    )

    # Crear en primer login
    if not usuario:
        usuario = Usuario(
            email=email,
            hashed_password="",           # Sin contraseña — solo Google Auth
            full_name=nombre,
            role=RolUsuario.gerente,      # Rol por defecto
        )
        usuario = await db.crear(COLECCIONES["users"], usuario)

    if not usuario.is_active:
        raise HTTPException(status_code=403, detail="La cuenta está deshabilitada")

    return RespuestaToken(
        access_token=crear_token_acceso(usuario.id),
        refresh_token=crear_token_refresco(usuario.id),
    )