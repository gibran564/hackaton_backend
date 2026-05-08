"""
Módulo de gestión de conexiones WebSocket por canal.

Implementa el patrón publicador/suscriptor para la difusión
de eventos en tiempo real entre los distintos módulos del sistema.
"""

import json
from typing import Dict, List

from fastapi import WebSocket


class GestorWebSocket:
    """
    Administra conexiones WebSocket agrupadas por canal lógico.

    Los canales soportados son: 'mesas', 'ordenes' y 'reservaciones'.
    Las conexiones inactivas se eliminan automáticamente durante la difusión.
    """

    def __init__(self) -> None:
        self._conexiones: Dict[str, List[WebSocket]] = {
            "mesas": [],
            "ordenes": [],
            "reservaciones": [],
        }

    async def conectar(self, canal: str, websocket: WebSocket) -> None:
        """
        Acepta y registra una nueva conexión WebSocket en el canal indicado.

        Args:
            canal: Nombre del canal de suscripción.
            websocket: Objeto de conexión WebSocket entrante.
        """
        await websocket.accept()
        if canal not in self._conexiones:
            self._conexiones[canal] = []
        self._conexiones[canal].append(websocket)

    def desconectar(self, canal: str, websocket: WebSocket) -> None:
        """
        Elimina una conexión WebSocket del registro del canal.

        Args:
            canal: Nombre del canal del que se desconecta el cliente.
            websocket: Conexión WebSocket a remover.
        """
        if canal in self._conexiones:
            self._conexiones[canal] = [
                ws for ws in self._conexiones[canal] if ws != websocket
            ]

    async def difundir(self, canal: str, carga: dict) -> None:
        """
        Difunde un mensaje JSON a todos los clientes suscritos al canal.

        Las conexiones que fallen durante el envío son removidas automáticamente.

        Args:
            canal: Canal objetivo de la difusión.
            carga: Diccionario con el payload del evento a difundir.
        """
        mensaje = json.dumps(carga)
        inactivas: List[WebSocket] = []
        for ws in self._conexiones.get(canal, []):
            try:
                await ws.send_text(mensaje)
            except Exception:
                inactivas.append(ws)
        for ws in inactivas:
            self.desconectar(canal, ws)

    async def enviar_personal(self, websocket: WebSocket, carga: dict) -> None:
        """
        Envía un mensaje JSON a un cliente WebSocket específico.

        Args:
            websocket: Conexión WebSocket destino.
            carga: Diccionario con el payload del mensaje.
        """
        await websocket.send_text(json.dumps(carga))

    def conteo_conexiones(self, canal: str) -> int:
        """
        Devuelve el número de clientes activos suscritos a un canal.

        Args:
            canal: Nombre del canal a consultar.

        Returns:
            Número de conexiones activas en el canal.
        """
        return len(self._conexiones.get(canal, []))


ws_manager = GestorWebSocket()
