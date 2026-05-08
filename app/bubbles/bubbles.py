"""
Módulo con las burbujas B2 a B5 del Framework Bubble Intelligence.

Cada burbuja analiza un dominio funcional independiente del restaurante:
consumo, operaciones, experiencia del cliente y optimización espacial.
"""

from typing import Dict

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import MinMaxScaler, RobustScaler
from xgboost import XGBRegressor

from app.bubbles.bubble_base import BurbujasBase, ResultadoBurbuja


class BurbujaConsumo(BurbujasBase):
    """
    B2 — Patrones de Consumo.

    Características: avg_order_value, top_category_ratio, alcohol_ratio, dessert_ratio, combo_rate.
    Algoritmo: XGBoost.
    Horizonte temporal: mediano plazo (tendencias semanales).
    """

    bubble_id = "B2"
    bubble_name = "Patrones de Consumo"
    FEATURES = ["avg_order_value", "top_category_ratio", "alcohol_ratio", "dessert_ratio", "combo_rate"]

    def __init__(self) -> None:
        self._modelo = XGBRegressor(
            n_estimators=80, max_depth=3, learning_rate=0.1,
            verbosity=0, random_state=42,
        )
        self._escalador = MinMaxScaler()
        self._entrenado = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Entrena el modelo XGBoost sobre datos de consumo histórico.

        Args:
            X: Matriz de características (n_samples, 5).
            y: Vector objetivo con la tasa de ingresos normalizada.
        """
        X_escalado = self._escalador.fit_transform(X)
        self._modelo.fit(X_escalado, y)
        self._entrenado = True

    def predict(self, X: np.ndarray) -> ResultadoBurbuja:
        """
        Predice la intensidad del patrón de consumo para el período actual.

        Args:
            X: Vector de entrada con forma (1, 5).

        Returns:
            Resultado con puntuación normalizada en [0.0, 1.0].
        """
        if not self._entrenado:
            puntuacion = float(np.clip(np.random.normal(0.55, 0.12), 0, 1))
            return ResultadoBurbuja(
                self.bubble_id, self.bubble_name, puntuacion, 0.5,
                self.FEATURES, {f: 0.2 for f in self.FEATURES},
                {"modo": "sintetico"},
            )
        X_escalado = self._escalador.transform(X)
        raw = self._modelo.predict(X_escalado)[0]
        return ResultadoBurbuja(
            self.bubble_id, self.bubble_name,
            float(np.clip(raw, 0, 1)), 0.82,
            self.FEATURES, self.get_feature_importances(),
        )

    def get_feature_importances(self) -> Dict[str, float]:
        """Devuelve las importancias de características del modelo XGBoost."""
        if not self._entrenado:
            return {f: 0.2 for f in self.FEATURES}
        fi = self._modelo.feature_importances_
        return dict(zip(self.FEATURES, fi.tolist()))


class BurbujaOperaciones(BurbujasBase):
    """
    B3 — Operaciones.

    Características: avg_prep_time, staff_load, kitchen_queue_depth, order_error_rate, table_turn_rate.
    Algoritmo: Random Forest.
    Horizonte temporal: tiempo real / por hora.
    """

    bubble_id = "B3"
    bubble_name = "Operaciones"
    FEATURES = ["avg_prep_time", "staff_load", "kitchen_queue_depth", "order_error_rate", "table_turn_rate"]

    def __init__(self) -> None:
        self._modelo = RandomForestRegressor(n_estimators=120, max_depth=5, random_state=42)
        self._escalador = RobustScaler()
        self._entrenado = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Entrena el Random Forest sobre métricas operativas históricas.

        Args:
            X: Matriz de características (n_samples, 5).
            y: Vector objetivo con el índice de eficiencia operativa.
        """
        X_escalado = self._escalador.fit_transform(X)
        self._modelo.fit(X_escalado, y)
        self._entrenado = True

    def predict(self, X: np.ndarray) -> ResultadoBurbuja:
        """
        Evalúa la carga operativa actual de la cocina y el personal.

        Args:
            X: Vector de entrada con forma (1, 5).

        Returns:
            Resultado con puntuación normalizada en [0.0, 1.0].
        """
        if not self._entrenado:
            puntuacion = float(np.clip(np.random.normal(0.65, 0.10), 0, 1))
            return ResultadoBurbuja(
                self.bubble_id, self.bubble_name, puntuacion, 0.5,
                self.FEATURES, {f: 0.2 for f in self.FEATURES},
                {"modo": "sintetico"},
            )
        X_escalado = self._escalador.transform(X)
        raw = self._modelo.predict(X_escalado)[0]
        return ResultadoBurbuja(
            self.bubble_id, self.bubble_name,
            float(np.clip(raw, 0, 1)), 0.88,
            self.FEATURES, self.get_feature_importances(),
        )

    def get_feature_importances(self) -> Dict[str, float]:
        """Devuelve las importancias de características del Random Forest."""
        if not self._entrenado:
            return {f: 0.2 for f in self.FEATURES}
        fi = self._modelo.feature_importances_
        return dict(zip(self.FEATURES, fi.tolist()))


class BurbujaExperiencia(BurbujasBase):
    """
    B4 — Experiencia del Cliente.

    Características: avg_rating, cancellation_rate, return_rate, complaint_rate, avg_wait_time.
    Algoritmo: Regresión Ridge (interpretable y estable).
    Horizonte temporal: largo plazo (mensual).
    """

    bubble_id = "B4"
    bubble_name = "Experiencia del Cliente"
    FEATURES = ["avg_rating", "cancellation_rate", "return_rate", "complaint_rate", "avg_wait_time"]

    def __init__(self) -> None:
        self._modelo = Ridge(alpha=1.0)
        self._escalador = MinMaxScaler()
        self._entrenado = False
        self._coeficientes = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Entrena la Regresión Ridge y normaliza los coeficientes como importancias.

        Args:
            X: Matriz de características (n_samples, 5).
            y: Vector objetivo con el índice de satisfacción del cliente.
        """
        X_escalado = self._escalador.fit_transform(X)
        self._modelo.fit(X_escalado, y)
        self._coeficientes = np.abs(self._modelo.coef_)
        self._coeficientes = self._coeficientes / (self._coeficientes.sum() + 1e-9)
        self._entrenado = True

    def predict(self, X: np.ndarray) -> ResultadoBurbuja:
        """
        Evalúa la experiencia del cliente basándose en indicadores de satisfacción.

        Args:
            X: Vector de entrada con forma (1, 5).

        Returns:
            Resultado con puntuación normalizada en [0.0, 1.0].
        """
        if not self._entrenado:
            puntuacion = float(np.clip(np.random.normal(0.70, 0.10), 0, 1))
            return ResultadoBurbuja(
                self.bubble_id, self.bubble_name, puntuacion, 0.5,
                self.FEATURES, {f: 0.2 for f in self.FEATURES},
                {"modo": "sintetico"},
            )
        X_escalado = self._escalador.transform(X)
        raw = float(self._modelo.predict(X_escalado)[0])
        return ResultadoBurbuja(
            self.bubble_id, self.bubble_name,
            float(np.clip(raw, 0, 1)), 0.78,
            self.FEATURES, self.get_feature_importances(),
        )

    def get_feature_importances(self) -> Dict[str, float]:
        """Devuelve los coeficientes normalizados de la Regresión Ridge."""
        if self._coeficientes is None:
            return {f: 0.2 for f in self.FEATURES}
        return dict(zip(self.FEATURES, self._coeficientes.tolist()))


class BurbujaEspacial(BurbujasBase):
    """
    B5 — Optimización Espacial.

    Características: occupancy_ratio, avg_table_utilization, dead_zone_ratio, aisle_blockage, floor_score.
    Algoritmo: XGBoost.
    Horizonte temporal: tiempo real.
    """

    bubble_id = "B5"
    bubble_name = "Optimización Espacial"
    FEATURES = ["occupancy_ratio", "avg_table_utilization", "dead_zone_ratio", "aisle_blockage", "floor_score"]

    def __init__(self) -> None:
        self._modelo = XGBRegressor(
            n_estimators=60, max_depth=3, learning_rate=0.15,
            verbosity=0, random_state=42,
        )
        self._escalador = MinMaxScaler()
        self._entrenado = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Entrena el modelo XGBoost sobre métricas de distribución espacial.

        Args:
            X: Matriz de características (n_samples, 5).
            y: Vector objetivo con el índice de eficiencia espacial.
        """
        X_escalado = self._escalador.fit_transform(X)
        self._modelo.fit(X_escalado, y)
        self._entrenado = True

    def predict(self, X: np.ndarray) -> ResultadoBurbuja:
        """
        Evalúa la eficiencia del uso del espacio físico del restaurante.

        Args:
            X: Vector de entrada con forma (1, 5).

        Returns:
            Resultado con puntuación normalizada en [0.0, 1.0].
        """
        if not self._entrenado:
            puntuacion = float(np.clip(np.random.normal(0.60, 0.12), 0, 1))
            return ResultadoBurbuja(
                self.bubble_id, self.bubble_name, puntuacion, 0.5,
                self.FEATURES, {f: 0.2 for f in self.FEATURES},
                {"modo": "sintetico"},
            )
        X_escalado = self._escalador.transform(X)
        raw = self._modelo.predict(X_escalado)[0]
        return ResultadoBurbuja(
            self.bubble_id, self.bubble_name,
            float(np.clip(raw, 0, 1)), 0.80,
            self.FEATURES, self.get_feature_importances(),
        )

    def get_feature_importances(self) -> Dict[str, float]:
        """Devuelve las importancias de características del modelo XGBoost espacial."""
        if not self._entrenado:
            return {f: 0.2 for f in self.FEATURES}
        fi = self._modelo.feature_importances_
        return dict(zip(self.FEATURES, fi.tolist()))
