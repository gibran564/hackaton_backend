"""
Cliente y repositorio de Firestore.

Firestore usa una API sincrónica en Python; las operaciones se ejecutan en
threads para no bloquear el event loop de FastAPI.

Modos de autenticación (en orden de prioridad):
  1. FIREBASE_CREDENTIALS_BASE64  → JSON del service account en base64.
                                    Ideal para Railway / cualquier PaaS.
  2. GOOGLE_APPLICATION_CREDENTIALS → ruta al archivo JSON local.
                                    Ideal para desarrollo local con secrets/.
  3. ADC (Application Default Credentials) → gcloud auth o entorno GCP.

En tests o cuando FIRESTORE_USE_MEMORY=true se usa RepositorioMemoria,
que implementa la misma interfaz sin necesidad de credenciales.
"""

from __future__ import annotations

import asyncio
import base64
import enum
import json
import logging
import os
from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Iterable, Optional, TypeVar

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


COLECCIONES = {
    "users": "users",
    "restaurants": "restaurants",
    "floors": "floors",
    "tables": "tables",
    "menus": "menus",
    "menu_items": "menu_items",
    "reservations": "reservations",
    "orders": "orders",
    "order_items": "order_items",
    "analytics_snapshots": "analytics_snapshots",
}


# ---------------------------------------------------------------------------
# Serialización
# ---------------------------------------------------------------------------

def _serializar(valor: Any) -> Any:
    if isinstance(valor, enum.Enum):
        return valor.value
    if is_dataclass(valor):
        return {k: _serializar(v) for k, v in asdict(valor).items()}
    if isinstance(valor, list):
        return [_serializar(v) for v in valor]
    if isinstance(valor, dict):
        return {k: _serializar(v) for k, v in valor.items()}
    return valor


def _datos_modelo(modelo: type[T], datos: dict[str, Any]) -> dict[str, Any]:
    permitidos = {campo.name for campo in fields(modelo)}
    return {k: v for k, v in datos.items() if k in permitidos}


# ---------------------------------------------------------------------------
# Repositorio Firestore
# ---------------------------------------------------------------------------

class RepositorioFirestore:
    """Repositorio asincrónico sobre Cloud Firestore."""

    def __init__(self, cliente: Any):
        self.cliente = cliente

    async def crear(self, coleccion: str, entidad: T) -> T:
        datos = _serializar(entidad)
        await asyncio.to_thread(
            self.cliente.collection(coleccion).document(datos["id"]).set,
            datos,
        )
        return entidad

    async def obtener(self, coleccion: str, document_id: str, modelo: type[T]) -> Optional[T]:
        snapshot = await asyncio.to_thread(
            self.cliente.collection(coleccion).document(document_id).get
        )
        if not snapshot.exists:
            return None
        datos = snapshot.to_dict() or {}
        datos["id"] = snapshot.id
        return modelo(**_datos_modelo(modelo, datos))

    async def listar(
        self,
        coleccion: str,
        modelo: type[T],
        filtros: Iterable[tuple[str, str, Any]] = (),
        ordenar_por: Optional[str] = None,
        descendente: bool = False,
    ) -> list[T]:
        consulta = self.cliente.collection(coleccion)
        for campo, operador, valor in filtros:
            consulta = consulta.where(campo, operador, _serializar(valor))
        if ordenar_por:
            from google.cloud import firestore
            direccion = (
                firestore.Query.DESCENDING if descendente else firestore.Query.ASCENDING
            )
            consulta = consulta.order_by(ordenar_por, direction=direccion)
        snapshots = await asyncio.to_thread(lambda: list(consulta.stream()))
        entidades: list[T] = []
        for snapshot in snapshots:
            datos = snapshot.to_dict() or {}
            datos["id"] = snapshot.id
            entidades.append(modelo(**_datos_modelo(modelo, datos)))
        return entidades

    async def primero(
        self,
        coleccion: str,
        modelo: type[T],
        filtros: Iterable[tuple[str, str, Any]],
    ) -> Optional[T]:
        elementos = await self.listar(coleccion, modelo, filtros)
        return elementos[0] if elementos else None

    async def actualizar(self, coleccion: str, entidad: T, cambios: dict[str, Any]) -> T:
        cambios = {**cambios, "updated_at": datetime.utcnow()}
        for campo, valor in cambios.items():
            setattr(entidad, campo, valor)
        await asyncio.to_thread(
            self.cliente.collection(coleccion).document(entidad.id).update,
            _serializar(cambios),
        )
        return entidad


# ---------------------------------------------------------------------------
# Repositorio en Memoria (tests / sin credenciales)
# ---------------------------------------------------------------------------

class RepositorioMemoria:
    """Repositorio compatible con la misma interfaz, sin persistencia."""

    def __init__(self) -> None:
        self._datos: dict[str, dict[str, dict[str, Any]]] = {
            coleccion: {} for coleccion in COLECCIONES.values()
        }

    async def crear(self, coleccion: str, entidad: T) -> T:
        self._datos.setdefault(coleccion, {})[entidad.id] = _serializar(entidad)
        return entidad

    async def obtener(self, coleccion: str, document_id: str, modelo: type[T]) -> Optional[T]:
        datos = self._datos.get(coleccion, {}).get(document_id)
        if not datos:
            return None
        return modelo(**_datos_modelo(modelo, {**datos, "id": document_id}))

    async def listar(
        self,
        coleccion: str,
        modelo: type[T],
        filtros: Iterable[tuple[str, str, Any]] = (),
        ordenar_por: Optional[str] = None,
        descendente: bool = False,
    ) -> list[T]:
        elementos = []
        for document_id, datos in self._datos.get(coleccion, {}).items():
            if all(
                self._coincide(datos.get(campo), operador, _serializar(valor))
                for campo, operador, valor in filtros
            ):
                elementos.append(
                    modelo(**_datos_modelo(modelo, {**datos, "id": document_id}))
                )
        if ordenar_por:
            elementos.sort(
                key=lambda item: getattr(item, ordenar_por, None),
                reverse=descendente,
            )
        return elementos

    async def primero(
        self,
        coleccion: str,
        modelo: type[T],
        filtros: Iterable[tuple[str, str, Any]],
    ) -> Optional[T]:
        elementos = await self.listar(coleccion, modelo, filtros)
        return elementos[0] if elementos else None

    async def actualizar(self, coleccion: str, entidad: T, cambios: dict[str, Any]) -> T:
        cambios = {**cambios, "updated_at": datetime.utcnow()}
        for campo, valor in cambios.items():
            setattr(entidad, campo, valor)
        self._datos.setdefault(coleccion, {})[entidad.id] = _serializar(entidad)
        return entidad

    @staticmethod
    def _coincide(actual: Any, operador: str, esperado: Any) -> bool:
        if operador == "==":
            return actual == esperado
        if operador == "!=":
            return actual != esperado
        if operador == ">=":
            return actual >= esperado
        if operador == "<":
            return actual < esperado
        if operador == "in":
            return actual in esperado
        return False


# ---------------------------------------------------------------------------
# Factory — elige el repositorio correcto al arrancar
# ---------------------------------------------------------------------------

def _crear_repositorio() -> RepositorioFirestore | RepositorioMemoria:
    usar_memoria = (
        settings.FIRESTORE_USE_MEMORY
        or os.getenv("PYTEST_CURRENT_TEST") is not None
    )
    if usar_memoria:
        logger.info("Usando RepositorioMemoria (FIRESTORE_USE_MEMORY=true o test)")
        return RepositorioMemoria()

    try:
        # Imports aquí para no crashear si el paquete no está instalado
        from google.cloud import firestore
        from google.oauth2 import service_account

        # ── Modo 1: base64 en variable de entorno (Railway / PaaS) ──────────
        firebase_b64 = os.getenv("FIREBASE_CREDENTIALS_BASE64", "").strip()
        if firebase_b64:
            cred_dict = json.loads(base64.b64decode(firebase_b64).decode("utf-8"))
            credentials = service_account.Credentials.from_service_account_info(
                cred_dict,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            cliente = firestore.Client(
                project=cred_dict["project_id"],
                credentials=credentials,
            )
            logger.info("✅ Firestore conectado via FIREBASE_CREDENTIALS_BASE64")
            return RepositorioFirestore(cliente)

        # ── Modo 2: ruta a archivo JSON (desarrollo local con secrets/) ──────
        creds_path = (
            settings.GOOGLE_APPLICATION_CREDENTIALS
            or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        ).strip()
        if creds_path and os.path.isfile(creds_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
            cliente = firestore.Client(project=settings.VITE_FIREBASE_PROJECT_ID)
            logger.info("✅ Firestore conectado via archivo: %s", creds_path)
            return RepositorioFirestore(cliente)

        # ── Modo 3: ADC — gcloud auth o entorno GCP ──────────────────────────
        cliente = firestore.Client(project=settings.VITE_FIREBASE_PROJECT_ID)
        logger.info("✅ Firestore conectado via Application Default Credentials")
        return RepositorioFirestore(cliente)

    except Exception as exc:
        logger.warning(
            "⚠️  No se pudo conectar a Firestore: %s\n"
            "    → Local:   configura GOOGLE_APPLICATION_CREDENTIALS=secrets/archivo.json\n"
            "    → Railway: configura FIREBASE_CREDENTIALS_BASE64=<base64 del JSON>\n"
            "    Usando RepositorioMemoria — los datos NO persisten.",
            exc,
        )
        return RepositorioMemoria()


repositorio = _crear_repositorio()


async def obtener_db() -> AsyncIterator[RepositorioFirestore | RepositorioMemoria]:
    yield repositorio


async def crear_tablas() -> None:
    """Firestore no requiere migraciones."""
    return None
