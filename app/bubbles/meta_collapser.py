"""
Módulo MetaCollapser del Framework Bubble Intelligence.

Agrega las señales independientes de las cinco burbujas de análisis
en una predicción operativa unificada.

CAMBIOS v2:
  - _inicializar_con_datos_sinteticos(): entrena cada burbuja con datos
    representativos del dominio restaurantero al instanciar el collapser.
    Esto elimina el modo 'sintetico' de las burbujas y activa las importancias
    de características reales del modelo.
  - _colapsar(): expone bubble_details con el detalle individual de cada burbuja.
  - context_snapshot: devuelve un subconjunto del contexto para inspección en el frontend.
"""

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List

import numpy as np

from app.bubbles.b1_customer_flow import BurbujaFlujoClientes
from app.bubbles.bubble_base import ResultadoBurbuja
from app.bubbles.bubbles import (
    BurbujaConsumo,
    BurbujaEspacial,
    BurbujaExperiencia,
    BurbujaOperaciones,
)


# ---------------------------------------------------------------------------
# Generadores de datos sintéticos por dominio
# ---------------------------------------------------------------------------

def _generar_datos_b1(n: int = 300) -> tuple:
    """
    B1 — Flujo de Clientes.
    y: ocupación real basada en hora + día + eventos.
    """
    rng = np.random.default_rng(0)
    time_of_day   = rng.uniform(0, 1, n)           # hora normalizada 0-23 → 0-1
    day_of_week   = rng.integers(0, 7, n) / 6.0
    is_holiday    = rng.choice([0.0, 1.0], n, p=[0.85, 0.15])
    weather_score = rng.uniform(0.2, 1.0, n)
    local_events  = rng.choice([0.0, 0.5, 1.0], n, p=[0.6, 0.25, 0.15])

    X = np.column_stack([time_of_day, day_of_week, is_holiday, weather_score, local_events])

    # Modelo de ocupación realista: pico en cenas (0.7-0.9 normalizado), más alto en fines
    lunch_peak  = np.exp(-((time_of_day - 0.52) ** 2) / 0.012)   # ~12h
    dinner_peak = np.exp(-((time_of_day - 0.83) ** 2) / 0.008)   # ~19-20h
    y = (
        0.3 * lunch_peak
        + 0.6 * dinner_peak
        + 0.15 * day_of_week
        + 0.10 * is_holiday
        + 0.08 * local_events
        + rng.normal(0, 0.04, n)
    )
    return X, np.clip(y, 0.0, 1.0)


def _generar_datos_b2(n: int = 300) -> tuple:
    """B2 — Patrones de Consumo."""
    rng = np.random.default_rng(1)
    avg_order     = rng.uniform(0.2, 1.0, n)
    top_cat       = rng.uniform(0.3, 0.9, n)
    alcohol       = rng.beta(2, 5, n)
    dessert       = rng.beta(1.5, 4, n)
    combo         = rng.beta(2, 3, n)
    X = np.column_stack([avg_order, top_cat, alcohol, dessert, combo])
    y = 0.40 * avg_order + 0.25 * top_cat + 0.15 * alcohol + 0.10 * dessert + 0.10 * combo
    y += rng.normal(0, 0.03, n)
    return X, np.clip(y, 0.0, 1.0)


def _generar_datos_b3(n: int = 300) -> tuple:
    """B3 — Operaciones (score alto = alta carga; usar invertido para eficiencia)."""
    rng = np.random.default_rng(2)
    prep_time    = rng.uniform(0.1, 1.0, n)
    staff_load   = rng.uniform(0.1, 1.0, n)
    queue_depth  = rng.beta(2, 3, n)
    error_rate   = rng.beta(1.5, 8, n)
    turn_rate    = rng.uniform(0.2, 1.0, n)
    X = np.column_stack([prep_time, staff_load, queue_depth, error_rate, turn_rate])
    # Score de operaciones: carga operativa (alto = mucho trabajo)
    y = 0.25 * staff_load + 0.30 * queue_depth + 0.20 * prep_time + 0.15 * error_rate + 0.10 * turn_rate
    y += rng.normal(0, 0.03, n)
    return X, np.clip(y, 0.0, 1.0)


def _generar_datos_b4(n: int = 300) -> tuple:
    """B4 — Experiencia del Cliente (score alto = mejor experiencia)."""
    rng = np.random.default_rng(3)
    avg_rating    = rng.beta(8, 2, n)        # Mayoría alta (restaurante bueno)
    cancel_rate   = rng.beta(1.5, 8, n)
    return_rate   = rng.beta(4, 3, n)
    complaint     = rng.beta(1, 10, n)
    wait_time     = rng.uniform(0.1, 0.8, n)
    X = np.column_stack([avg_rating, cancel_rate, return_rate, complaint, wait_time])
    y = 0.40 * avg_rating + 0.25 * return_rate - 0.20 * cancel_rate - 0.10 * complaint - 0.05 * wait_time
    y += rng.normal(0, 0.03, n)
    return X, np.clip(y, 0.0, 1.0)


def _generar_datos_b5(n: int = 300) -> tuple:
    """B5 — Optimización Espacial."""
    rng = np.random.default_rng(4)
    occupancy     = rng.uniform(0.1, 1.0, n)
    table_util    = occupancy * rng.uniform(0.7, 1.0, n)
    dead_zone     = rng.beta(1.5, 5, n)
    aisle         = rng.beta(1, 8, n)
    floor_score   = rng.uniform(0.5, 1.0, n)
    X = np.column_stack([occupancy, table_util, dead_zone, aisle, floor_score])
    y = 0.35 * occupancy + 0.30 * table_util + 0.20 * floor_score - 0.10 * dead_zone - 0.05 * aisle
    y += rng.normal(0, 0.03, n)
    return X, np.clip(y, 0.0, 1.0)


# ---------------------------------------------------------------------------
# MetaCollapser
# ---------------------------------------------------------------------------

class MetaCollapser:
    """
    Agrega las puntuaciones aisladas de las burbujas en una predicción consolidada.
    """

    PESOS: Dict[str, float] = {
        "B1": 0.25,
        "B2": 0.20,
        "B3": 0.25,
        "B4": 0.15,
        "B5": 0.15,
    }

    ETIQUETAS_BURBUJA: Dict[str, str] = {
        "B1": "flujo_clientes",
        "B2": "consumo",
        "B3": "operaciones",
        "B4": "experiencia",
        "B5": "espacial",
    }

    def __init__(self) -> None:
        self.burbujas = [
            BurbujaFlujoClientes(),
            BurbujaConsumo(),
            BurbujaOperaciones(),
            BurbujaExperiencia(),
            BurbujaEspacial(),
        ]
        # Entrenar inmediatamente con datos sintéticos representativos
        self._inicializar_con_datos_sinteticos()

    # ------------------------------------------------------------------
    # Entrenamiento sintético
    # ------------------------------------------------------------------

    def _inicializar_con_datos_sinteticos(self) -> None:
        """
        Entrena cada burbuja con datos sintéticos que representan
        patrones reales del dominio restaurantero.

        Este paso garantiza que las burbujas nunca operen en modo
        'sintetico' (score aleatorio) y produzcan feature importances
        reales desde el primer análisis.
        """
        generadores = [
            _generar_datos_b1,
            _generar_datos_b2,
            _generar_datos_b3,
            _generar_datos_b4,
            _generar_datos_b5,
        ]
        for burbuja, gen in zip(self.burbujas, generadores):
            X, y = gen()
            burbuja.fit(X, y)

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _ejecutar_burbuja(self, burbuja: Any, contexto: Dict[str, Any]) -> ResultadoBurbuja:
        """Ejecuta una sola burbuja con manejo de errores y valor de respaldo."""
        try:
            X = burbuja.validar_caracteristicas(contexto)
            return burbuja.predict(X)
        except ValueError:
            return ResultadoBurbuja(
                bubble_id=burbuja.bubble_id,
                bubble_name=burbuja.bubble_name,
                score=0.5,
                confidence=0.0,
                features_used=[],
                feature_importances={},
                metadata={"modo": "respaldo"},
            )

    def _colapsar(
        self, resultados: List[ResultadoBurbuja], contexto: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Agrega los resultados de todas las burbujas en el resultado final."""
        puntuaciones_ponderadas = np.array([
            r.score * self.PESOS.get(r.bubble_id, 0.2) for r in resultados
        ])
        peso_total = sum(self.PESOS.get(r.bubble_id, 0.2) for r in resultados)
        prediccion_ocupacion = float(puntuaciones_ponderadas.sum() / peso_total)

        dominante = max(resultados, key=lambda r: r.score)
        factor_dominante = self.ETIQUETAS_BURBUJA.get(dominante.bubble_id, dominante.bubble_name)

        puntuaciones_array = np.array([r.score for r in resultados])
        incertidumbre = float(np.std(puntuaciones_array))

        puntuaciones_burbuja = {
            self.ETIQUETAS_BURBUJA.get(r.bubble_id, r.bubble_id): round(r.score, 4)
            for r in resultados
        }

        # Detalle individual para el frontend (tabla / radar chart)
        bubble_details = [
            {
                "bubble_id": r.bubble_id,
                "bubble_name": r.bubble_name,
                "score": round(r.score, 4),
                "confidence": round(r.confidence, 4),
                "feature_importances": {
                    k: round(v, 4) for k, v in r.feature_importances.items()
                },
            }
            for r in resultados
        ]

        resumen_shap = dict(
            sorted(dominante.feature_importances.items(), key=lambda x: x[1], reverse=True)
        )

        recomendaciones = self._generar_recomendaciones(resultados, prediccion_ocupacion, contexto)

        # Subconjunto del contexto relevante para mostrar en el frontend
        context_snapshot = {
            "occupancy_ratio": round(contexto.get("occupancy_ratio", 0), 3),
            "kitchen_queue_depth": round(contexto.get("kitchen_queue_depth", 0), 3),
            "staff_load": round(contexto.get("staff_load", 0), 3),
            "avg_order_value": round(contexto.get("avg_order_value", 0), 3),
            "avg_rating": round(contexto.get("avg_rating", 0), 3),
            "time_of_day": round(contexto.get("time_of_day", 0), 3),
            "day_of_week": round(contexto.get("day_of_week", 0), 3),
        }

        return {
            "occupancy_prediction": round(prediccion_ocupacion, 4),
            "dominant_factor": factor_dominante,
            "uncertainty": round(incertidumbre, 4),
            "bubble_scores": puntuaciones_burbuja,
            "bubble_details": bubble_details,
            "shap_summary": resumen_shap,
            "recommendations": recomendaciones,
            "context_snapshot": context_snapshot,
        }

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def ejecutar(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        resultados = [self._ejecutar_burbuja(b, contexto) for b in self.burbujas]
        return self._colapsar(resultados, contexto)

    async def ejecutar_stream(
        self, contexto: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        resultados: List[ResultadoBurbuja] = []

        for burbuja in self.burbujas:
            resultado = await asyncio.to_thread(self._ejecutar_burbuja, burbuja, contexto)
            resultados.append(resultado)

            etiqueta = self.ETIQUETAS_BURBUJA.get(resultado.bubble_id, resultado.bubble_id)
            payload = {
                "bubble_id": resultado.bubble_id,
                "bubble_name": resultado.bubble_name,
                "etiqueta": etiqueta,
                "score": round(resultado.score, 4),
                "confidence": round(resultado.confidence, 4),
                "feature_importances": {
                    k: round(v, 4) for k, v in resultado.feature_importances.items()
                },
                "metadata": resultado.metadata,
            }
            yield f"event: bubble_result\ndata: {json.dumps(payload)}\n\n"

        final = await asyncio.to_thread(self._colapsar, resultados, contexto)
        yield f"event: final_result\ndata: {json.dumps(final)}\n\n"
        yield "event: done\ndata: {}\n\n"

    # ------------------------------------------------------------------
    # Generación de recomendaciones
    # ------------------------------------------------------------------

    def _generar_recomendaciones(
        self, resultados: List[ResultadoBurbuja], ocupacion: float, contexto: Dict[str, Any]
    ) -> List[str]:
        recomendaciones: List[str] = []
        mapa = {r.bubble_id: r.score for r in resultados}

        if ocupacion > 0.85 or contexto.get("occupancy_ratio", 0.0) > 0.85:
            recomendaciones.append(
                "Alta ocupación prevista — considere activar asientos de desbordamiento o alertas de lista de espera."
            )
        if mapa.get("B3", 0.5) > 0.75 or contexto.get("kitchen_queue_depth", 0.0) > 0.85:
            recomendaciones.append(
                "Carga operativa de cocina elevada — optimice la cola de preparación y la asignación de personal."
            )
        if mapa.get("B1", 0.5) > 0.80 or contexto.get("local_events", 0.0) > 0.85:
            recomendaciones.append(
                "Pico de afluencia de clientes esperado — verifique que los niveles de personal sean suficientes."
            )
        if mapa.get("B4", 0.5) < 0.40:
            recomendaciones.append(
                "Señales de experiencia del cliente bajas — revise patrones de cancelación y tiempos de espera."
            )
        if mapa.get("B5", 0.5) < 0.45:
            recomendaciones.append(
                "Utilización espacial subóptima — considere reorganizar la distribución de mesas."
            )
        if mapa.get("B2", 0.5) > 0.70:
            recomendaciones.append(
                "Período de consumo de alto valor previsto — promueva artículos premium del menú."
            )
        if not recomendaciones:
            recomendaciones.append(
                "Las operaciones se encuentran dentro de los parámetros normales — mantenga la dotación y distribución actuales."
            )
        return recomendaciones
