"""
Módulo de la Burbuja B1: Flujo de Clientes.

Predice el volumen de afluencia de clientes a corto plazo
utilizando variables temporales, climáticas y de contexto local.
"""

from typing import Dict, List

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler

from app.bubbles.bubble_base import BurbujasBase, ResultadoBurbuja


class BurbujaFlujoClientes(BurbujasBase):
    """
    B1 — Flujo de Clientes.

    Características: time_of_day, day_of_week, is_holiday, weather_score, local_events.
    Algoritmo: Gradient Boosting Regressor.
    Horizonte temporal: corto plazo (mismo día / próximas 4 horas).
    """

    bubble_id = "B1"
    bubble_name = "Flujo de Clientes"
    FEATURES: List[str] = ["time_of_day", "day_of_week", "is_holiday", "weather_score", "local_events"]

    def __init__(self) -> None:
        self._modelo = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
        )
        self._escalador = StandardScaler()
        self._entrenado = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Entrena el modelo de Gradient Boosting sobre el conjunto de datos proporcionado.

        Args:
            X: Matriz de características de entrenamiento (n_samples, 5).
            y: Vector objetivo con la tasa de ocupación histórica.
        """
        X_escalado = self._escalador.fit_transform(X)
        self._modelo.fit(X_escalado, y)
        self._entrenado = True

    def predict(self, X: np.ndarray) -> ResultadoBurbuja:
        """
        Predice la tasa de flujo de clientes para el vector de entrada.

        Si el modelo no ha sido entrenado, devuelve una puntuación sintética
        con distribución normal centrada en 0.6.

        Args:
            X: Vector de entrada con forma (1, 5).

        Returns:
            Resultado con puntuación normalizada en [0.0, 1.0].
        """
        if not self._entrenado:
            puntuacion = float(np.clip(np.random.normal(0.6, 0.15), 0, 1))
            return ResultadoBurbuja(
                bubble_id=self.bubble_id,
                bubble_name=self.bubble_name,
                score=puntuacion,
                confidence=0.5,
                features_used=self.FEATURES,
                feature_importances={f: 1 / len(self.FEATURES) for f in self.FEATURES},
                metadata={"modo": "sintetico"},
            )

        X_escalado = self._escalador.transform(X)
        raw = self._modelo.predict(X_escalado)[0]
        return ResultadoBurbuja(
            bubble_id=self.bubble_id,
            bubble_name=self.bubble_name,
            score=float(np.clip(raw, 0.0, 1.0)),
            confidence=0.85,
            features_used=self.FEATURES,
            feature_importances=self.get_feature_importances(),
        )

    def get_feature_importances(self) -> Dict[str, float]:
        """
        Devuelve las importancias de características del modelo entrenado.

        Returns:
            Diccionario con la importancia relativa de cada característica.
        """
        if not self._entrenado:
            return {f: 1 / len(self.FEATURES) for f in self.FEATURES}
        importancias = self._modelo.feature_importances_
        return dict(zip(self.FEATURES, importancias.tolist()))
