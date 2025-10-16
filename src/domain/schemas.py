from pydantic import BaseModel, EmailStr, Field, HttpUrl, ConfigDict, conint, condecimal
from typing import Optional, List
from uuid import UUID
from enum import Enum

class TipoDePersona(str, Enum):
    NATURAL = "NATURAL"
    JURIDICA = "JURIDICA"

class TipoDocumento(str, Enum):
    CC = "CC"
    NIT = "NIT"
    PASAPORTE = "PASAPORTE"
    CE = "CE"

# --------- Proveedor DTOs ----------
class ProveedorBase(BaseModel):
    nombre: str = Field(..., max_length=255)
    tipo_de_persona: TipoDePersona
    documento: str = Field(..., max_length=64)
    tipo_documento: TipoDocumento
    pais: str = Field(..., min_length=2, max_length=2)
    direccion: Optional[str] = Field(None, max_length=255)
    telefono: Optional[str] = Field(None, max_length=64)
    email: Optional[EmailStr] = None
    pagina_web: Optional[HttpUrl] = None
    activo: Optional[bool] = True

class ProveedorCreate(ProveedorBase):
    pass

class ProveedorUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=255)
    tipo_de_persona: Optional[TipoDePersona] = None
    documento: Optional[str] = Field(None, max_length=64)
    tipo_documento: Optional[TipoDocumento] = None
    pais: Optional[str] = Field(None, min_length=2, max_length=2)
    direccion: Optional[str] = Field(None, max_length=255)
    telefono: Optional[str] = Field(None, max_length=64)
    email: Optional[EmailStr] = None
    pagina_web: Optional[HttpUrl] = None
    activo: Optional[bool] = None

class ProveedorOut(ProveedorBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

# ----- ProductoProveedor DTOs -------
class ProductoProveedorIn(BaseModel):
    producto_id: UUID
    sku_proveedor: Optional[str] = Field(None, max_length=128)
    precio: Optional[float] = None
    moneda: Optional[str] = Field(None, max_length=3)
    lead_time_dias: Optional[int] = None
    lote_minimo: Optional[int] = None
    activo: Optional[bool] = True

class ProductoProveedorOut(ProductoProveedorIn):
    proveedor_id: UUID
    model_config = ConfigDict(from_attributes=True)

class TerminosCompraOut(BaseModel):
    sku_proveedor: Optional[str] = Field(None, max_length=128)
    precio: Optional[float] = None
    moneda: Optional[str] = Field(None, max_length=3)
    lead_time_dias: Optional[int] = None
    lote_minimo: Optional[int] = None
    activo: bool = True

class ProveedorParaProductoOut(ProveedorOut):
    terminos: TerminosCompraOut

class ItemOCIn(BaseModel):
    producto_id: UUID
    cantidad: conint(gt=0)
    precio_unitario: Optional[condecimal(max_digits=14, decimal_places=4)] = None
    impuesto_pct:    Optional[condecimal(max_digits=5,  decimal_places=2)] = None
    descuento_pct:   Optional[condecimal(max_digits=5,  decimal_places=2)] = None
    sku_proveedor:   Optional[str] = Field(None, max_length=128)

class OrdenCompraCreate(BaseModel):
    proveedor_id: UUID
    pedido_ref: Optional[UUID] = None     # id del pedido en ms-pedidos
    moneda: Optional[str] = Field(None, max_length=3)
    notas: Optional[str]  = Field(None, max_length=500)
    codigo: Optional[str] = Field(None, max_length=32)  # si no envías, el servicio lo genera
    items: List[ItemOCIn]

class ItemOCOut(ItemOCIn):
    id: UUID
    oc_id: UUID

class OrdenCompraOut(BaseModel):
    id: UUID
    codigo: str
    proveedor_id: UUID
    pedido_ref: Optional[UUID] = None
    estado: str
    subtotal: Optional[condecimal(max_digits=14, decimal_places=4)] = None
    impuesto_total: Optional[condecimal(max_digits=14, decimal_places=4)] = None
    total: Optional[condecimal(max_digits=14, decimal_places=4)] = None
    moneda: Optional[str] = None
    notas: Optional[str] = None
    items: List[ItemOCOut] = []
