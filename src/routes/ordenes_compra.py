from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from src.dependencies import get_session
from src.domain import schemas
from src.services.orden_compra import OrdenCompraService

router = APIRouter(prefix="/v1/ordenes-compra", tags=["OrdenesCompra"])

@router.post("", response_model=schemas.OrdenCompraOut, status_code=status.HTTP_201_CREATED)
def crear_oc(payload: schemas.OrdenCompraCreate, db: Session = Depends(get_session)):
    svc = OrdenCompraService(db)
    try:
        oc = svc.crear(
            proveedor_id=payload.proveedor_id,
            items=[it.model_dump() for it in payload.items],
            pedido_ref=payload.pedido_ref,
            moneda=payload.moneda,
            notas=payload.notas,
            codigo=payload.codigo
        )
        # carga eager items para respuesta
        oc.items  # accede para materializar
        return oc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error creando la orden de compra")

@router.get("", response_model=List[schemas.OrdenCompraOut])
def listar_oc(
    proveedor_id: Optional[UUID] = Query(None),
    estado: Optional[str] = Query(None, description="ABIERTA|ENVIADA|PARCIAL|COMPLETA|CANCELADA"),
    q: Optional[str] = Query(None, description="búsqueda por código"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session)
):
    svc = OrdenCompraService(db)
    return svc.listar(proveedor_id, estado, q, limit, offset)

@router.get("/{oc_id}", response_model=schemas.OrdenCompraOut)
def obtener_oc(oc_id: UUID = Path(...), db: Session = Depends(get_session)):
    svc = OrdenCompraService(db)
    oc = svc.obtener(oc_id)
    if not oc:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    oc.items
    return oc

@router.post("/{oc_id}/marcar-enviada", response_model=schemas.OrdenCompraOut)
def marcar_enviada(oc_id: UUID, db: Session = Depends(get_session)):
    svc = OrdenCompraService(db)
    try:
        return svc.marcar_enviada(oc_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{oc_id}/marcar-completa", response_model=schemas.OrdenCompraOut)
def marcar_completa(oc_id: UUID, db: Session = Depends(get_session)):
    svc = OrdenCompraService(db)
    try:
        return svc.marcar_completa(oc_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")

@router.post("/{oc_id}/cancelar", response_model=schemas.OrdenCompraOut)
def cancelar_oc(oc_id: UUID, db: Session = Depends(get_session)):
    svc = OrdenCompraService(db)
    try:
        return svc.cancelar(oc_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{oc_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_oc(oc_id: UUID, db: Session = Depends(get_session)):
    svc = OrdenCompraService(db)
    try:
        svc.eliminar(oc_id)
        return None
    except LookupError:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")