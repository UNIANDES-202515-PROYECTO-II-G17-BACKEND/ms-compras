from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, String, DateTime, Boolean, Numeric, Integer, ForeignKey, UniqueConstraint
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
