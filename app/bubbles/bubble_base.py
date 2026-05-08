"""
Módulo base del Framework Bubble Intelligence.

Define las interfaces abstractas y la estructura de datos compartidas
por todas las burbujas de análisis del sistema.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np


@dataclass
class ResultadoBurbuja:
    """
    Resultado estandarizado producido por cualquier burbuja de análisis.

    Attributes:
        bubble_id: Identificador único de la burbuja (ej. 'B1').
        bubble_name: Nombre descriptivo de la burbuja.
        score: Puntuación normalizada en el rango [0.0, 1.0].
        confidence: Confianza interna del modelo en la predicción.
        features_used: Lista de características utilizadas en la inferencia.
        feature_importances: Mapa de importancia por característica.
        metadata: Información adicional sobre el modo de inferencia.
    """
    bubble_id: str
    bubble_name: str
    score: float
    confidence: float
    features_used: List[str]
    feature_importances: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)


class BurbujasBase(ABC):
    """
    Clase abstracta base para todas las burbujas del Framework Bubble Intelligence.

    Cada burbuja opera sobre un subconjunto exclusivo de características
    y produce una puntuación normalizada independiente.

    Reglas del framework:
        1. Exclusividad de características: ninguna característica se comparte.
        2. Libertad algorítmica: cada burbuja puede utilizar cualquier método ML.
        3. Preprocesamiento independiente: cada burbuja gestiona su propio escalador.
        4. Aislamiento temporal: los horizontes de entrenamiento son diferenciados.
    """

    bubble_id: str
    bubble_name: str
    FEATURES: List[str]

    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Entrena el modelo interno de la burbuja.

        Args:
            X: Matriz de características de entrenamiento.
            y: Vector objetivo de entrenamiento.
        """

    @abstractmethod
    def predict(self, X: np.ndarray) -> ResultadoBurbuja:
        """
        Realiza la inferencia sobre el vector de entrada proporcionado.

        Args:
            X: Vector de características de entrada.

        Returns:
            Resultado estandarizado con puntuación e importancias.
        """

    @abstractmethod
    def get_feature_importances(self) -> Dict[str, float]:
        """
        Devuelve el mapa de importancia de características del modelo.

        Returns:
            Diccionario que asocia cada característica con su importancia.
        """

    def validar_caracteristicas(self, datos: Dict[str, Any]) -> np.ndarray:
        """
        Extrae y ordena las características requeridas desde un diccionario de entrada.

        Args:
            datos: Diccionario con todas las características del contexto.

        Returns:
            Array numpy con forma (1, n_features) listo para inferencia.

        Raises:
            ValueError: Si alguna característica requerida no está presente.
        """
        faltantes = [f for f in self.FEATURES if f not in datos]
        if faltantes:
            raise ValueError(f"[{self.bubble_id}] Características faltantes: {faltantes}")
        return np.array([datos[f] for f in self.FEATURES], dtype=float).reshape(1, -1)
