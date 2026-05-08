"""
Pruebas de integración para el módulo de autenticación.

Verifica el flujo completo de registro e inicio de sesión,
incluyendo la generación de tokens y el manejo de credenciales inválidas.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_registro_e_inicio_sesion() -> None:
    """
    Verifica el flujo de registro seguido de inicio de sesión exitoso.

    Comprueba que el registro devuelva los datos del usuario con el rol
    correcto y que el inicio de sesión retorne los tokens de acceso y refresco.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as cliente:
        respuesta = await cliente.post("/api/v1/auth/registro", json={
            "email": "prueba@ejemplo.com",
            "password": "contrasena123",
            "full_name": "Usuario de Prueba",
        })
        assert respuesta.status_code == 201
        datos = respuesta.json()
        assert datos["email"] == "prueba@ejemplo.com"
        assert datos["role"] == "customer"

        respuesta = await cliente.post("/api/v1/auth/login", json={
            "email": "prueba@ejemplo.com",
            "password": "contrasena123",
        })
        assert respuesta.status_code == 200
        tokens = respuesta.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens


@pytest.mark.asyncio
async def test_inicio_sesion_invalido() -> None:
    """
    Verifica que las credenciales incorrectas devuelvan un error 401.

    Comprueba que el sistema rechace solicitudes de autenticación con
    un correo electrónico no registrado o una contraseña incorrecta.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as cliente:
        respuesta = await cliente.post("/api/v1/auth/login", json={
            "email": "nadie@ejemplo.com",
            "password": "contrasena_incorrecta",
        })
        assert respuesta.status_code == 401
