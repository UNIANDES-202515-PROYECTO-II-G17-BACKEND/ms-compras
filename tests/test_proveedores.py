
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock
from uuid import uuid4, UUID

from src.app import app
from src.domain.models import Proveedor, ProductoProveedor
from src.dependencies import get_session
from src.domain.schemas import TipoDePersona, TipoDocumento

# Mock de la base de datos
@pytest.fixture
def db_session_mock():
    db = MagicMock(spec=Session)
    return db

@pytest.fixture
def client(db_session_mock):
    app.dependency_overrides[get_session] = lambda: db_session_mock
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# Datos de prueba comunes
proveedor_data_valida = {
    "nombre": "Proveedor Test",
    "tipo_de_persona": TipoDePersona.JURIDICA.value,
    "documento": "12345678",
    "tipo_documento": TipoDocumento.NIT.value,
    "pais": "CO",
    "email": "test@proveedor.com",
    "activo": True
}

def test_crear_proveedor_exitoso(client, db_session_mock):
    # Arrange
    db_session_mock.query.return_value.filter.return_value.first.return_value = None

    # Simular el comportamiento de db.refresh, que asigna el ID
    def refresh_side_effect(obj):
        obj.id = uuid4()

    db_session_mock.refresh.side_effect = refresh_side_effect

    # Act
    response = client.post("/v1/proveedores", json=proveedor_data_valida)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == proveedor_data_valida["nombre"]
    assert data["documento"] == proveedor_data_valida["documento"]
    assert UUID(data["id"]) # Check if ID is a valid UUID
    db_session_mock.add.assert_called_once()
    db_session_mock.commit.assert_called_once()

def test_crear_proveedor_conflicto(client, db_session_mock):
    # Arrange
    db_session_mock.query.return_value.filter.return_value.first.return_value = Proveedor(**proveedor_data_valida)

    # Act
    response = client.post("/v1/proveedores", json=proveedor_data_valida)

    # Assert
    assert response.status_code == 409
    assert "Proveedor ya existe" in response.json()["detail"]

def test_listar_proveedores(client, db_session_mock):
    # Arrange
    proveedor_1 = Proveedor(id=uuid4(), nombre="Proveedor A", documento="111", pais="CO", activo=True, tipo_de_persona="NATURAL", tipo_documento="CC")
    proveedor_2 = Proveedor(id=uuid4(), nombre="Proveedor B", documento="222", pais="MX", activo=False, tipo_de_persona="JURIDICA", tipo_documento="NIT")
    db_session_mock.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [proveedor_1, proveedor_2]

    # Act
    response = client.get("/v1/proveedores")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["nombre"] == "Proveedor A"
    assert data[1]["nombre"] == "Proveedor B"

def test_obtener_proveedor_existente(client, db_session_mock):
    # Arrange
    proveedor_id = uuid4()
    db_session_mock.get.return_value = Proveedor(id=proveedor_id, nombre="Proveedor Encontrado", documento="doc", pais="CO", tipo_de_persona="NATURAL", tipo_documento="CC")

    # Act
    response = client.get(f"/v1/proveedores/{proveedor_id}")

    # Assert
    assert response.status_code == 200
    assert response.json()["nombre"] == "Proveedor Encontrado"

def test_obtener_proveedor_no_encontrado(client, db_session_mock):
    # Arrange
    proveedor_id = uuid4()
    db_session_mock.get.return_value = None

    # Act
    response = client.get(f"/v1/proveedores/{proveedor_id}")

    # Assert
    assert response.status_code == 404
    assert "Proveedor no encontrado" in response.json()["detail"]

def test_actualizar_proveedor_exitoso(client, db_session_mock):
    # Arrange
    proveedor_id = uuid4()
    proveedor_existente = Proveedor(id=proveedor_id, nombre="Original", documento="doc1", pais="CO", tipo_de_persona="JURIDICA", tipo_documento="NIT")
    db_session_mock.get.return_value = proveedor_existente
    db_session_mock.query.return_value.filter.return_value.first.return_value = None # No conflict
    update_data = {"nombre": "Actualizado", "email": "nuevo@email.com"}

    # Act
    response = client.patch(f"/v1/proveedores/{proveedor_id}", json=update_data)

    # Assert
    assert response.status_code == 200
    assert response.json()["nombre"] == "Actualizado"
    assert response.json()["email"] == "nuevo@email.com"
    db_session_mock.commit.assert_called_once()

def test_actualizar_proveedor_no_encontrado(client, db_session_mock):
    # Arrange
    proveedor_id = uuid4()
    db_session_mock.get.return_value = None
    update_data = {"nombre": "Fantasma"}

    # Act
    response = client.patch(f"/v1/proveedores/{proveedor_id}", json=update_data)

    # Assert
    assert response.status_code == 404

def test_actualizar_proveedor_conflicto(client, db_session_mock):
    # Arrange
    proveedor_id = uuid4()
    proveedor_a_actualizar = Proveedor(id=proveedor_id, nombre="Original", documento="doc1", pais="CO", tipo_de_persona="NATURAL", tipo_documento="CC")
    proveedor_conflicto = Proveedor(id=uuid4(), nombre="Otro", documento="doc2", pais="AR", tipo_de_persona="JURIDICA", tipo_documento="NIT")
    db_session_mock.get.return_value = proveedor_a_actualizar
    db_session_mock.query.return_value.filter.return_value.first.return_value = proveedor_conflicto
    update_data = {"documento": "doc2", "pais": "AR"}

    # Act
    response = client.patch(f"/v1/proveedores/{proveedor_id}", json=update_data)

    # Assert
    assert response.status_code == 409
    assert "Conflicto de documento/pais" in response.json()["detail"]


def test_eliminar_proveedor_exitoso(client, db_session_mock):
    # Arrange
    proveedor_id = uuid4()
    db_session_mock.get.return_value = Proveedor(id=proveedor_id, **proveedor_data_valida)

    # Act
    response = client.delete(f"/v1/proveedores/{proveedor_id}")

    # Assert
    assert response.status_code == 204
    db_session_mock.delete.assert_called_once()
    db_session_mock.commit.assert_called_once()

def test_eliminar_proveedor_no_encontrado(client, db_session_mock):
    # Arrange
    proveedor_id = uuid4()
    db_session_mock.get.return_value = None

    # Act
    response = client.delete(f"/v1/proveedores/{proveedor_id}")

    # Assert
    assert response.status_code == 404

def test_asociar_producto_nuevo(client, db_session_mock):
    # Arrange
    proveedor_id = uuid4()
    producto_id = uuid4()
    db_session_mock.get.side_effect = [
        Proveedor(id=proveedor_id, **proveedor_data_valida), # Primer get (proveedor)
        None                       # Segundo get (relacion)
    ]
    asociacion_data = {"producto_id": str(producto_id), "sku_proveedor": "SKU123", "activo": True}

    # Act
    response = client.post(f"/v1/proveedores/{proveedor_id}/productos", json=asociacion_data)

    # Assert
    assert response.status_code == 201
    assert response.json()["sku_proveedor"] == "SKU123"
    db_session_mock.add.assert_called_once()
    db_session_mock.commit.assert_called_once()

def test_asociar_producto_actualizar(client, db_session_mock):
    # Arrange
    proveedor_id = uuid4()
    producto_id = uuid4()
    relacion_existente = ProductoProveedor(proveedor_id=proveedor_id, producto_id=producto_id, sku_proveedor="SKU_OLD", activo=True)
    db_session_mock.get.side_effect = [
        Proveedor(id=proveedor_id, **proveedor_data_valida), # get proveedor
        relacion_existente          # get relacion
    ]
    asociacion_data = {"producto_id": str(producto_id), "sku_proveedor": "SKU_NEW", "activo": False}

    # Act
    response = client.post(f"/v1/proveedores/{proveedor_id}/productos", json=asociacion_data)

    # Assert
    assert response.status_code == 201
    assert response.json()["sku_proveedor"] == "SKU_NEW"
    assert relacion_existente.sku_proveedor == "SKU_NEW" # Verifica que el objeto fue modificado
    db_session_mock.add.assert_not_called() # No se debe agregar, se modifica
    db_session_mock.commit.assert_called_once()


def test_listar_productos_de_proveedor(client, db_session_mock):
    # Arrange
    proveedor_id = uuid4()
    producto_id_1 = uuid4()
    producto_id_2 = uuid4()
    db_session_mock.get.return_value = Proveedor(id=proveedor_id, **proveedor_data_valida)
    db_session_mock.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        ProductoProveedor(proveedor_id=proveedor_id, producto_id=producto_id_1, activo=True),
        ProductoProveedor(proveedor_id=proveedor_id, producto_id=producto_id_2, activo=False)
    ]

    # Act
    response = client.get(f"/v1/proveedores/{proveedor_id}/productos")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["producto_id"] == str(producto_id_1)

def test_desasociar_producto_exitoso(client, db_session_mock):
    # Arrange
    proveedor_id = uuid4()
    producto_id = uuid4()
    db_session_mock.get.return_value = ProductoProveedor(proveedor_id=proveedor_id, producto_id=producto_id, activo=True)

    # Act
    response = client.delete(f"/v1/proveedores/{proveedor_id}/productos/{producto_id}")

    # Assert
    assert response.status_code == 204
    db_session_mock.delete.assert_called_once()
    db_session_mock.commit.assert_called_once()

def test_desasociar_producto_no_encontrado(client, db_session_mock):
    # Arrange
    db_session_mock.get.return_value = None

    # Act
    response = client.delete(f"/v1/proveedores/{uuid4()}/productos/{uuid4()}")

    # Assert
    assert response.status_code == 404

def test_listar_proveedores_por_producto(client, db_session_mock):
    # Arrange
    producto_id = uuid4()
    proveedor_id = uuid4()
    rel = ProductoProveedor(proveedor_id=proveedor_id, producto_id=producto_id, precio=100.0, activo=True)
    
    # Evitar conflicto de kwargs duplicados para 'nombre'
    prov_data = proveedor_data_valida.copy()
    prov_data["nombre"] = "Proveedor de Producto"
    prov = Proveedor(id=proveedor_id, **prov_data)

    db_session_mock.query.return_value.join.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [(rel, prov)]

    # Act
    response = client.get(f"/v1/proveedores/{producto_id}/proveedores")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["nombre"] == "Proveedor de Producto"
    assert data[0]["terminos"]["precio"] == 100.0
