"""
Módulo principal de la plataforma Restaurant BI.
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.session import crear_tablas, repositorio, RepositorioFirestore
from app.api.v1 import auth, users, restaurants, tables, menus, kitchen, analytics, websocket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    logger.info("Iniciando Restaurant BI Platform v%s...", settings.APP_VERSION)
    await crear_tablas()

    if isinstance(repositorio, RepositorioFirestore):
        logger.info("✅ Firestore activo (proyecto: %s)", settings.VITE_FIREBASE_PROJECT_ID)
    else:
        logger.warning(
            "⚠️  Usando RepositorioMemoria — los datos NO persisten.\n"
            "    Local:   GOOGLE_APPLICATION_CREDENTIALS=secrets/archivo.json\n"
            "    Railway: FIREBASE_CREDENTIALS_BASE64=<base64 del JSON>"
        )

    yield
    logger.info("Apagando servidor...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Plataforma de Reservaciones y Business Intelligence con Bubble Intelligence Analytics",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=ciclo_de_vida,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def manejador_global_excepciones(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Excepción no controlada: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})


PREFIJO_API = "/api/v1"

app.include_router(auth.router,        prefix=PREFIJO_API)
app.include_router(users.router,       prefix=PREFIJO_API)
app.include_router(restaurants.router, prefix=PREFIJO_API)
app.include_router(tables.router,      prefix=PREFIJO_API)
app.include_router(menus.router,       prefix=PREFIJO_API)
app.include_router(kitchen.router,     prefix=PREFIJO_API)
app.include_router(analytics.router,   prefix=PREFIJO_API)
app.include_router(websocket.router)


@app.get("/health", tags=["Salud"])
async def verificar_salud() -> dict:
    return {
        "estado": "activo",
        "version": settings.APP_VERSION,
        "firestore": isinstance(repositorio, RepositorioFirestore),
    }
