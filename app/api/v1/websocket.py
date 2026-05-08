"""
Endpoint WebSocket para comunicación en tiempo real por canales.

Soporta los canales 'mesas', 'ordenes' y 'reservaciones'.
Los clientes reciben eventos de actualización difundidos desde
los endpoints REST correspondientes.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.manager import ws_manager

router = APIRouter(tags=["WebSocket"])

CANALES_VALIDOS = {"mesas", "ordenes", "reservaciones"}


@router.websocket("/ws/{canal}")
async def endpoint_websocket(websocket: WebSocket, canal: str) -> None:
    """
    Gestiona la conexión WebSocket de un cliente a un canal específico.

    Rechaza la conexión con código 4004 si el canal no es válido.
    Mantiene la conexión activa respondiendo pings y limpia el registro
    al desconectarse.

    Args:
        websocket: Objeto de conexión WebSocket de FastAPI.
        canal: Nombre del canal al que el cliente desea suscribirse.
    """
    if canal not in CANALES_VALIDOS:
        await websocket.close(code=4004)
        return

    await ws_manager.conectar(canal, websocket)
    try:
        await ws_manager.enviar_personal(
            websocket,
            {
                "evento": "conectado",
                "canal": canal,
                "clientes": ws_manager.conteo_conexiones(canal),
            },
        )
        while True:
            dato = await websocket.receive_text()
            if dato == "ping":
                await ws_manager.enviar_personal(websocket, {"evento": "pong"})
    except WebSocketDisconnect:
        ws_manager.desconectar(canal, websocket)
