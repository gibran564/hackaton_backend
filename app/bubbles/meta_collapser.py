"""
Módulo MetaCollapser del Framework Bubble Intelligence.

Agrega las señales independientes de las cinco burbujas de análisis
en una predicción operativa unificada, identificando el factor dominante,
cuantificando la incertidumbre y generando recomendaciones accionables.

Soporta dos modos de ejecución:
  - ejecutar()        → resultado completo en un solo dict (síncrono).
  - ejecutar_stream() → generador asíncrono que emite cada burbuja en tiempo
                        real vía Server-Sent Events, seguido del resultado final.
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


class MetaCollapser:
    """
    Agrega las puntuaciones aisladas de las burbujas en una predicción consolidada.

    Estrategia de colapso:
        - Promedio ponderado de puntuaciones (pesos basados en confianza del dominio).
        - Identificación del factor dominante como la burbuja de mayor puntuación.
        - Cuantificación de incertidumbre mediante desviación estándar entre burbujas.
        - Generación de recomendaciones operativas basadas en umbrales por dominio.
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

        puntuaciones = np.array([r.score for r in resultados])
        incertidumbre = float(np.std(puntuaciones))

        puntuaciones_burbuja = {
            self.ETIQUETAS_BURBUJA.get(r.bubble_id, r.bubble_id): round(r.score, 4)
            for r in resultados
        }

        resumen_shap = dict(
            sorted(dominante.feature_importances.items(), key=lambda x: x[1], reverse=True)
        )

        recomendaciones = self._generar_recomendaciones(resultados, prediccion_ocupacion, contexto)

        return {
            "occupancy_prediction": round(prediccion_ocupacion, 4),
            "dominant_factor": factor_dominante,
            "uncertainty": round(incertidumbre, 4),
            "bubble_scores": puntuaciones_burbuja,
            "shap_summary": resumen_shap,
            "recommendations": recomendaciones,
        }

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def ejecutar(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta todas las burbujas sobre el contexto y colapsa sus señales.

        Args:
            contexto: Diccionario con las 25 características de entrada.

        Returns:
            Diccionario con predicción de ocupación, factor dominante,
            incertidumbre, puntuaciones por burbuja, resumen SHAP
            y lista de recomendaciones operativas.
        """
        resultados = [self._ejecutar_burbuja(b, contexto) for b in self.burbujas]
        return self._colapsar(resultados, contexto)

    async def ejecutar_stream(
        self, contexto: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """
        Generador asíncrono que emite eventos SSE mientras ejecuta las burbujas.

        Protocolo de eventos:
          - event: bubble_result  → resultado de cada burbuja al terminar
          - event: final_result   → predicción consolidada del MetaCollapser
          - event: done           → señal de cierre del stream

        Cada línea sigue el formato SSE estándar:
            event: <nombre>\\ndata: <json>\\n\\n

        Args:
            contexto: Diccionario con las 25 características de entrada.

        Yields:
            Strings con formato SSE listos para ser escritos en la respuesta HTTP.
        """
        resultados: List[ResultadoBurbuja] = []

        for burbuja in self.burbujas:
            # Ejecuta la burbuja en un thread para no bloquear el event loop
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

        # Colapso final en thread (operaciones numpy)
        final = await asyncio.to_thread(self._colapsar, resultados, contexto)
        yield f"event: final_result\ndata: {json.dumps(final)}\n\n"
        yield "event: done\ndata: {}\n\n"

    def _generar_recomendaciones(
        self, resultados: List[ResultadoBurbuja], ocupacion: float, contexto: Dict[str, Any]
    ) -> List[str]:
        """
        Genera recomendaciones operativas basadas en los umbrales de señal de cada burbuja.

        Args:
            resultados: Lista de resultados de todas las burbujas.
            ocupacion: Predicción agregada de ocupación.
            contexto: Contexto original con características de entrada.

        Returns:
            Lista de recomendaciones en texto legible para el gerente.
        """
        recomendaciones: List[str] = []
        mapa_puntuaciones = {r.bubble_id: r.score for r in resultados}

        if ocupacion > 0.85 or contexto.get("occupancy_ratio", 0.0) > 0.85:
            recomendaciones.append(
                "Alta ocupación prevista — considere activar asientos de desbordamiento o alertas de lista de espera."
            )
        if mapa_puntuaciones.get("B3", 0.5) > 0.75 or contexto.get("kitchen_queue_depth", 0.0) > 0.85:
            recomendaciones.append(
                "Carga operativa de cocina elevada — optimice la cola de preparación y la asignación de personal."
            )
        if mapa_puntuaciones.get("B1", 0.5) > 0.80 or contexto.get("local_events", 0.0) > 0.85:
            recomendaciones.append(
                "Pico de afluencia de clientes esperado — verifique que los niveles de personal sean suficientes."
            )
        if mapa_puntuaciones.get("B4", 0.5) < 0.40:
            recomendaciones.append(
                "Señales de experiencia del cliente bajas — revise patrones de cancelación y tiempos de espera."
            )
        if mapa_puntuaciones.get("B5", 0.5) < 0.45:
            recomendaciones.append(
                "Utilización espacial subóptima — considere reorganizar la distribución de mesas en el primer piso."
            )
        if mapa_puntuaciones.get("B2", 0.5) > 0.70:
            recomendaciones.append(
                "Período de consumo de alto valor previsto — promueva artículos premium del menú."
            )
        if not recomendaciones:
            recomendaciones.append(
                "Las operaciones se encuentran dentro de los parámetros normales — mantenga la dotación y distribución actuales."
            )

        return recomendaciones
