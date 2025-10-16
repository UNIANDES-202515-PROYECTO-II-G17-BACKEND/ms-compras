from __future__ import annotations
from decimal import Decimal
from typing import Iterable, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from src.domain.models import OrdenCompra, ItemOrdenCompra, Proveedor, ProductoProveedor

ESTADOS_VALIDOS = {"ABIERTA","ENVIADA","PARCIAL","COMPLETA","CANCELADA"}

def _dec(v, default="0"):
    return Decimal(str(v if v is not None else default))

def _calc_totales(items: Iterable[dict[str, object]]):
    subtotal = Decimal("0")
    impuestos = Decimal("0")
    for it in items:
        pu   = _dec(it.get("precio_unitario"))
        cant = _dec(it.get("cantidad"), "0")
        li   = pu * cant
        dsc  = li * _dec(it.get("descuento_pct")) / Decimal("100")
        neto = li - dsc
        imp  = neto * _dec(it.get("impuesto_pct")) / Decimal("100")
        subtotal += neto
        impuestos += imp
    return subtotal, impuestos, (subtotal + impuestos)

class OrdenCompraService:
    def __init__(self, db: Session):
        self.db = db

    # --------- CREATE ----------
    def crear(
        self,
        proveedor_id: UUID,
        items: list[dict],
        pedido_ref: Optional[UUID] = None,
        moneda: Optional[str] = None,
        notas: Optional[str] = None,
        codigo: Optional[str] = None,
    ) -> OrdenCompra:
        # 1) Validaciones base
        prov = self.db.get(Proveedor, proveedor_id)
        if not prov or not prov.activo:
            raise ValueError("Proveedor inválido o inactivo")

        if not items:
            raise ValueError("La orden debe tener items")

        # 2) Validar catálogo proveedor-producto (existencia relación)
        producto_ids = {it["producto_id"] for it in items}
        rels = (
            self.db.query(ProductoProveedor)
            .filter(ProductoProveedor.proveedor_id == proveedor_id,
                    ProductoProveedor.producto_id.in_(list(producto_ids)))
            .all()
        )
        valid_ids = {r.producto_id for r in rels}
        missing = producto_ids - valid_ids
        if missing:
            raise ValueError(f"Producto(s) no ofertados por el proveedor: {', '.join(map(str, missing))}")

        # 3) Generar código si no llega
        if not codigo:
            codigo = f"OC-{datetime.utcnow().year}-{uuid.uuid4().hex[:6].upper()}"

        # 4) Calcular totales
        subtotal, imp, total = _calc_totales(items)

        # 5) Persistir
        oc = OrdenCompra(
            codigo=codigo,
            proveedor_id=proveedor_id,
            pedido_ref=pedido_ref,
            moneda=moneda,
            notas=notas,
            subtotal=subtotal,
            impuesto_total=imp,
            total=total,
            estado="ABIERTA",
        )
        self.db.add(oc)
        self.db.flush()  # para obtener oc.id

        # 6) Crear items (snapshot sku/precio si llega, o copias del catálogo)
        #    Rellenar sku_proveedor desde catálogo si no vino en el payload
        rel_map = {r.producto_id: r for r in rels}
        for it in items:
            rel = rel_map[it["producto_id"]]
            self.db.add(
                ItemOrdenCompra(
                    oc_id=oc.id,
                    producto_id=it["producto_id"],
                    cantidad=it["cantidad"],
                    precio_unitario=it.get("precio_unitario"),
                    impuesto_pct=it.get("impuesto_pct"),
                    descuento_pct=it.get("descuento_pct"),
                    sku_proveedor=it.get("sku_proveedor") or rel.sku_proveedor
                )
            )

        self.db.commit()
        self.db.refresh(oc)
        return oc

    # --------- READ ----------
    def obtener(self, oc_id: UUID) -> Optional[OrdenCompra]:
        return self.db.get(OrdenCompra, oc_id)

    def listar(self, proveedor_id: Optional[UUID], estado: Optional[str], q: Optional[str],
               limit: int = 50, offset: int = 0) -> list[OrdenCompra]:
        qy = self.db.query(OrdenCompra)
        if proveedor_id:
            qy = qy.filter(OrdenCompra.proveedor_id == proveedor_id)
        if estado:
            qy = qy.filter(OrdenCompra.estado == estado)
        if q:
            like = f"%{q.strip()}%"
            qy = qy.filter(OrdenCompra.codigo.ilike(like))
        return qy.order_by(OrdenCompra.creado_en.desc()).offset(offset).limit(limit).all()

    # --------- UPDATE (estados mínimos) ----------
    def marcar_enviada(self, oc_id: UUID) -> OrdenCompra:
        oc = self._ensure(oc_id)
        if oc.estado not in {"ABIERTA","PARCIAL"}:
            raise ValueError("Transición no válida")
        oc.estado = "ENVIADA"
        self.db.commit(); self.db.refresh(oc)
        return oc

    def marcar_completa(self, oc_id: UUID) -> OrdenCompra:
        oc = self._ensure(oc_id)
        oc.estado = "COMPLETA"
        self.db.commit(); self.db.refresh(oc)
        return oc

    def cancelar(self, oc_id: UUID) -> OrdenCompra:
        oc = self._ensure(oc_id)
        if oc.estado in {"COMPLETA","CANCELADA"}:
            raise ValueError("No puede cancelarse una OC completa/cancelada")
        oc.estado = "CANCELADA"
        self.db.commit(); self.db.refresh(oc)
        return oc

    # --------- DELETE ----------
    def eliminar(self, oc_id: UUID) -> None:
        oc = self._ensure(oc_id)
        self.db.delete(oc); self.db.commit()

    # --------- helpers ----------
    def _ensure(self, oc_id: UUID) -> OrdenCompra:
        oc = self.obtener(oc_id)
        if not oc:
            raise LookupError("Orden de compra no encontrada")
        return oc
