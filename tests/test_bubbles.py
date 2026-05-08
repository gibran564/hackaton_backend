"""
Pruebas unitarias del Framework Bubble Intelligence.

Verifica el comportamiento del MetaCollapser, la operación de cada
burbuja en modo sintético (sin entrenamiento) y la validación de características.
"""

import pytest

from app.bubbles.b1_customer_flow import BurbujaFlujoClientes
from app.bubbles.bubbles import (
    BurbujaConsumo,
    BurbujaEspacial,
    BurbujaExperiencia,
    BurbujaOperaciones,
)
from app.bubbles.meta_collapser import MetaCollapser

CONTEXTO_MUESTRA = {
    "time_of_day": 0.75,
    "day_of_week": 0.57,
    "is_holiday": 0.0,
    "weather_score": 0.8,
    "local_events": 0.5,
    "avg_order_value": 0.6,
    "top_category_ratio": 0.45,
    "alcohol_ratio": 0.3,
    "dessert_ratio": 0.2,
    "combo_rate": 0.35,
    "avg_prep_time": 0.55,
    "staff_load": 0.7,
    "kitchen_queue_depth": 0.4,
    "order_error_rate": 0.05,
    "table_turn_rate": 0.65,
    "avg_rating": 0.82,
    "cancellation_rate": 0.08,
    "return_rate": 0.50,
    "complaint_rate": 0.02,
    "avg_wait_time": 0.25,
    "occupancy_ratio": 0.72,
    "avg_table_utilization": 0.65,
    "dead_zone_ratio": 0.08,
    "aisle_blockage": 0.04,
    "floor_score": 0.80,
}


def test_meta_collapser_ejecuta_correctamente() -> None:
    """
    Verifica que el MetaCollapser produzca una salida estructuralmente correcta.

    Comprueba la presencia de todos los campos requeridos y que la predicción
    de ocupación se encuentre dentro del rango [0.0, 1.0].
    """
    collapser = MetaCollapser()
    resultado = collapser.ejecutar(CONTEXTO_MUESTRA)

    assert "occupancy_prediction" in resultado
    assert 0.0 <= resultado["occupancy_prediction"] <= 1.0
    assert "dominant_factor" in resultado
    assert isinstance(resultado["dominant_factor"], str)
    assert "uncertainty" in resultado
    assert "bubble_scores" in resultado
    assert len(resultado["bubble_scores"]) == 5
    assert "recommendations" in resultado
    assert len(resultado["recommendations"]) >= 1


def test_todas_las_burbujas_predicen_sin_entrenamiento() -> None:
    """
    Verifica que cada burbuja genere una puntuación sintética válida
    cuando el modelo aún no ha sido entrenado con datos reales.
    """
    for ClaseBurbuja in [
        BurbujaFlujoClientes,
        BurbujaConsumo,
        BurbujaOperaciones,
        BurbujaExperiencia,
        BurbujaEspacial,
    ]:
        burbuja = ClaseBurbuja()
        X = burbuja.validar_caracteristicas(CONTEXTO_MUESTRA)
        resultado = burbuja.predict(X)

        assert 0.0 <= resultado.score <= 1.0
        assert resultado.bubble_id is not None
        assert isinstance(resultado.feature_importances, dict)


def test_validacion_caracteristicas_lanza_error_por_faltantes() -> None:
    """
    Verifica que la validación de características lance ValueError
    cuando el contexto de entrada está incompleto.
    """
    burbuja = BurbujaFlujoClientes()
    contexto_incompleto = {"time_of_day": 0.5}

    with pytest.raises(ValueError, match="Características faltantes"):
        burbuja.validar_caracteristicas(contexto_incompleto)


def test_recomendaciones_con_alta_ocupacion() -> None:
    """
    Verifica que el MetaCollapser genere recomendaciones relacionadas con
    ocupación o flujo de clientes cuando todas las señales son elevadas.
    """
    collapser = MetaCollapser()
    contexto_alto = {k: 0.95 for k in CONTEXTO_MUESTRA}
    resultado = collapser.ejecutar(contexto_alto)

    texto_recomendaciones = " ".join(resultado["recommendations"]).lower()
    assert "ocupación" in texto_recomendaciones or "afluencia" in texto_recomendaciones or "cocina" in texto_recomendaciones
