from pydantic import BaseModel, EmailStr, Field, HttpUrl, ConfigDict
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
