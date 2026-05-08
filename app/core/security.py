"""
Módulo de seguridad: hashing de contraseñas y manejo de tokens JWT.

Implementa funciones de cifrado de contraseñas y generación/validación
de tokens de acceso y actualización mediante JSON Web Tokens.
"""

from datetime import datetime, timedelta
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

contexto_cifrado = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def cifrar_contrasena(contrasena: str) -> str:
    """
    Genera el hash seguro de una contraseña en texto plano.

    Args:
        contrasena: Contraseña original del usuario.

    Returns:
        Hash de la contraseña.
    """
    return contexto_cifrado.hash(contrasena)


def verificar_contrasena(contrasena_plana: str, hash_contrasena: str) -> bool:
    """
    Compara una contraseña en texto plano con su hash almacenado.

    Args:
        contrasena_plana: Contraseña proporcionada por el usuario.
        hash_contrasena: Hash almacenado en la base de datos.

    Returns:
        True si la contraseña coincide, False en caso contrario.
    """
    return contexto_cifrado.verify(contrasena_plana, hash_contrasena)


def crear_token_acceso(sujeto: Any, delta_expiracion: Optional[timedelta] = None) -> str:
    """
    Genera un token JWT de acceso con expiración configurable.

    Args:
        sujeto: Identificador del usuario (generalmente su UUID).
        delta_expiracion: Duración personalizada del token.

    Returns:
        Token JWT firmado con tipo 'access'.
    """
    expiracion = datetime.utcnow() + (
        delta_expiracion or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    carga = {"sub": str(sujeto), "exp": expiracion, "type": "access"}
    return jwt.encode(carga, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def crear_token_refresco(sujeto: Any) -> str:
    """
    Genera un token JWT de actualización de larga duración.

    Args:
        sujeto: Identificador del usuario (generalmente su UUID).

    Returns:
        Token JWT firmado con tipo 'refresh'.
    """
    expiracion = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    carga = {"sub": str(sujeto), "exp": expiracion, "type": "refresh"}
    return jwt.encode(carga, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str) -> dict:
    """
    Decodifica y valida un token JWT.

    Args:
        token: Token JWT en formato string.

    Returns:
        Diccionario con el payload si el token es válido,
        o un diccionario vacío si es inválido o ha expirado.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return {}
