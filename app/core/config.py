"""
Módulo de configuración centralizada de la aplicación.

Utiliza pydantic-settings para cargar variables de entorno
desde el archivo .env y validarlas con tipado estático.

Nota: los nombres de atributo corresponden exactamente a las variables de entorno
definidas en .env y constituyen una interfaz externa del sistema; por tanto,
se mantienen en inglés conforme a la convención estándar de configuración.
"""

from typing import List

from pydantic_settings import BaseSettings


class Configuracion(BaseSettings):
    """
    Configuración global de la plataforma Restaurant BI.

    Cada atributo puede sobreescribirse mediante una variable de entorno con el
    mismo nombre en mayúsculas o a través del archivo .env. Los valores por
    defecto son válidos únicamente para entornos de desarrollo local.
    """

    APP_NAME: str = "Restaurant BI Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    SECRET_KEY: str = "cambiar-en-produccion-clave-super-secreta"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    VITE_FIREBASE_API_KEY: str = ""
    VITE_FIREBASE_AUTH_DOMAIN: str = ""
    VITE_FIREBASE_PROJECT_ID: str = "reservasrestaurantes"
    VITE_FIREBASE_STORAGE_BUCKET: str = ""
    VITE_FIREBASE_MESSAGING_SENDER_ID: str = ""
    VITE_FIREBASE_APP_ID: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    FIRESTORE_USE_MEMORY: bool = False

    REDIS_URL: str = "redis://redis:6379/0"

    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "restaurant-media"

    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    RATE_LIMIT_PER_MINUTE: int = 60

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Configuracion()
