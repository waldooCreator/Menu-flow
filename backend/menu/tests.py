import json
import threading
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.db import connections
from django.test import SimpleTestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from configuracion.models import Parametro
from estaciones.models import Comanda, Estacion
from pedidos.firma import firmar_pedido
from pedidos.models import DetallePedido, Mesa, Pedido
from pedidos.novedades import NovedadInvalida, agregar_item
from ventas.models import Caja, Cuenta
from ventas.operaciones import cerrar_cuenta

from . import promociones as promo
from .models import Categoria, ComponentePromocion, Plato


class DisponibilidadPlatoTests(TransactionTestCase):
    """SPEC-017: disponibilidad, permisos y revalidación del pedido."""

    def setUp(self):
        cocina_grupo = Group.objects.get_or_create(name="cocina")[0]
        mesero_grupo = Group.objects.get_or_create(name="mesero")[0]
        self.cocina = User.objects.create_user("cocina_disponibilidad", password="x")
        self.cocina.groups.add(cocina_grupo)
        self.otro_cocina = User.objects.create_user("otra_cocina_disponibilidad", password="x")
        self.otro_cocina.groups.add(cocina_grupo)
        self.mesero = User.objects.create_user("mesero_disponibilidad", password="x")
        self.mesero.groups.add(mesero_grupo)
        self.admin = User.objects.create_user(
            "admin_disponibilidad", password="x", is_staff=True,
        )

        estacion = Estacion.objects.create(nombre="Cocina disponibilidad", por_defecto=True)
        categoria = Categoria.objects.create(
            nombre="Platos disponibilidad", estacion=estacion,
        )
        self.plato = Plato.objects.create(
            categoria=categoria, nombre="Plato disponible", precio=10000,
        )
        self.otro_plato = Plato.objects.create(
            categoria=categoria, nombre="Otro plato", precio=12000,
        )
        self.mesa = Mesa.objects.create(codigo="M-DISPONIBLE", nombre="Mesa disponibilidad")

    def cliente(self, usuario=None):
        cliente = APIClient()
        if usuario:
            cliente.force_authenticate(usuario)
        return cliente

    def texto_qr(self, plato_ids):
        return firmar_pedido(
            self.mesa.codigo,
            "Cliente disponibilidad",
            [{"plato_id": plato_id, "cantidad": 1, "observacion": ""}
             for plato_id in plato_ids],
        )

    def test_cocina_puede_agotar_reactivar_y_queda_auditoria(self):
        cliente = self.cliente(self.cocina)

        agotado = cliente.post(
            f"/api/platos/{self.plato.id}/disponibilidad/",
            {"disponible": False}, format="json",
        )
        self.assertEqual(agotado.status_code, 200)
        self.plato.refresh_from_db()
        self.assertFalse(self.plato.disponible)
        self.assertEqual(self.plato.disponible_cambiado_por, self.cocina)
        self.assertIsNotNone(self.plato.disponible_cambiado_en)

        reactivado = cliente.post(
            f"/api/platos/{self.plato.id}/disponibilidad/",
            {"disponible": True}, format="json",
        )
        self.assertEqual(reactivado.status_code, 200)
        self.plato.refresh_from_db()
        self.assertTrue(self.plato.disponible)
        self.assertEqual(reactivado.json()["disponible_cambiado_por"], self.cocina.username)

    def test_endpoint_no_expone_nombre_ni_precio(self):
        respuesta = self.cliente(self.cocina).post(
            f"/api/platos/{self.plato.id}/disponibilidad/",
            {"disponible": False, "nombre": "Alterado", "precio": 1}, format="json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.plato.refresh_from_db()
        self.assertEqual(self.plato.nombre, "Plato disponible")
        self.assertEqual(self.plato.precio, 10000)

    def test_mesero_y_anonimo_no_pueden_agotar(self):
        mesero = self.cliente(self.mesero).post(
            f"/api/platos/{self.plato.id}/disponibilidad/",
            {"disponible": False}, format="json",
        )
        anonimo = self.cliente().post(
            f"/api/platos/{self.plato.id}/disponibilidad/",
            {"disponible": False}, format="json",
        )
        self.assertIn(mesero.status_code, (401, 403))
        self.assertIn(anonimo.status_code, (401, 403))

    def test_administrador_tambien_puede_cambiar_disponibilidad(self):
        respuesta = self.cliente(self.admin).post(
            f"/api/platos/{self.plato.id}/disponibilidad/",
            {"disponible": False}, format="json",
        )
        self.assertEqual(respuesta.status_code, 200)

    def test_firmar_un_plato_agotado_se_rechaza(self):
        self.plato.disponible = False
        self.plato.save(update_fields=["disponible"])
        respuesta = self.cliente().post(
            "/api/pedidos/firmar/",
            {"mesa": self.mesa.codigo, "items": [{"plato_id": self.plato.id, "cantidad": 1}]},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Plato disponible", respuesta.json()["detalle"])

    def test_qr_firmado_antes_del_agotado_se_revalida_y_no_crea_nada(self):
        texto = self.texto_qr([self.plato.id])
        self.plato.disponible = False
        self.plato.save(update_fields=["disponible"])

        respuesta = self.cliente(self.mesero).post(
            "/api/pedidos/confirmar/", {"texto": texto}, format="json",
        )
        self.assertEqual(respuesta.status_code, 409)
        self.assertIn("Plato disponible", respuesta.json()["detalle"])
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertEqual(Cuenta.objects.count(), 0)

    def test_si_uno_de_dos_se_agota_se_rechaza_el_pedido_completo(self):
        texto = self.texto_qr([self.plato.id, self.otro_plato.id])
        self.otro_plato.disponible = False
        self.otro_plato.save(update_fields=["disponible"])

        respuesta = self.cliente(self.mesero).post(
            "/api/pedidos/confirmar/", {"texto": texto}, format="json",
        )
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertEqual(Cuenta.objects.count(), 0)

    def test_pedido_confirmado_no_se_toca_si_despues_se_agota(self):
        respuesta = self.cliente(self.mesero).post(
            "/api/pedidos/confirmar/",
            {"texto": self.texto_qr([self.plato.id])}, format="json",
        )
        self.assertEqual(respuesta.status_code, 201)
        pedido_id = respuesta.json()["pedido_id"]

        self.plato.disponible = False
        self.plato.save(update_fields=["disponible"])
        pedido = Pedido.objects.get(pk=pedido_id)
        self.assertEqual(pedido.estado, Pedido.PENDIENTE)
        self.assertEqual(pedido.detalles.count(), 1)

    def test_dos_cocineros_cambiando_a_la_vez_no_rompen_el_plato(self):
        barrera = threading.Barrier(2)
        resultados = []

        def cambiar(usuario, disponible):
            try:
                barrera.wait()
                respuesta = self.cliente(usuario).post(
                    f"/api/platos/{self.plato.id}/disponibilidad/",
                    {"disponible": disponible}, format="json",
                )
                resultados.append(respuesta.status_code)
            finally:
                connections.close_all()

        hilos = [
            threading.Thread(target=cambiar, args=(self.cocina, False)),
            threading.Thread(target=cambiar, args=(self.otro_cocina, True)),
        ]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        self.assertEqual(sorted(resultados), [200, 200])
        self.plato.refresh_from_db()
        self.assertIsNotNone(self.plato.disponible_cambiado_por_id)
        self.assertIsNotNone(self.plato.disponible_cambiado_en)


# ============================================================================
# SPEC-023 — Promociones
# ============================================================================

ZONA = ZoneInfo(settings.TIME_ZONE)


def a_las(anio, mes, dia, hora, minuto=0):
    return datetime(anio, mes, dia, hora, minuto, tzinfo=ZONA)


class VigenciaPromocion(SimpleTestCase):
    """
    La regla de vigencia, sin base de datos y con la hora fijada: probarla
    contra el reloj real haría que las pruebas pasaran o fallaran según la
    hora a la que se corran.

    El 2026-09-18 es viernes.
    """

    def promo(self, **campos):
        base = dict(tipo=Plato.PROMOCION, nombre="Combo", precio=50000, activa=True,
                    disponible=True, vigente_desde=datetime(2026, 9, 1).date(),
                    vigente_hasta=None, dias_semana=list(range(7)),
                    hora_inicio=None, hora_fin=None)
        base.update(campos)
        return Plato(**base)

    def test_un_plato_normal_no_tiene_estado_de_promocion(self):
        self.assertIsNone(promo.estado_promocion(Plato(tipo=Plato.PLATO), a_las(2026, 9, 18, 12)))

    def test_con_inicio_manana_no_aparece_hoy(self):
        p = self.promo(vigente_desde=datetime(2026, 9, 19).date())
        self.assertEqual(promo.estado_promocion(p, a_las(2026, 9, 18, 12)), promo.PROGRAMADA)

    def test_que_termino_ayer_no_aparece_hoy(self):
        p = self.promo(vigente_hasta=datetime(2026, 9, 17).date())
        self.assertEqual(promo.estado_promocion(p, a_las(2026, 9, 18, 12)), promo.VENCIDA)

    def test_el_ultimo_dia_todavia_vale(self):
        p = self.promo(vigente_hasta=datetime(2026, 9, 18).date())
        self.assertEqual(promo.estado_promocion(p, a_las(2026, 9, 18, 23, 59)), promo.VIGENTE)

    def test_sin_fecha_de_fin_sigue_vigente(self):
        self.assertEqual(promo.estado_promocion(self.promo(), a_las(2030, 1, 1, 12)), promo.VIGENTE)

    def test_de_lunes_a_jueves_no_aparece_un_viernes(self):
        p = self.promo(dias_semana=[0, 1, 2, 3])
        self.assertEqual(promo.estado_promocion(p, a_las(2026, 9, 18, 12)), promo.FUERA_DE_HORARIO)
        self.assertEqual(promo.estado_promocion(p, a_las(2026, 9, 17, 12)), promo.VIGENTE)

    def test_franja_de_12_a_15(self):
        p = self.promo(hora_inicio=time(12), hora_fin=time(15))
        self.assertEqual(promo.estado_promocion(p, a_las(2026, 9, 18, 14, 59)), promo.VIGENTE)
        self.assertEqual(promo.estado_promocion(p, a_las(2026, 9, 18, 15, 1)), promo.FUERA_DE_HORARIO)
        self.assertEqual(promo.estado_promocion(p, a_las(2026, 9, 18, 11, 59)), promo.FUERA_DE_HORARIO)

    def test_franja_que_cruza_medianoche_pertenece_al_dia_en_que_empezo(self):
        solo_viernes = self.promo(dias_semana=[4], hora_inicio=time(20), hora_fin=time(2))
        # Sábado 01:00: todavía es la noche del viernes.
        self.assertEqual(promo.estado_promocion(solo_viernes, a_las(2026, 9, 19, 1)), promo.VIGENTE)
        # Viernes 01:00: es la noche del jueves, que no está marcado.
        self.assertEqual(
            promo.estado_promocion(solo_viernes, a_las(2026, 9, 18, 1)), promo.FUERA_DE_HORARIO)
        self.assertEqual(promo.estado_promocion(solo_viernes, a_las(2026, 9, 18, 21)), promo.VIGENTE)
        self.assertEqual(
            promo.estado_promocion(solo_viernes, a_las(2026, 9, 19, 3)), promo.FUERA_DE_HORARIO)

    def test_la_madrugada_del_ultimo_dia_todavia_vale(self):
        p = self.promo(vigente_hasta=datetime(2026, 9, 18).date(),
                       hora_inicio=time(20), hora_fin=time(2))
        self.assertEqual(promo.estado_promocion(p, a_las(2026, 9, 19, 1)), promo.VIGENTE)
        self.assertEqual(promo.estado_promocion(p, a_las(2026, 9, 19, 21)), promo.VENCIDA)

    def test_apagada_aunque_este_en_fechas(self):
        p = self.promo(activa=False)
        self.assertEqual(promo.estado_promocion(p, a_las(2026, 9, 18, 12)), promo.APAGADA)

    def test_agotada_se_distingue_de_vigente(self):
        p = self.promo(disponible=False)
        self.assertEqual(promo.estado_promocion(p, a_las(2026, 9, 18, 12)), promo.AGOTADA)
        self.assertFalse(promo.se_puede_vender(p, a_las(2026, 9, 18, 12)))


class BasePromociones(TransactionTestCase):
    def setUp(self):
        # La configuración se cachea en memoria de proceso, y vaciar la base
        # entre pruebas no dispara la señal que la invalida.
        cache.clear()
        self.addCleanup(cache.clear)

        self.admin = User.objects.create_user("admin_promo", password="x", is_staff=True)
        self.mesero = User.objects.create_user("mesero_promo", password="x")
        self.mesero.groups.add(Group.objects.get_or_create(name="mesero")[0])

        self.cocina = Estacion.objects.create(nombre="Cocina", por_defecto=True)
        self.bar = Estacion.objects.create(nombre="Bar", orden=1)
        self.cat_bebidas = Categoria.objects.create(nombre="Bebidas", estacion=self.bar)
        self.jugo = Plato.objects.create(categoria=self.cat_bebidas, nombre="Jugo", precio=5000)
        self.mesa = Mesa.objects.create(codigo="M-PROMO", nombre="Mesa promo")
        self.caja = Caja.objects.create(nombre="Efectivo")

        self.hoy = timezone.localdate()
        self.combo = self.crear_promo("Combo Parrillero", 50000)

    def crear_promo(self, nombre, precio, **campos):
        datos = dict(tipo=Plato.PROMOCION, nombre=nombre, precio=precio,
                     vigente_desde=self.hoy - timedelta(days=1))
        datos.update(campos)
        p = Plato.objects.create(**datos)
        ComponentePromocion.objects.create(promocion=p, orden=0, cantidad=2, nombre="Hamburguesa clásica",
                                           especificacion="Pan brioche, carne 150 g, cheddar")
        ComponentePromocion.objects.create(promocion=p, orden=1, cantidad=1, nombre="Gaseosa 400 ml")
        return p

    def api(self, usuario=None):
        c = APIClient()
        if usuario:
            c.force_authenticate(usuario)
        return c

    def confirmar(self, items):
        # Un nombre distinto por pedido: dos QR idénticos firmados en el mismo
        # segundo son el mismo texto, y el segundo se rechaza como duplicado.
        self.pedidos_hechos = getattr(self, "pedidos_hechos", 0) + 1
        texto = firmar_pedido(self.mesa.codigo, f"Cliente {self.pedidos_hechos}",
                              [{"plato_id": p.id, "cantidad": c, "observacion": ""} for p, c in items])
        return self.api(self.mesero).post("/api/pedidos/confirmar/", {"texto": texto}, format="json")

    def platos_publicos(self, usuario=None, **params):
        r = self.api(usuario).get("/api/platos/", {"page_size": 200, **params})
        return {p["id"]: p for p in r.json()["results"]}


class PromocionesMenuYPanel(BasePromociones):
    def test_el_menu_publico_solo_trae_promos_vigentes_o_agotadas(self):
        programada = self.crear_promo("Programada", 1000, vigente_desde=self.hoy + timedelta(days=3))
        vencida = self.crear_promo("Vencida", 1000, vigente_desde=self.hoy - timedelta(days=9),
                                   vigente_hasta=self.hoy - timedelta(days=1))
        apagada = self.crear_promo("Apagada", 1000, activa=False)
        agotada = self.crear_promo("Agotada", 1000, disponible=False)

        visibles = self.platos_publicos()
        self.assertIn(self.combo.id, visibles)
        self.assertIn(agotada.id, visibles)
        self.assertIn(self.jugo.id, visibles)
        for oculta in (programada, vencida, apagada):
            self.assertNotIn(oculta.id, visibles)

        combo = visibles[self.combo.id]
        self.assertEqual(combo["tipo"], "promocion")
        self.assertIsNone(combo["categoria_id"])
        self.assertEqual(combo["estado_promocion"], "vigente")
        self.assertEqual([c["nombre"] for c in combo["componentes"]],
                         ["Hamburguesa clásica", "Gaseosa 400 ml"])
        self.assertEqual(combo["componentes"][0]["especificacion"], "Pan brioche, carne 150 g, cheddar")

    def test_el_panel_ve_todas_pero_todas_1_no_sirve_sin_ser_admin(self):
        programada = self.crear_promo("Programada", 1000, vigente_desde=self.hoy + timedelta(days=3))
        self.assertIn(programada.id, self.platos_publicos(self.admin, todas=1))
        self.assertNotIn(programada.id, self.platos_publicos(self.mesero, todas=1))
        self.assertNotIn(programada.id, self.platos_publicos(None, todas=1))

    def datos_promo(self, **cambios):
        datos = {
            "tipo": "promocion", "nombre": "Combo Familiar", "precio": 80000,
            "vigente_desde": self.hoy.isoformat(), "dias_semana": [4, 5, 6],
            "hora_inicio": "12:00", "hora_fin": "15:00",
            "componentes": [
                {"cantidad": 4, "nombre": "Perro caliente", "especificacion": "Salchicha americana"},
                {"cantidad": 1, "nombre": "Gaseosa 1.5 L"},
            ],
        }
        datos.update(cambios)
        return datos

    def test_el_admin_crea_una_promocion_con_componentes(self):
        r = self.api(self.admin).post("/api/platos/", self.datos_promo(), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        p = Plato.objects.get(pk=r.json()["id"])
        self.assertTrue(p.es_promocion)
        self.assertIsNone(p.categoria)
        self.assertEqual(p.dias_semana, [4, 5, 6])
        self.assertEqual([(c.cantidad, c.nombre) for c in p.componentes.all()],
                         [(4, "Perro caliente"), (1, "Gaseosa 1.5 L")])

    def test_componentes_como_texto_json_para_el_formulario_con_foto(self):
        datos = self.datos_promo()
        datos["componentes"] = json.dumps(datos["componentes"])
        datos["dias_semana"] = json.dumps(datos["dias_semana"])
        r = self.api(self.admin).post("/api/platos/", datos, format="multipart")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Plato.objects.get(pk=r.json()["id"]).componentes.count(), 2)

    def test_una_promocion_sin_componentes_no_se_guarda(self):
        r = self.api(self.admin).post("/api/platos/", self.datos_promo(componentes=[]), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("componentes", r.json())

    def test_editar_reemplaza_los_componentes_en_el_orden_recibido(self):
        r = self.api(self.admin).patch(f"/api/platos/{self.combo.id}/", {"componentes": [
            {"cantidad": 1, "nombre": "Gaseosa 400 ml"},
            {"cantidad": 3, "nombre": "Hamburguesa clásica"},
        ]}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual([c.nombre for c in self.combo.componentes.all()],
                         ["Gaseosa 400 ml", "Hamburguesa clásica"])

    def test_franja_a_medias_y_fechas_al_reves_se_rechazan(self):
        r = self.api(self.admin).post("/api/platos/", self.datos_promo(hora_fin=None), format="json")
        self.assertEqual(r.status_code, 400)
        r = self.api(self.admin).post("/api/platos/", self.datos_promo(
            vigente_hasta=(self.hoy - timedelta(days=1)).isoformat()), format="json")
        self.assertEqual(r.status_code, 400)

    def test_un_plato_normal_sigue_exigiendo_categoria(self):
        r = self.api(self.admin).post("/api/platos/", {"nombre": "Suelto", "precio": 1000}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_solo_el_admin_crea_promociones(self):
        r = self.api(self.mesero).post("/api/platos/", self.datos_promo(), format="json")
        self.assertEqual(r.status_code, 403)

    def test_una_promo_vendida_no_se_puede_borrar(self):
        self.assertEqual(self.confirmar([(self.combo, 1)]).status_code, 201)
        r = self.api(self.admin).delete(f"/api/platos/{self.combo.id}/")
        self.assertEqual(r.status_code, 409)
        self.assertIn("apágala", r.json()["detalle"])
        self.assertTrue(Plato.objects.filter(pk=self.combo.id).exists())


class PromocionesVentaYCocina(BasePromociones):
    def test_confirmar_congela_el_desglose_y_cocina_lo_ve(self):
        r = self.confirmar([(self.combo, 2)])
        self.assertEqual(r.status_code, 201, r.content)
        detalle = DetallePedido.objects.get(pedido_id=r.json()["pedido_id"])
        self.assertEqual(detalle.precio_congelado, 50000)
        self.assertEqual(detalle.desglose_congelado, [[2, "Hamburguesa clásica"], [1, "Gaseosa 400 ml"]])

        cocinero = User.objects.create_user("cocina_tablero", password="x")
        cocinero.groups.add(Group.objects.get_or_create(name="cocina")[0])
        tarjetas = self.api(cocinero).get("/api/comandas/").json()
        tarjetas = tarjetas["results"] if isinstance(tarjetas, dict) else tarjetas
        renglon = tarjetas[0]["detalles"][0]
        self.assertEqual(renglon["nombre"], "Combo Parrillero")
        self.assertEqual(renglon["desglose"], [[2, "Hamburguesa clásica"], [1, "Gaseosa 400 ml"]])

    def test_cambiar_la_promo_despues_no_altera_el_pedido(self):
        r = self.confirmar([(self.combo, 1)])
        self.combo.componentes.filter(nombre="Gaseosa 400 ml").update(nombre="Jugo natural")
        self.combo.precio = 99000
        self.combo.nombre = "Combo renombrado"
        self.combo.save()
        detalle = DetallePedido.objects.get(pedido_id=r.json()["pedido_id"])
        self.assertEqual(detalle.desglose_congelado[1], [1, "Gaseosa 400 ml"])
        self.assertEqual((detalle.nombre_congelado, detalle.precio_congelado), ("Combo Parrillero", 50000))

    def test_la_promo_va_entera_a_la_estacion_por_defecto_aunque_haya_bar(self):
        r = self.confirmar([(self.combo, 1), (self.jugo, 1)])
        pedido = Pedido.objects.get(pk=r.json()["pedido_id"])
        por_plato = {d.plato_id: d.comanda.estacion for d in pedido.detalles.select_related("comanda")}
        self.assertEqual(por_plato[self.combo.id], self.cocina)
        self.assertEqual(por_plato[self.jugo.id], self.bar)

    def test_estaciones_unificadas_mandan_todo_a_la_de_por_defecto_y_se_puede_volver(self):
        parametro = Parametro.objects.create(
            clave="estaciones-unificadas", etiqueta="Unificar", tipo=Parametro.BOOLEANO, valor="si")
        r = self.confirmar([(self.jugo, 1)])
        self.assertEqual(Comanda.objects.get(pedido_id=r.json()["pedido_id"]).estacion, self.cocina)

        parametro.valor = "no"
        parametro.save()
        r = self.confirmar([(self.jugo, 1)])
        self.assertEqual(Comanda.objects.get(pedido_id=r.json()["pedido_id"]).estacion, self.bar)

    def test_confirmar_una_promo_que_dejo_de_estar_vigente_se_rechaza_nombrandola(self):
        texto = firmar_pedido(self.mesa.codigo, "Cliente",
                              [{"plato_id": self.combo.id, "cantidad": 1, "observacion": ""}])
        # Entre que el cliente generó el QR y el mesero lo lee, la promo venció.
        Plato.objects.filter(pk=self.combo.pk).update(
            vigente_desde=self.hoy - timedelta(days=5), vigente_hasta=self.hoy - timedelta(days=1))
        r = self.api(self.mesero).post("/api/pedidos/confirmar/", {"texto": texto}, format="json")
        self.assertEqual(r.status_code, 409)
        self.assertIn("Combo Parrillero", r.json()["detalle"])
        self.assertFalse(Pedido.objects.exists())

    def test_verificar_marca_la_promo_vencida_como_no_disponible(self):
        texto = firmar_pedido(self.mesa.codigo, "Cliente",
                              [{"plato_id": self.combo.id, "cantidad": 1, "observacion": ""}])
        Plato.objects.filter(pk=self.combo.pk).update(activa=False)
        item = self.api().post("/api/pedidos/verificar/", {"texto": texto}, format="json").json()["items"][0]
        self.assertFalse(item["disponible"])
        self.assertTrue(item["es_promocion"])

    def test_el_cliente_no_puede_firmar_una_promo_fuera_de_horario(self):
        Plato.objects.filter(pk=self.combo.pk).update(vigente_desde=self.hoy + timedelta(days=2))
        r = self.api().post("/api/pedidos/firmar/", {
            "mesa": self.mesa.codigo,
            "items": [{"plato_id": self.combo.id, "cantidad": 1, "observacion": ""}],
        }, format="json")
        self.assertEqual(r.status_code, 400)

    def test_agregar_a_un_pedido_en_curso_congela_y_valida_vigencia(self):
        pedido = Pedido.objects.get(pk=self.confirmar([(self.jugo, 1)]).json()["pedido_id"])
        agregar_item(pedido, self.mesero, self.combo.id, 1)
        detalle = pedido.detalles.get(plato=self.combo)
        self.assertEqual(len(detalle.desglose_congelado), 2)

        Plato.objects.filter(pk=self.combo.pk).update(activa=False)
        with self.assertRaises(NovedadInvalida):
            agregar_item(pedido, self.mesero, self.combo.id, 1)


class PromocionesReportes(BasePromociones):
    def vender(self, items, cuando=None):
        pedido = Pedido.objects.get(pk=self.confirmar(items).json()["pedido_id"])
        cerrar_cuenta(pedido.cuenta, self.admin, self.caja.id)
        if cuando:
            Cuenta.objects.filter(pk=pedido.cuenta_id).update(cerrada_en=cuando)
        return pedido

    def reporte(self, **params):
        r = self.api(self.admin).get("/api/reportes/producto/", params)
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_veinte_combos_son_veinte_unidades_del_combo(self):
        self.vender([(self.combo, 20)])
        datos = self.reporte(plato=self.combo.id)
        self.assertEqual((datos["unidades"], datos["ingresos"]), (20, 1_000_000))

        # Y no le suman nada a un plato que se llama como un componente.
        hamburguesa = Plato.objects.create(
            categoria=self.cat_bebidas, nombre="Hamburguesa clásica", precio=20000)
        self.assertEqual(self.reporte(plato=hamburguesa.id)["unidades"], 0)

    def test_el_filtro_funciona_con_un_plato_normal(self):
        self.vender([(self.jugo, 3)])
        self.assertEqual(self.reporte(plato=self.jugo.id)["unidades"], 3)

    def test_agrupado_por_dia_semana_y_mes_cuadra_con_el_total(self):
        base = timezone.make_aware(datetime(2026, 8, 3, 13), ZONA)  # lunes
        for dias, cantidad in [(0, 2), (1, 1), (8, 4), (30, 5)]:
            self.vender([(self.combo, cantidad)], cuando=base + timedelta(days=dias))
        rango = {"plato": self.combo.id, "desde": "2026-08-01", "hasta": "2026-09-30"}

        for agrupar in ("dia", "semana", "mes"):
            datos = self.reporte(agrupar=agrupar, **rango)
            self.assertEqual(datos["unidades"], 12)
            self.assertEqual(sum(p["unidades"] for p in datos["periodos"]), 12, agrupar)
            self.assertEqual(sum(p["ingresos"] for p in datos["periodos"]), datos["ingresos"], agrupar)

        semanas = self.reporte(agrupar="semana", **rango)["periodos"]
        primera = next(p for p in semanas if p["inicio"] == "2026-08-03")
        self.assertEqual(primera["unidades"], 3)
        meses = {p["inicio"]: p["unidades"] for p in self.reporte(agrupar="mes", **rango)["periodos"]}
        self.assertEqual(meses, {"2026-08-01": 7, "2026-09-01": 5})

    def test_los_pedidos_anulados_no_cuentan(self):
        pedido = self.vender([(self.combo, 2)])
        Pedido.objects.filter(pk=pedido.pk).update(estado=Pedido.ANULADO)
        self.assertEqual(self.reporte(plato=self.combo.id)["unidades"], 0)

    def test_una_promo_renombrada_sigue_sumando_sus_ventas(self):
        self.vender([(self.combo, 2)])
        self.combo.nombre = "Combo Parrillero XL"
        self.combo.save()
        self.vender([(self.combo, 1)])
        datos = self.reporte(plato=self.combo.id)
        self.assertEqual(datos["unidades"], 3)
        self.assertEqual(datos["plato"]["nombre"], "Combo Parrillero XL")

    def test_solo_promociones_deja_el_ranking_con_combos(self):
        self.vender([(self.combo, 1), (self.jugo, 9)])
        todos = self.api(self.admin).get("/api/reportes/").json()
        self.assertEqual({p["nombre"] for p in todos["productos"]}, {"Combo Parrillero", "Jugo"})
        solo = self.api(self.admin).get("/api/reportes/", {"solo_promociones": 1}).json()
        self.assertEqual([p["nombre"] for p in solo["productos"]], ["Combo Parrillero"])
        self.assertIn(self.combo.id, {p["id"] for p in solo["catalogo"]})

    def test_quien_no_puede_cobrar_no_ve_el_reporte(self):
        cocinero = User.objects.create_user("cocina_promo", password="x")
        cocinero.groups.add(Group.objects.get_or_create(name="cocina")[0])
        r = self.api(cocinero).get("/api/reportes/producto/", {"plato": self.combo.id})
        self.assertEqual(r.status_code, 403)
