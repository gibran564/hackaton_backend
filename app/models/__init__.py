from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


def generar_uuid() -> str:
    """Genera un identificador único universal en formato string."""
    return str(uuid.uuid4())


def _ahora() -> datetime:
    return datetime.utcnow()


def _enum(valor: Any, tipo: type[enum.Enum]) -> enum.Enum:
    if isinstance(valor, tipo):
        return valor
    return tipo(valor)


class RolUsuario(str, enum.Enum):
    cliente = "customer"
    mesero = "waiter"
    cocina = "kitchen"
    cajero = "cashier"
    gerente = "manager"
    administrador = "admin"


class EstadoMesa(str, enum.Enum):
    disponible = "available"
    ocupada = "occupied"
    reservada = "reserved"
    mantenimiento = "maintenance"


class EstadoReservacion(str, enum.Enum):
    pendiente = "pending"
    confirmada = "confirmed"
    sentada = "seated"
    completada = "completed"
    cancelada = "cancelled"
    no_presentado = "no_show"


class EstadoOrden(str, enum.Enum):
    pendiente = "pending"
    preparando = "preparing"
    lista = "ready"
    servida = "served"
    cancelada = "cancelled"


class NivelPrecio(str, enum.Enum):
    economico = "$"
    moderado  = "$$"
    caro      = "$$$"
    muy_caro  = "$$$$"


class CategoriaRestaurante(str, enum.Enum):
    mexicana        = "Mexicana"
    mariscos_carnes = "Mariscos & Carnes"
    internacional   = "Internacional"
    vegetal_cafe    = "Vegetal & Café"


@dataclass
class Usuario:
    email: str
    hashed_password: str
    full_name: str
    phone: Optional[str] = None
    role: RolUsuario = RolUsuario.cliente
    is_active: bool = True
    id: str = field(default_factory=generar_uuid)
    created_at: datetime = field(default_factory=_ahora)
    updated_at: datetime = field(default_factory=_ahora)

    def __post_init__(self) -> None:
        self.role = _enum(self.role, RolUsuario)


@dataclass
class Restaurante:
    # ── Identidad ──────────────────────────────────────────
    name:      str
    tipo:      str
    categoria: CategoriaRestaurante
    ubicacion: str
    precio:    NivelPrecio

    # ── Operación ──────────────────────────────────────────
    address:      Optional[str] = None
    phone:        Optional[str] = None
    email:        Optional[str] = None
    description:  Optional[str] = None
    opening_time: str  = "08:00"
    closing_time:  str = "22:00"
    max_capacity:  int = 100
    is_active:    bool = True

    # ── Métricas y presentación ────────────────────────────
    calificacion:         float     = 0.0
    porcentaje_ocupacion: int       = 0
    total_reseñas:        int       = 0
    reservas_hoy:         int       = 0
    imagen_url:           Optional[str]  = None
    galeria:              list[str] = field(default_factory=list)
    etiquetas:            list[str] = field(default_factory=list)
    horario:              Optional[str]  = None

    # ── Metadatos ──────────────────────────────────────────
    id:         str      = field(default_factory=generar_uuid)
    created_at: datetime = field(default_factory=_ahora)

    def __post_init__(self) -> None:
        self.categoria = _enum(self.categoria, CategoriaRestaurante)
        self.precio    = _enum(self.precio, NivelPrecio)

    @property
    def etiqueta_ocupacion(self) -> str:
        p = self.porcentaje_ocupacion
        if p >= 90:   estado = "Lleno"
        elif p >= 50: estado = "Ocupado"
        else:         estado = "Disponible"
        return f"{p}% · {estado}"


@dataclass
class Piso:
    restaurant_id: str
    name: str
    floor_number: int
    width: float = 800.0
    height: float = 600.0
    is_active: bool = True
    id: str = field(default_factory=generar_uuid)


@dataclass
class Mesa:
    floor_id: str
    label: str
    capacity: int = 4
    status: EstadoMesa = EstadoMesa.disponible
    pos_x: float = 0.0
    pos_y: float = 0.0
    is_active: bool = True
    id: str = field(default_factory=generar_uuid)
    updated_at: datetime = field(default_factory=_ahora)

    def __post_init__(self) -> None:
        self.status = _enum(self.status, EstadoMesa)


@dataclass
class Menu:
    restaurant_id: str
    name: str
    description: Optional[str] = None
    is_active: bool = True
    items: list[ArticuloMenu] = field(default_factory=list)
    id: str = field(default_factory=generar_uuid)
    created_at: datetime = field(default_factory=_ahora)


@dataclass
class ArticuloMenu:
    menu_id: str
    name: str
    category: str
    price: float
    description: Optional[str] = None
    prep_time: int = 15
    available: bool = True
    image_url: Optional[str] = None
    id: str = field(default_factory=generar_uuid)
    created_at: datetime = field(default_factory=_ahora)
    updated_at: datetime = field(default_factory=_ahora)


@dataclass
class Reservacion:
    restaurant_id: str
    user_id: str
    party_size: int
    scheduled_at: datetime
    table_id: Optional[str] = None
    duration_minutes: int = 90
    status: EstadoReservacion = EstadoReservacion.pendiente
    notes: Optional[str] = None
    waitlist_position: Optional[int] = None
    id: str = field(default_factory=generar_uuid)
    created_at: datetime = field(default_factory=_ahora)
    updated_at: datetime = field(default_factory=_ahora)

    def __post_init__(self) -> None:
        self.status = _enum(self.status, EstadoReservacion)


@dataclass
class Orden:
    table_id: str
    waiter_id: Optional[str] = None
    status: EstadoOrden = EstadoOrden.pendiente
    total: float = 0.0
    notes: Optional[str] = None
    items: list[ArticuloOrden] = field(default_factory=list)
    id: str = field(default_factory=generar_uuid)
    created_at: datetime = field(default_factory=_ahora)
    updated_at: datetime = field(default_factory=_ahora)

    def __post_init__(self) -> None:
        self.status = _enum(self.status, EstadoOrden)


@dataclass
class ArticuloOrden:
    order_id: str
    menu_item_id: str
    unit_price: float
    quantity: int = 1
    notes: Optional[str] = None
    id: str = field(default_factory=generar_uuid)


@dataclass
class SnapshotAnalitico:
    restaurant_id: str
    snapshot_type: str
    payload: dict
    id: str = field(default_factory=generar_uuid)
    created_at: datetime = field(default_factory=_ahora)