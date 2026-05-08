#!/usr/bin/env python3
"""
seed.py — Cargador de datos de prueba para Restaurant BI Platform.

Modos de uso:
    python seed.py                  # usa las credenciales del .env
    python seed.py --verbose        # muestra cada documento creado
    python seed.py --memoria        # fuerza modo memoria (para pruebas rápidas)
"""

import asyncio
import argparse
import os
import sys
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Carga .env antes de importar la app
from dotenv import load_dotenv
load_dotenv()

from app.core.security import cifrar_contrasena
from app.db.session import repositorio, COLECCIONES, RepositorioFirestore, RepositorioMemoria
from app.models import (
    Usuario, RolUsuario,
    Restaurante, Piso, Mesa, EstadoMesa,
    Reservacion, EstadoReservacion,
    Orden, EstadoOrden, ArticuloOrden,
    Menu, ArticuloMenu,
)

# ── Datos falsos ─────────────────────────────────────────────────────────────

RESTAURANTE = dict(
    name="Rancho Sport Grill",
    address="Av. Tecnológico 1200, Durango, Dgo.",
    phone="618-555-0101",
    email="contacto@ranchosport.mx",
    description="Restaurante con análisis BI en tiempo real",
    opening_time="07:00",
    closing_time="23:00",
    max_capacity=80,
)

PISOS = [
    dict(name="Planta Baja", floor_number=1),
    dict(name="Terraza",     floor_number=2),
]

MESAS_PLANTILLA = [
    dict(label="M-{n}", capacity=2,  pos_x=100, pos_y=100),
    dict(label="M-{n}", capacity=4,  pos_x=250, pos_y=100),
    dict(label="M-{n}", capacity=4,  pos_x=400, pos_y=100),
    dict(label="M-{n}", capacity=6,  pos_x=100, pos_y=250),
    dict(label="M-{n}", capacity=6,  pos_x=250, pos_y=250),
    dict(label="M-{n}", capacity=8,  pos_x=400, pos_y=250),
]

USUARIOS = [
    dict(email="gerente@ranchosport.mx",  full_name="Joel Ramos",       role=RolUsuario.gerente,  phone="618-555-0001"),
    dict(email="mesero1@ranchosport.mx",  full_name="Carlos Mendoza",   role=RolUsuario.mesero,   phone="618-555-0002"),
    dict(email="cocina@ranchosport.mx",   full_name="Ana Fierro",       role=RolUsuario.cocina,   phone="618-555-0003"),
    dict(email="cliente1@gmail.com",      full_name="Sofía Torres",     role=RolUsuario.cliente,  phone="618-555-0010"),
    dict(email="cliente2@gmail.com",      full_name="Diego Herrera",    role=RolUsuario.cliente,  phone="618-555-0011"),
    dict(email="cliente3@gmail.com",      full_name="Valentina Cruz",   role=RolUsuario.cliente,  phone="618-555-0012"),
]

MENU_ITEMS = [
    dict(name="Arrachera al carbón",   category="Carnes",    price=285.0, prep_time=18),
    dict(name="Tacos de brisket",      category="Tacos",     price=165.0, prep_time=12),
    dict(name="Ensalada César",        category="Ensaladas", price=120.0, prep_time=8),
    dict(name="Costillas BBQ",         category="Carnes",    price=340.0, prep_time=25),
    dict(name="Orden de alitas",       category="Botanas",   price=185.0, prep_time=15),
    dict(name="Michelada artesanal",   category="Bebidas",   price=90.0,  prep_time=3),
    dict(name="Agua de horchata 1L",   category="Bebidas",   price=55.0,  prep_time=2),
    dict(name="Pastel de tres leches", category="Postres",   price=95.0,  prep_time=5),
    dict(name="Flan napolitano",       category="Postres",   price=75.0,  prep_time=5),
    dict(name="Combo familiar",        category="Combos",    price=520.0, prep_time=30),
]

PASSWORD = "Rancho2024!"

V = "\033[92m"   # verde
A = "\033[93m"   # amarillo
N = "\033[1m"    # negrita
R = "\033[0m"    # reset


def log(msg, color=""):
    print(f"{color}{msg}{R}")


def _estado_mesa() -> EstadoMesa:
    return random.choices(
        [EstadoMesa.disponible, EstadoMesa.ocupada, EstadoMesa.reservada],
        weights=[0.45, 0.40, 0.15],
    )[0]


def _estado_reservacion() -> EstadoReservacion:
    return random.choices(
        [EstadoReservacion.confirmada, EstadoReservacion.pendiente,
         EstadoReservacion.completada, EstadoReservacion.cancelada],
        weights=[0.40, 0.25, 0.25, 0.10],
    )[0]


def _estado_orden() -> EstadoOrden:
    return random.choices(
        [EstadoOrden.pendiente, EstadoOrden.preparando,
         EstadoOrden.lista, EstadoOrden.servida],
        weights=[0.20, 0.35, 0.25, 0.20],
    )[0]


def _fecha(dias_atras=10, dias_adelante=10) -> datetime:
    delta = random.randint(-dias_atras * 1440, dias_adelante * 1440)
    return datetime.utcnow() + timedelta(minutes=delta)


async def sembrar(verbose=False) -> None:
    repo = repositorio
    es_firestore = isinstance(repo, RepositorioFirestore)
    tipo = "🔥 Firestore" if es_firestore else "💾 Memoria"

    log(f"\n{N}Restaurant BI — Seed de datos{R}")
    log(f"Repositorio: {tipo}")

    if not es_firestore:
        log(
            "\n⚠️  Sin conexión a Firestore — los datos solo existen en este proceso.\n"
            "   Local:   GOOGLE_APPLICATION_CREDENTIALS=secrets/archivo.json\n"
            "   Railway: FIREBASE_CREDENTIALS_BASE64=<base64>",
            A,
        )

    # 1. Restaurante
    log("\n1/6  Restaurante...", N)
    restaurante = Restaurante(**RESTAURANTE)
    await repo.crear(COLECCIONES["restaurants"], restaurante)
    log(f"     ✅ {restaurante.name}  ({restaurante.id})", V)

    # 2. Pisos
    log("2/6  Pisos...", N)
    pisos = []
    for p in PISOS:
        piso = Piso(restaurant_id=restaurante.id, **p)
        await repo.crear(COLECCIONES["floors"], piso)
        pisos.append(piso)
        if verbose:
            log(f"     ✅ {piso.name}", V)
    log(f"     ✅ {len(pisos)} pisos", V)

    # 3. Mesas
    log("3/6  Mesas...", N)
    mesas, n = [], 1
    for piso in pisos:
        for plantilla in MESAS_PLANTILLA:
            datos = {**plantilla, "label": plantilla["label"].format(n=n)}
            mesa = Mesa(floor_id=piso.id, status=_estado_mesa(), **datos)
            await repo.crear(COLECCIONES["tables"], mesa)
            mesas.append(mesa)
            n += 1
    log(f"     ✅ {len(mesas)} mesas", V)

    # 4. Usuarios
    log("4/6  Usuarios...", N)
    hashed = cifrar_contrasena(PASSWORD)
    usuarios = []
    for u in USUARIOS:
        usuario = Usuario(hashed_password=hashed, **u)
        await repo.crear(COLECCIONES["users"], usuario)
        usuarios.append(usuario)
        if verbose:
            log(f"     ✅ {usuario.email}  [{usuario.role.value}]", V)
    log(f"     ✅ {len(usuarios)} usuarios", V)

    # 5. Menú
    log("5/6  Menú...", N)
    menu = Menu(restaurant_id=restaurante.id, name="Menú Principal")
    await repo.crear(COLECCIONES["menus"], menu)
    articulos = []
    for item in MENU_ITEMS:
        a = ArticuloMenu(menu_id=menu.id, **item)
        await repo.crear(COLECCIONES["menu_items"], a)
        articulos.append(a)
    log(f"     ✅ {len(articulos)} artículos", V)

    # 6. Reservaciones y órdenes
    log("6/6  Reservaciones y órdenes...", N)
    clientes = [u for u in usuarios if u.role == RolUsuario.cliente]
    meseros  = [u for u in usuarios if u.role == RolUsuario.mesero]
    total_res = total_ord = 0

    for _ in range(25):
        estado = _estado_reservacion()
        mesa   = random.choice(mesas)
        res = Reservacion(
            restaurant_id=restaurante.id,
            user_id=random.choice(clientes).id,
            table_id=mesa.id,
            party_size=random.randint(1, mesa.capacity),
            scheduled_at=_fecha(),
            duration_minutes=random.choice([60, 90, 120]),
            status=estado,
            notes=random.choice([None, None, "Sin gluten", "Cumpleaños", "Ventana"]),
        )
        await repo.crear(COLECCIONES["reservations"], res)
        total_res += 1

        if estado in (EstadoReservacion.confirmada, EstadoReservacion.sentada):
            items_ord = random.sample(articulos, k=random.randint(2, 5))
            orden = Orden(
                table_id=mesa.id,
                waiter_id=meseros[0].id if meseros else None,
                status=_estado_orden(),
                total=round(sum(a.price * random.randint(1, 3) for a in items_ord), 2),
            )
            await repo.crear(COLECCIONES["orders"], orden)
            for a in items_ord:
                await repo.crear(COLECCIONES["order_items"], ArticuloOrden(
                    order_id=orden.id,
                    menu_item_id=a.id,
                    unit_price=a.price,
                    quantity=random.randint(1, 3),
                ))
            total_ord += 1

    log(f"     ✅ {total_res} reservaciones  •  {total_ord} órdenes", V)

    # Resumen
    sep = "─" * 52
    log(f"\n{N}{sep}{R}")
    log(f"  {'🔥 Firestore' if es_firestore else '💾 Memoria (sin persistencia)'}")
    log(f"  restaurant_id = {N}{restaurante.id}{R}")
    log(f"\n  Credenciales ({PASSWORD}):")
    for u in usuarios:
        log(f"    {u.email:<36} [{u.role.value}]")
    log(f"\n  Endpoint stream:")
    log(f"  POST /api/v1/analiticos/bubble-insight/stream")
    log(f'  Body: {{"restaurant_id": "{restaurante.id}"}}')
    log(f"{N}{sep}{R}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose",  action="store_true")
    parser.add_argument("--memoria",  action="store_true", help="Fuerza RepositorioMemoria")
    args = parser.parse_args()

    if args.memoria:
        os.environ["FIRESTORE_USE_MEMORY"] = "true"

    asyncio.run(sembrar(verbose=args.verbose))
