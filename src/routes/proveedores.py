from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from src.dependencies import get_session
from src.domain.models import Proveedor, ProductoProveedor
from src.domain import schemas

router = APIRouter(prefix="/v1/proveedores", tags=["Proveedores"])

# --------- CRUD Proveedor ---------
@router.post("", response_model=schemas.ProveedorOut, status_code=status.HTTP_201_CREATED)
def crear_proveedor(payload: schemas.ProveedorCreate, db: Session = Depends(get_session)):
    # documento+pais únicos
    exists = db.query(Proveedor).filter(
        Proveedor.documento == payload.documento,
        Proveedor.pais == payload.pais
    ).first()
    if exists:
        raise HTTPException(status_code=409, detail="Proveedor ya existe para ese documento/pais")

    # ✅ dump a JSON-friendly (HttpUrl -> str)
    data = payload.model_dump(mode="json", exclude_none=True)
    # (opcional) asegurar por si acaso
    if data.get("pagina_web") is not None:
        data["pagina_web"] = str(data["pagina_web"])

    obj = Proveedor(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("", response_model=List[schemas.ProveedorOut])
def listar_proveedores(
    q: Optional[str] = Query(None, description="Búsqueda por nombre/documento"),
    pais: Optional[str] = Query(None, min_length=2, max_length=2),
    activo: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session)
):
    query = db.query(Proveedor)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter((Proveedor.nombre.ilike(like)) | (Proveedor.documento.ilike(like)))
    if pais:
        query = query.filter(Proveedor.pais == pais)
    if activo is not None:
        query = query.filter(Proveedor.activo == activo)
    return query.order_by(Proveedor.nombre.asc()).offset(offset).limit(limit).all()


@router.get("/{proveedor_id}", response_model=schemas.ProveedorOut)
def obtener_proveedor(proveedor_id: UUID = Path(...), db: Session = Depends(get_session)):
    obj = db.get(Proveedor, proveedor_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return obj


@router.patch("/{proveedor_id}", response_model=schemas.ProveedorOut)
def actualizar_proveedor(
    proveedor_id: UUID,
    payload: schemas.ProveedorUpdate,
    db: Session = Depends(get_session)
):
    obj = db.get(Proveedor, proveedor_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    # ✅ dump parcial seguro (solo campos enviados) y JSON-friendly
    data = payload.model_dump(mode="json", exclude_unset=True, exclude_none=True)
    if data.get("pagina_web") is not None:
        data["pagina_web"] = str(data["pagina_web"])

    # Si cambia documento+pais, mantener unicidad
    if "documento" in data or "pais" in data:
        doc = data.get("documento", obj.documento)
        pais = data.get("pais", obj.pais)
        conflict = db.query(Proveedor).filter(
            Proveedor.id != proveedor_id,
            Proveedor.documento == doc,
            Proveedor.pais == pais
        ).first()
        if conflict:
            raise HTTPException(status_code=409, detail="Conflicto de documento/pais")

    for k, v in data.items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{proveedor_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_proveedor(proveedor_id: UUID, db: Session = Depends(get_session)):
    obj = db.get(Proveedor, proveedor_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    db.delete(obj)
    db.commit()
    return None


# --------- Asociación Producto–Proveedor ---------
@router.post("/{proveedor_id}/productos", response_model=schemas.ProductoProveedorOut, status_code=status.HTTP_201_CREATED)
def asociar_producto(
    proveedor_id: UUID,
    payload: schemas.ProductoProveedorIn,
    db: Session = Depends(get_session)
):
    prov = db.get(Proveedor, proveedor_id)
    if not prov:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    rel = db.get(ProductoProveedor, {"proveedor_id": proveedor_id, "producto_id": payload.producto_id})
    if rel:
        # upsert sencillo: actualiza si ya existe
        for k, v in payload.model_dump(exclude={"producto_id"}).items():
            setattr(rel, k, v)
    else:
        rel = ProductoProveedor(proveedor_id=proveedor_id, **payload.model_dump())
        db.add(rel)

    db.commit()
    db.refresh(rel)
    return rel


@router.get("/{proveedor_id}/productos", response_model=List[schemas.ProductoProveedorOut])
def listar_productos_de_proveedor(
    proveedor_id: UUID,
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_session)
):
    prov = db.get(Proveedor, proveedor_id)
    if not prov:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    q = db.query(ProductoProveedor).filter(ProductoProveedor.proveedor_id == proveedor_id)
    if activo is not None:
        q = q.filter(ProductoProveedor.activo == activo)
    return q.order_by(ProductoProveedor.producto_id.asc()).all()


@router.delete("/{proveedor_id}/productos/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def desasociar_producto(
    proveedor_id: UUID,
    producto_id: UUID,
    db: Session = Depends(get_session)
):
    rel = db.get(ProductoProveedor, {"proveedor_id": proveedor_id, "producto_id": producto_id})
    if not rel:
        raise HTTPException(status_code=404, detail="Relación no encontrada")
    db.delete(rel)
    db.commit()
    return None


@router.get("/{producto_id}/proveedores", response_model=List[schemas.ProveedorParaProductoOut])
def listar_proveedores_por_producto(
    producto_id: UUID = Path(...),
    activo_relacion: Optional[bool] = Query(None, description="Filtrar por relación activa/inactiva"),
    activo_proveedor: Optional[bool] = Query(None, description="Filtrar por proveedor activo/inactivo"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session)
):
    """
    Devuelve los proveedores que abastecen el producto indicado,
    incluyendo los términos de compra (precio, sku_proveedor, lead time, etc.).
    """
    q = (
        db.query(ProductoProveedor, Proveedor)
        .join(Proveedor, ProductoProveedor.proveedor_id == Proveedor.id)
        .filter(ProductoProveedor.producto_id == producto_id)
    )

    if activo_relacion is not None:
        q = q.filter(ProductoProveedor.activo == activo_relacion)
    if activo_proveedor is not None:
        q = q.filter(Proveedor.activo == activo_proveedor)

    rows = q.order_by(Proveedor.nombre.asc()).offset(offset).limit(limit).all()

    resultado: List[schemas.ProveedorParaProductoOut] = []
    for rel, prov in rows:
        resultado.append(
            schemas.ProveedorParaProductoOut(
                id=prov.id,
                nombre=prov.nombre,
                tipo_de_persona=prov.tipo_de_persona,
                documento=prov.documento,
                tipo_documento=prov.tipo_documento,
                pais=prov.pais,
                direccion=prov.direccion,
                telefono=prov.telefono,
                email=prov.email,
                pagina_web=prov.pagina_web,
                activo=prov.activo,
                terminos=schemas.TerminosCompraOut(
                    sku_proveedor=rel.sku_proveedor,
                    precio=float(rel.precio) if rel.precio is not None else None,
                    moneda=rel.moneda,
                    lead_time_dias=rel.lead_time_dias,
                    lote_minimo=rel.lote_minimo,
                    activo=rel.activo,
                ),
            )
        )

    return resultado