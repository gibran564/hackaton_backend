"""
Módulo de esquemas Pydantic para validación de entrada y serialización de salida.

Define los modelos de transferencia de datos (DTOs) utilizados en
todos los endpoints de la API v1, organizados por dominio funcional.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.models import RolUsuario, EstadoMesa, EstadoReservacion, EstadoOrden


class SolicitudLogin(BaseModel):
    """Credenciales requeridas para iniciar sesión."""
    email: EmailStr
    password: str


class RespuestaToken(BaseModel):
    """Par de tokens JWT devuelto tras autenticación exitosa."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class SolicitudRefresco(BaseModel):
    """Token de refresco para obtener un nuevo token de acceso."""
    refresh_token: str
    
class SolicitudGoogleAuth(BaseModel):
    """Firebase ID token obtenido del flujo Google OAuth en el frontend."""
    id_token: str
class SolicitudGoogleAuth(BaseModel):
    """Firebase ID token obtenido del flujo Google OAuth en el frontend."""
    id_token: str

class CrearUsuario(BaseModel):
    """Datos requeridos para registrar un nuevo usuario en el sistema."""
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    phone: Optional[str] = None
    role: RolUsuario = RolUsuario.cliente


class SalidaUsuario(BaseModel):
    """Representación pública de un usuario del sistema."""
    id: str
    email: str
    full_name: str
    phone: Optional[str]
    role: RolUsuario
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CrearRestaurante(BaseModel):
    """Datos necesarios para registrar un nuevo restaurante."""
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    description: Optional[str] = None
    opening_time: str = "08:00"
    closing_time: str = "22:00"
    max_capacity: int = 100


class SalidaRestaurante(BaseModel):
    """Representación pública de un restaurante."""
    id: str
    name: str
    address: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    description: Optional[str]
    opening_time: str
    closing_time: str
    max_capacity: int
    is_active: bool

    class Config:
        from_attributes = True


class CrearPiso(BaseModel):
    """Datos para crear un piso dentro de un restaurante."""
    name: str
    floor_number: int
    width: float = 800.0
    height: float = 600.0


class SalidaPiso(BaseModel):
    """Representación pública de un piso del restaurante."""
    id: str
    restaurant_id: str
    name: str
    floor_number: int
    width: float
    height: float
    is_active: bool

    class Config:
        from_attributes = True


class CrearMesa(BaseModel):
    """Datos para registrar una nueva mesa en un piso."""
    label: str
    capacity: int
    pos_x: float = 0.0
    pos_y: float = 0.0


class ActualizarMesa(BaseModel):
    """Campos actualizables de una mesa (todos opcionales)."""
    status: Optional[EstadoMesa] = None
    pos_x: Optional[float] = None
    pos_y: Optional[float] = None
    capacity: Optional[int] = None


class SalidaMesa(BaseModel):
    """Representación pública de una mesa con su estado actual."""
    id: str
    floor_id: str
    label: str
    capacity: int
    status: EstadoMesa
    pos_x: float
    pos_y: float
    is_active: bool
    updated_at: datetime

    class Config:
        from_attributes = True


class CrearMenu(BaseModel):
    """Datos para crear un menú asociado a un restaurante."""
    name: str
    description: Optional[str] = None


class CrearArticuloMenu(BaseModel):
    """Datos para agregar un artículo a un menú existente."""
    name: str
    description: Optional[str] = None
    category: str
    price: float = Field(gt=0)
    prep_time: int = 15
    available: bool = True
    image_url: Optional[str] = None


class ActualizarArticuloMenu(BaseModel):
    """Campos actualizables de un artículo del menú (todos opcionales)."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    prep_time: Optional[int] = None
    available: Optional[bool] = None


class SalidaArticuloMenu(BaseModel):
    """Representación pública de un artículo del menú."""
    id: str
    menu_id: str
    name: str
    description: Optional[str]
    category: str
    price: float
    prep_time: int
    available: bool
    image_url: Optional[str]

    class Config:
        from_attributes = True


class SalidaMenu(BaseModel):
    """Representación pública de un menú con sus artículos incluidos."""
    id: str
    restaurant_id: str
    name: str
    description: Optional[str]
    is_active: bool
    items: List[SalidaArticuloMenu] = []

    class Config:
        from_attributes = True


class CrearReservacion(BaseModel):
    """Datos necesarios para solicitar una reservación de mesa."""
    restaurant_id: str
    party_size: int = Field(ge=1)
    scheduled_at: datetime
    duration_minutes: int = 90
    notes: Optional[str] = None


class ActualizarReservacion(BaseModel):
    """Campos actualizables de una reservación existente."""
    status: Optional[EstadoReservacion] = None
    table_id: Optional[str] = None
    notes: Optional[str] = None


class SalidaReservacion(BaseModel):
    """Representación pública completa de una reservación."""
    id: str
    restaurant_id: str
    user_id: str
    table_id: Optional[str]
    party_size: int
    scheduled_at: datetime
    duration_minutes: int
    status: EstadoReservacion
    notes: Optional[str]
    waitlist_position: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class CrearArticuloOrden(BaseModel):
    """Línea de artículo dentro de una solicitud de orden."""
    menu_item_id: str
    quantity: int = Field(ge=1)
    notes: Optional[str] = None


class CrearOrden(BaseModel):
    """Datos requeridos para registrar una nueva orden de cocina."""
    table_id: str
    items: List[CrearArticuloOrden]
    notes: Optional[str] = None


class SalidaArticuloOrden(BaseModel):
    """Representación pública de una línea de detalle de orden."""
    id: str
    menu_item_id: str
    quantity: int
    unit_price: float
    notes: Optional[str]

    class Config:
        from_attributes = True


class SalidaOrden(BaseModel):
    """Representación pública de una orden con su detalle de artículos."""
    id: str
    table_id: str
    waiter_id: Optional[str]
    status: EstadoOrden
    total: float
    notes: Optional[str]
    items: List[SalidaArticuloOrden] = []
    created_at: datetime

    class Config:
        from_attributes = True


class SolicitudAnaliticos(BaseModel):
    """Parámetros de consulta para el módulo de analíticos."""
    restaurant_id: str
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class SalidaBurbujaIndividual(BaseModel):
    """Resultado serializable de una sola burbuja para el frontend."""
    bubble_id: str
    bubble_name: str
    score: float
    confidence: float
    feature_importances: dict


class SalidaInsightBubble(BaseModel):
    """Resultado consolidado del análisis Bubble Intelligence."""
    occupancy_prediction: float
    dominant_factor: str
    uncertainty: float
    bubble_scores: dict                # {etiqueta: score}
    bubble_details: list               # List[SalidaBurbujaIndividual] — serializado
    shap_summary: dict
    recommendations: list
    context_snapshot: dict             # Subconjunto del contexto para debug en el frontend
