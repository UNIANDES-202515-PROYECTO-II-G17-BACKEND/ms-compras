from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, String, DateTime, Boolean, Numeric, Integer, ForeignKey, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

Base = declarative_base()

# -------------------------
# Proveedor (owner: ms-compras)
# -------------------------
class Proveedor(Base):
    __tablename__ = "proveedor"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(255), nullable=False)

    # identidad
    tipo_de_persona = Column(String(32), nullable=False)     # NATURAL | JURIDICA (enum simple)
    documento = Column(String(64), nullable=False)
    tipo_documento = Column(String(32), nullable=False)      # NIT/RUC/CC/CE/etc
    pais = Column(String(2), nullable=False)                 # ISO-2 recomendado

    # contacto
    direccion = Column(String(255), nullable=True)
    telefono = Column(String(64), nullable=True)
    email = Column(String(255), nullable=True)
    pagina_web = Column(String(255), nullable=True)

    # estado
    activo = Column(Boolean, nullable=False, default=True)

    # auditoría
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # relaciones
    productos = relationship("ProductoProveedor", back_populates="proveedor", cascade="all, delete-orphan")
    ordenes_compra = relationship("OrdenCompra", back_populates="proveedor", cascade="all, delete-orphan")
    __table_args__ = (
        UniqueConstraint("documento", "pais", name="uq_proveedor_documento_pais"),
    )


# ---------------------------------------
# Relación Producto–Proveedor (catálogo)
# (producto_id viene de ms-inventario)
# ---------------------------------------
class ProductoProveedor(Base):
    __tablename__ = "producto_proveedor"

    proveedor_id = Column(UUID(as_uuid=True), ForeignKey("proveedor.id", ondelete="CASCADE"), primary_key=True)
    producto_id = Column(UUID(as_uuid=True), primary_key=True)

    sku_proveedor = Column(String(128), nullable=True)
    precio = Column(Numeric(14, 4), nullable=True)
    moneda = Column(String(3), nullable=True)                # USD, COP, MXN...
    lead_time_dias = Column(Integer, nullable=True)
    lote_minimo = Column(Integer, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)

    proveedor = relationship("Proveedor", back_populates="productos")

    __table_args__ = (
        UniqueConstraint("proveedor_id", "sku_proveedor", name="uq_cat_prov_sku"),
    )

class OrdenCompra(Base):
    __tablename__ = "orden_compra"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # opcional pero MUY útil para idempotencia y trazabilidad (ej: "OC-2025-000123")
    codigo = Column(String(32), unique=True, nullable=False, index=True)

    proveedor_id = Column(UUID(as_uuid=True), ForeignKey("proveedor.id", ondelete="RESTRICT"), nullable=False)
    proveedor = relationship("Proveedor", back_populates="ordenes_compra")

    # referencia al pedido en ms-pedidos (no FK entre BDs)
    pedido_ref = Column(UUID(as_uuid=True), nullable=True)

    # estados: ABIERTA|ENVIADA|PARCIAL|COMPLETA|CANCELADA  (string simple + check)
    estado = Column(String(16), nullable=False, default="ABIERTA")

    # totales (cache/reporting)
    subtotal = Column(Numeric(14, 4), nullable=True)
    impuesto_total = Column(Numeric(14, 4), nullable=True)
    total = Column(Numeric(14, 4), nullable=True)

    moneda = Column(String(3), nullable=True)   # opcional
    notas = Column(String(500), nullable=True)

    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    items = relationship("ItemOrdenCompra", back_populates="orden_compra", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "estado IN ('ABIERTA','ENVIADA','PARCIAL','COMPLETA','CANCELADA')",
            name="ck_oc_estado"
        ),
        Index("ix_oc_proveedor_estado", "proveedor_id", "estado"),
    )


class ItemOrdenCompra(Base):
    __tablename__ = "item_orden_compra"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    oc_id = Column(UUID(as_uuid=True), ForeignKey("orden_compra.id", ondelete="CASCADE"), nullable=False)

    # producto_id viene de ms-inventario (sin FK)
    producto_id = Column(UUID(as_uuid=True), nullable=False)

    # redundancias útiles
    sku_proveedor = Column(String(128), nullable=True)

    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(14, 4), nullable=True)
    impuesto_pct = Column(Numeric(5, 2), nullable=True)    # 0..100
    descuento_pct = Column(Numeric(5, 2), nullable=True)   # 0..100

    orden_compra = relationship("OrdenCompra", back_populates="items")

    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_item_oc_cantidad_pos"),
        Index("ix_item_oc_producto", "producto_id"),
    )
