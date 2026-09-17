"""
Enrutador central de la API. Todo lo que consume Vue vive bajo /api/.
"""

from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from configuracion.views import ConfiguracionPublicaView, ParametroViewSet
from nucleo.usuarios import UsuarioViewSet
from pedidos.admin_mesas import MesaAdminViewSet
from clientes.views import ClienteViewSet
from ventas.views import (
    ActivosView,
    AjustarSaldoView,
    AnularCuentaView,
    CategoriaGastoViewSet,
    CerrarCuentaView,
    SaldoInicialView,
    CuentasView,
    DetalleCuentaView,
    ExportarVentasView,
    ConsolidadoVentasView,
    AbrirTurnoView,
    CajaViewSet,
    CerrarTurnoView,
    MovimientosView,
    TrasladarView,
    ReporteProductoView,
    ReportesView,
    TurnoActualView,
    VentasView,
    TurnosView,
    TiqueteVentaView,
    TiquetesSeleccionadosView,
)
from nucleo.vistas import PerfilView
from estaciones.views import ComandaViewSet, EstacionViewSet
from menu.views import (
    CategoriaViewSet,
    DisponibilidadPlatoView,
    EtiquetaViewSet,
    ObservacionRapidaViewSet,
    PlatoViewSet,
)
from pedidos.views import (
    AgregarItemView,
    CambiarCantidadView,
    CambiarDestinoView,
    CambiarEstadoMesaView,
    CambiarObservacionView,
    EditarPedidoLoteView,
    ConfirmarPedidoView,
    EntregarPedidoView,
    FirmarPedidoView,
    ListarMesasView,
    MarcarNotificacionLeidaView,
    NotificacionesView,
    PedidosActivosView,
    QuitarItemView,
    SalonView,
    ValidarMesaView,
    VerificarPedidoView,
)

router = DefaultRouter()
router.register("configuracion", ParametroViewSet, basename="parametro")
router.register("categorias", CategoriaViewSet, basename="categoria")
router.register("platos", PlatoViewSet, basename="plato")
router.register("etiquetas", EtiquetaViewSet, basename="etiqueta")
router.register("observaciones-rapidas", ObservacionRapidaViewSet, basename="observacionrapida")
router.register("estaciones", EstacionViewSet, basename="estacion")
# Administración (solo admin): mesas y usuarios desde el panel (SPEC-001/007)
router.register("mesas-admin", MesaAdminViewSet, basename="mesa-admin")
router.register("usuarios", UsuarioViewSet, basename="usuario")
router.register("cajas", CajaViewSet, basename="caja")
# En que se va la plata (SPEC-020): la lee quien registra gastos, la
# modifica solo el administrador.
router.register("categorias-gasto", CategoriaGastoViewSet, basename="categoriagasto")
# Clientes (SPEC-019): CRUD completo, incluido borrar por Ley 1581.
router.register("clientes", ClienteViewSet, basename="cliente")
router.register("comandas", ComandaViewSet, basename="comanda")

urlpatterns = [
    path("configuracion/publica/", ConfiguracionPublicaView.as_view(), name="configuracion-publica"),
    path("auth/login/", obtain_auth_token, name="api-login"),
    path("auth/perfil/", PerfilView.as_view(), name="api-perfil"),
    path("mesas/", ListarMesasView.as_view(), name="mesa-listar"),
    path("mesas/salon/", SalonView.as_view(), name="mesa-salon"),
    path("mesas/<str:codigo>/estado/", CambiarEstadoMesaView.as_view(), name="mesa-estado"),
    path("mesas/validar/<str:codigo>/", ValidarMesaView.as_view(), name="mesa-validar"),
    path("pedidos/", PedidosActivosView.as_view(), name="pedido-activos"),
    # La cuenta (SPEC-013)
    # Historial de ventas (SPEC-015): las cuentas que se cobraron, con
    # filtros y totales. Nada que ver con la DIAN — es el historial interno.
    path("ventas/", VentasView.as_view(), name="venta-listar"),
    # Los cuatro reportes de venta (SPEC-018), en una sola llamada.
    path("reportes/", ReportesView.as_view(), name="reportes"),
    # Un producto, plato o promocion, por dia, semana o mes (SPEC-023).
    path("reportes/producto/", ReporteProductoView.as_view(), name="reporte-producto"),
    path("ventas/consolidado/", ConsolidadoVentasView.as_view(), name="venta-consolidado"),
    path("ventas/exportar/", ExportarVentasView.as_view(), name="venta-exportar"),
    path("ventas/tiquetes/", TiquetesSeleccionadosView.as_view(), name="venta-tiquetes"),
    path("ventas/<int:pk>/tiquete/", TiqueteVentaView.as_view(), name="venta-tiquete"),
    path("cuentas/", CuentasView.as_view(), name="cuenta-listar"),
    path("cuentas/<int:pk>/", DetalleCuentaView.as_view(), name="cuenta-detalle"),
    path("cuentas/<int:pk>/cerrar/", CerrarCuentaView.as_view(), name="cuenta-cerrar"),
    path("cuentas/<int:pk>/anular/", AnularCuentaView.as_view(), name="cuenta-anular"),
    # Turno de caja y libro de movimientos (SPEC-014)
    path("turnos/", TurnosView.as_view(), name="turno-listar"),
    path("turnos/actual/", TurnoActualView.as_view(), name="turno-actual"),
    path("turnos/abrir/", AbrirTurnoView.as_view(), name="turno-abrir"),
    path("turnos/<int:pk>/cerrar/", CerrarTurnoView.as_view(), name="turno-cerrar"),
    path("movimientos/", MovimientosView.as_view(), name="movimiento-listar"),
    path("cajas/trasladar/", TrasladarView.as_view(), name="caja-trasladar"),
    # Activos liquidos (SPEC-020): cuanta plata hay ahora y donde.
    path("activos/", ActivosView.as_view(), name="activos"),
    path("cajas/<int:pk>/saldo-inicial/", SaldoInicialView.as_view(), name="caja-saldo-inicial"),
    path("cajas/<int:pk>/ajustar/", AjustarSaldoView.as_view(), name="caja-ajustar"),
    path("pedidos/firmar/", FirmarPedidoView.as_view(), name="pedido-firmar"),
    path("platos/<int:pk>/disponibilidad/", DisponibilidadPlatoView.as_view(), name="plato-disponibilidad"),
    path("pedidos/verificar/", VerificarPedidoView.as_view(), name="pedido-verificar"),
    path("pedidos/confirmar/", ConfirmarPedidoView.as_view(), name="pedido-confirmar"),
    path("pedidos/notificaciones/", NotificacionesView.as_view(), name="pedido-notificaciones"),
    path(
        "pedidos/notificaciones/<int:pk>/leer/",
        MarcarNotificacionLeidaView.as_view(),
        name="notificacion-leer",
    ),
    path("pedidos/<int:pk>/entregar/", EntregarPedidoView.as_view(), name="pedido-entregar"),
    # Novedades sobre un pedido ya enviado (SPEC-011)
    path("pedidos/<int:pk>/destino/", CambiarDestinoView.as_view(), name="pedido-destino"),
    path("pedidos/<int:pk>/items/agregar/", AgregarItemView.as_view(), name="pedido-item-agregar"),
    path("pedidos/<int:pk>/items/quitar/", QuitarItemView.as_view(), name="pedido-item-quitar"),
    path("pedidos/<int:pk>/items/cantidad/", CambiarCantidadView.as_view(), name="pedido-item-cantidad"),
    path("pedidos/<int:pk>/items/observacion/", CambiarObservacionView.as_view(), name="pedido-item-observacion"),
    # Varios cambios en una sola transaccion (el boton "Aplicar cambios")
    path("pedidos/<int:pk>/editar/", EditarPedidoLoteView.as_view(), name="pedido-editar-lote"),
    path("", include(router.urls)),
]
