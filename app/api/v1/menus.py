"""Endpoints de gestión de menús y artículos del menú."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import requerir_gerente
from app.db.session import COLECCIONES, obtener_db
from app.models import ArticuloMenu, Menu, Usuario
from app.schemas import (
    ActualizarArticuloMenu,
    CrearArticuloMenu,
    CrearMenu,
    SalidaArticuloMenu,
    SalidaMenu,
)

router = APIRouter(tags=["Menús"])


@router.post("/restaurantes/{restaurant_id}/menus", response_model=SalidaMenu, status_code=201)
async def crear_menu(
    restaurant_id: str,
    payload: CrearMenu,
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_gerente),
) -> SalidaMenu:
    menu = Menu(restaurant_id=restaurant_id, **payload.model_dump())
    return await db.crear(COLECCIONES["menus"], menu)


@router.get("/restaurantes/{restaurant_id}/menus", response_model=List[SalidaMenu])
async def listar_menus(
    restaurant_id: str,
    db=Depends(obtener_db),
) -> List[SalidaMenu]:
    menus = await db.listar(
        COLECCIONES["menus"],
        Menu,
        [("restaurant_id", "==", restaurant_id), ("is_active", "==", True)],
    )
    for menu in menus:
        menu.items = await db.listar(
            COLECCIONES["menu_items"],
            ArticuloMenu,
            [("menu_id", "==", menu.id), ("available", "==", True)],
        )
    return menus


@router.post("/menus/{menu_id}/articulos", response_model=SalidaArticuloMenu, status_code=201)
async def agregar_articulo(
    menu_id: str,
    payload: CrearArticuloMenu,
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_gerente),
) -> SalidaArticuloMenu:
    articulo = ArticuloMenu(menu_id=menu_id, **payload.model_dump())
    return await db.crear(COLECCIONES["menu_items"], articulo)


@router.patch("/articulos/{item_id}", response_model=SalidaArticuloMenu)
async def actualizar_articulo(
    item_id: str,
    payload: ActualizarArticuloMenu,
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_gerente),
) -> SalidaArticuloMenu:
    articulo = await db.obtener(COLECCIONES["menu_items"], item_id, ArticuloMenu)
    if not articulo:
        raise HTTPException(status_code=404, detail="Artículo del menú no encontrado")
    return await db.actualizar(
        COLECCIONES["menu_items"],
        articulo,
        payload.model_dump(exclude_none=True),
    )


@router.delete("/articulos/{item_id}", status_code=204)
async def eliminar_articulo(
    item_id: str,
    db=Depends(obtener_db),
    _: Usuario = Depends(requerir_gerente),
) -> None:
    articulo = await db.obtener(COLECCIONES["menu_items"], item_id, ArticuloMenu)
    if not articulo:
        raise HTTPException(status_code=404, detail="Artículo del menú no encontrado")
    await db.actualizar(COLECCIONES["menu_items"], articulo, {"available": False})
