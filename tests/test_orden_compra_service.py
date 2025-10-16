
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest
from src.services.orden_compra import OrdenCompraService
from src.domain.models import OrdenCompra, ItemOrdenCompra, Proveedor, ProductoProveedor


def test_crear_orden_compra_exitosa():
    # Arrange
    db_session = MagicMock()
    service = OrdenCompraService(db_session)

    proveedor_id = uuid.uuid4()
    producto_id = uuid.uuid4()
    items = [
        {
            "producto_id": producto_id,
            "cantidad": 2,
            "precio_unitario": 10.0,
            "impuesto_pct": 10,
            "descuento_pct": 5,
        }
    ]

    mock_proveedor = MagicMock(spec=Proveedor)
    mock_proveedor.activo = True
    db_session.get.return_value = mock_proveedor

    mock_rel = MagicMock(spec=ProductoProveedor)
    mock_rel.producto_id = producto_id
    mock_rel.sku_proveedor = 'SKU_FROM_CATALOG'
    db_session.query.return_value.filter.return_value.all.return_value = [mock_rel]

    # Act
    result = service.crear(proveedor_id, items)

    # Assert
    assert result is not None
    assert isinstance(result, OrdenCompra)
    assert result.proveedor_id == proveedor_id
    assert result.subtotal == Decimal("19.0")
    assert result.impuesto_total == Decimal("1.9")
    assert result.total == Decimal("20.9")

    assert db_session.add.call_count == 2
    added_item = db_session.add.call_args_list[1].args[0]
    assert isinstance(added_item, ItemOrdenCompra)
    assert added_item.sku_proveedor == 'SKU_FROM_CATALOG'

    db_session.commit.assert_called_once()
    db_session.refresh.assert_called_once_with(result)


def test_crear_orden_compra_proveedor_invalido():
    # Arrange
    db_session = MagicMock()
    service = OrdenCompraService(db_session)

    proveedor_id = uuid.uuid4()
    items = [{"producto_id": uuid.uuid4(), "cantidad": 1}]

    db_session.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="Proveedor inválido o inactivo"):
        service.crear(proveedor_id, items)


def test_crear_orden_compra_sin_items():
    # Arrange
    db_session = MagicMock()
    service = OrdenCompraService(db_session)

    proveedor_id = uuid.uuid4()
    mock_proveedor = MagicMock(spec=Proveedor)
    mock_proveedor.activo = True
    db_session.get.return_value = mock_proveedor

    # Act & Assert
    with pytest.raises(ValueError, match="La orden debe tener items"):
        service.crear(proveedor_id, [])


def test_crear_orden_compra_productos_no_ofertados():
    # Arrange
    db_session = MagicMock()
    service = OrdenCompraService(db_session)

    proveedor_id = uuid.uuid4()
    items = [{"producto_id": uuid.uuid4(), "cantidad": 1}]
    
    mock_proveedor = MagicMock(spec=Proveedor)
    mock_proveedor.activo = True
    db_session.get.return_value = mock_proveedor

    db_session.query.return_value.filter.return_value.all.return_value = []

    # Act & Assert
    with pytest.raises(ValueError, match="Producto\(s\) no ofertados por el proveedor"):
        service.crear(proveedor_id, items)


def test_obtener_orden_compra():
    # Arrange
    db_session = MagicMock()
    service = OrdenCompraService(db_session)

    oc_id = uuid.uuid4()
    mock_oc = MagicMock(spec=OrdenCompra)
    mock_oc.id = oc_id
    db_session.get.return_value = mock_oc

    # Act
    result = service.obtener(oc_id)

    # Assert
    assert result is not None
    assert result.id == oc_id
    db_session.get.assert_called_once_with(OrdenCompra, oc_id)


def test_listar_ordenes_compra():
    # Arrange
    db_session = MagicMock()
    service = OrdenCompraService(db_session)

    db_session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        MagicMock(spec=OrdenCompra),
        MagicMock(spec=OrdenCompra),
    ]

    # Act
    result = service.listar(None, None, None)

    # Assert
    assert len(result) == 2


def test_marcar_enviada():
    # Arrange
    db_session = MagicMock()
    service = OrdenCompraService(db_session)

    oc_id = uuid.uuid4()
    oc = MagicMock()
    oc.estado = "ABIERTA"
    service._ensure = MagicMock(return_value=oc)

    # Act
    result = service.marcar_enviada(oc_id)

    # Assert
    assert result.estado == "ENVIADA"


def test_marcar_completa():
    # Arrange
    db_session = MagicMock()
    service = OrdenCompraService(db_session)

    oc_id = uuid.uuid4()
    oc = MagicMock()
    service._ensure = MagicMock(return_value=oc)

    # Act
    result = service.marcar_completa(oc_id)

    # Assert
    assert result.estado == "COMPLETA"


def test_cancelar_orden_compra():
    # Arrange
    db_session = MagicMock()
    service = OrdenCompraService(db_session)

    oc_id = uuid.uuid4()
    oc = MagicMock()
    oc.estado = "ABIERTA"
    service._ensure = MagicMock(return_value=oc)

    # Act
    result = service.cancelar(oc_id)

    # Assert
    assert result.estado == "CANCELADA"


def test_eliminar_orden_compra():
    # Arrange
    db_session = MagicMock()
    service = OrdenCompraService(db_session)

    oc_id = uuid.uuid4()
    oc = MagicMock()
    service._ensure = MagicMock(return_value=oc)

    # Act
    service.eliminar(oc_id)

    # Assert
    db_session.delete.assert_called_once_with(oc)
    db_session.commit.assert_called_once()
