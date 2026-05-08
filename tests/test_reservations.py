"""
Pruebas unitarias del servicio de reservaciones.

Verifica el comportamiento del algoritmo de búsqueda de mesa disponible
ante distintos escenarios de disponibilidad del restaurante.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.reservation_service import buscar_mesa_disponible


@pytest.mark.asyncio
async def test_buscar_mesa_retorna_none_cuando_todas_ocupadas() -> None:
    """
    Verifica que el servicio devuelva None cuando no existe ninguna
    mesa candidata con la capacidad y disponibilidad requeridas.
    """
    mock_db = AsyncMock()

    mock_resultado = MagicMock()
    mock_resultado.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_resultado)

    mesa = await buscar_mesa_disponible(
        db=mock_db,
        restaurant_id="restaurante-001",
        party_size=4,
        scheduled_at=datetime(2026, 6, 15, 19, 0),
        duration_minutes=90,
    )
    assert mesa is None
