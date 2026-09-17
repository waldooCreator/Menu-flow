"""
Criterios de aceptación de SPEC-005, SPEC-011, SPEC-012 y SPEC-013.

Nacieron el 2026-09-14 al poner al día la documentación: las apps `pedidos` y
`estaciones` no tenían ni una prueba, y los criterios de esas specs figuraban
sin marcar aunque en su mayoría ya funcionaban. Cada prueba nombra la línea de
la spec que verifica, así que una casilla marcada en la bóveda tiene detrás
algo que se puede correr.

Dos de ellas destaparon fallos reales (el aviso de un domicilio listo y la
comanda tomada dos veces), corregidos el mismo día.
"""

from django.contrib.auth.models import Group, User
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from estaciones.models import Comanda, Estacion
from menu.models import Categoria, Plato
from pedidos.firma import firmar_pedido
from pedidos.models import Mesa, Notificacion, Novedad, Pedido
from pedidos.novedades import (
    NovedadInvalida, agregar_item, cambiar_cantidad, cambiar_destino,
    novedades_sin_ver, quitar_item,
)
from ventas.models import Caja, Cuenta
from ventas.tests import en_paralelo


class Base(TransactionTestCase):
    def setUp(self):
        self.mesero = User.objects.create_user("m1", password="x")
        self.mesero.groups.add(Group.objects.get_or_create(name="mesero")[0])
        self.otro_mesero = User.objects.create_user("m2", password="x")
        self.otro_mesero.groups.add(Group.objects.get_or_create(name="mesero")[0])
        self.cocinero = User.objects.create_user("c1", password="x")
        self.cocinero.groups.add(Group.objects.get_or_create(name="cocina")[0])
        self.cajero = User.objects.create_user("caj", password="x")
        self.cajero.groups.add(Group.objects.get_or_create(name="cajero")[0])

        self.cocina = Estacion.objects.create(nombre="Cocina", por_defecto=True)
        self.bar = Estacion.objects.create(nombre="Bar")
        cat_cocina = Categoria.objects.create(nombre="Platos", estacion=self.cocina)
        cat_bar = Categoria.objects.create(nombre="Bebidas", estacion=self.bar)
        self.arroz = Plato.objects.create(categoria=cat_cocina, nombre="Arroz", precio=10000)
        self.pollo = Plato.objects.create(categoria=cat_cocina, nombre="Pollo", precio=20000)
        self.jugo = Plato.objects.create(categoria=cat_bar, nombre="Jugo", precio=5000)

        self.m1 = Mesa.objects.create(codigo="M1", nombre="Mesa 1")
        self.m2 = Mesa.objects.create(codigo="M2", nombre="Mesa 2")
        self.efectivo = Caja.objects.create(nombre="Efectivo", tipo=Caja.EFECTIVO)
        self._n = 0

    def api(self, usuario):
        c = APIClient()
        c.force_authenticate(usuario)
        return c

    def pedir(self, mesa=None, items=None, domicilio=False, usuario=None, nombre="Cliente",
              costo_envio=None):
        """Confirma un pedido por el camino real: firmar el QR y confirmarlo."""
        self._n += 1
        items = items or [(self.arroz, 1)]
        texto = firmar_pedido(
            mesa.codigo if mesa else "", nombre,
            [{"plato_id": p.id, "cantidad": c, "observacion": f"#{self._n}"} for p, c in items],
            es_domicilio=domicilio,
        )
        cuerpo = {"texto": texto}
        if costo_envio is not None:
            cuerpo["costo_envio"] = costo_envio
        r = self.api(usuario or self.mesero).post("/api/pedidos/confirmar/", cuerpo, format="json")
        assert r.status_code == 201, (r.status_code, r.content)
        return Pedido.objects.get(pk=r.json()["pedido_id"])


class Spec011Novedades(Base):
    def test_L190_domicilio_muestra_Domicilio_en_la_tarjeta_de_cocina(self):
        pedido = self.pedir(domicilio=True)
        r = self.api(self.cocinero).get("/api/comandas/")
        datos = r.json()
        lista = datos["results"] if isinstance(datos, dict) else datos
        tarjeta = next(c for c in lista if c["pedido"] == pedido.id)
        self.assertEqual(tarjeta["destino"], "Domicilio")

    def test_L190b_marcar_lista_un_domicilio_avisa_al_mesero(self):
        """
        Corregido 2026-09-14. El aviso se armaba con `pedido.mesa.nombre`; en
        un domicilio la mesa es nula, la petición respondía 500 y el mesero
        nunca se enteraba de que el domicilio estaba listo.
        """
        pedido = self.pedir(domicilio=True)
        comanda = pedido.comandas.first()
        r = self.api(self.cocinero).post(f"/api/comandas/{comanda.id}/lista/")
        self.assertEqual(r.status_code, 200, r.content[:300])

        aviso = Notificacion.objects.get(comanda=comanda)
        self.assertEqual(aviso.mesero, self.mesero)
        self.assertIn("Domicilio", aviso.mensaje)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.LISTO)

    def test_L191_listar_pedidos_activos_incluye_los_sin_mesa(self):
        pedido = self.pedir(domicilio=True)
        r = self.api(self.mesero).get("/api/pedidos/")
        ids = [p["id"] for p in (r.json()["results"] if isinstance(r.json(), dict) else r.json())]
        self.assertIn(pedido.id, ids)

    def test_L192_L193_mover_de_mesa_ocupa_la_nueva_y_no_libera_la_vieja(self):
        pedido = self.pedir(mesa=self.m1)
        cambiar_destino(pedido, self.mesero, mesa_codigo="M2")
        self.m1.refresh_from_db(); self.m2.refresh_from_db(); pedido.refresh_from_db()
        self.assertEqual(pedido.destino, "Mesa 2")
        self.assertEqual(self.m2.estado, Mesa.OCUPADA)
        self.assertEqual(self.m1.estado, Mesa.OCUPADA, "la mesa vieja no se libera sola")

    def test_L194_pasar_a_domicilio_hace_que_cocina_muestre_Domicilio(self):
        pedido = self.pedir(mesa=self.m1)
        cambiar_destino(pedido, self.mesero, es_domicilio=True)
        pedido.refresh_from_db()
        self.assertEqual(pedido.destino, "Domicilio")

    def test_L195_cada_cambio_deja_una_novedad_con_autor_antes_despues_y_fecha(self):
        pedido = self.pedir(mesa=self.m1)
        cambiar_destino(pedido, self.mesero, mesa_codigo="M2")
        n = Novedad.objects.get(pedido=pedido)
        self.assertEqual(n.autor, self.mesero)
        self.assertEqual((n.antes, n.despues), ("Mesa 1", "Mesa 2"))
        self.assertIsNotNone(n.creada)

    def test_L196_L198_novedad_sin_ver_y_visto_la_apaga_sin_reaparecer(self):
        pedido = self.pedir(mesa=self.m1)
        comanda = pedido.comandas.first()
        cambiar_destino(pedido, self.mesero, mesa_codigo="M2")
        pendientes = novedades_sin_ver(comanda)
        self.assertEqual(pendientes.count(), 1)
        self.assertIn("Mesa 2", pendientes.first().descripcion, "muestra el cambio concreto")
        self.api(self.cocinero).post(f"/api/comandas/{comanda.id}/visto/")
        comanda.refresh_from_db()
        self.assertEqual(novedades_sin_ver(comanda).count(), 0)

    def test_L199_una_comanda_lista_que_recibe_novedad_sale_de_listas(self):
        pedido = self.pedir(mesa=self.m1)
        comanda = pedido.comandas.first()
        comanda.marcar_lista()
        cambiar_destino(pedido, self.mesero, mesa_codigo="M2")
        comanda.refresh_from_db()
        self.assertNotEqual(comanda.estado, Comanda.LISTA)

    def test_L200_agregar_plato_de_otra_categoria_crea_la_comanda_de_esa_estacion(self):
        pedido = self.pedir(mesa=self.m1, items=[(self.arroz, 1)])
        self.assertFalse(pedido.comandas.filter(estacion=self.bar).exists())
        agregar_item(pedido, self.mesero, plato_id=self.jugo.id)
        self.assertTrue(pedido.comandas.filter(estacion=self.bar).exists())

    def test_L201_plato_agregado_congela_el_precio_del_momento(self):
        pedido = self.pedir(mesa=self.m1)
        self.pollo.precio = 25000; self.pollo.save()
        agregar_item(pedido, self.mesero, plato_id=self.pollo.id)
        self.assertEqual(pedido.detalles.get(plato=self.pollo).precio_congelado, 25000)

    def test_L202_cambiar_cantidad_no_altera_el_precio_congelado(self):
        pedido = self.pedir(mesa=self.m1)
        detalle = pedido.detalles.first()
        self.arroz.precio = 99999; self.arroz.save()
        cambiar_cantidad(pedido, self.mesero, detalle.id, 3)
        detalle.refresh_from_db()
        self.assertEqual(detalle.precio_congelado, 10000)

    def test_L203_quitar_el_ultimo_renglon_se_rechaza(self):
        pedido = self.pedir(mesa=self.m1)
        with self.assertRaises(NovedadInvalida):
            quitar_item(pedido, self.mesero, pedido.detalles.first().id)

    def test_L204_un_pedido_entregado_no_se_puede_editar(self):
        pedido = self.pedir(mesa=self.m1)
        pedido.estado = Pedido.ENTREGADO; pedido.save()
        with self.assertRaises(NovedadInvalida):
            agregar_item(pedido, self.mesero, plato_id=self.jugo.id)

    def test_L205_liberar_mesa_con_pedido_avisa_cuantos_hay_en_curso(self):
        self.pedir(mesa=self.m1)
        r = self.api(self.mesero).post("/api/mesas/M1/estado/", {"estado": "libre"}, format="json")
        self.assertEqual(r.json()["pedidos_en_curso"], 1)

    def test_L206_sin_sesion_o_con_rol_cocina_no_se_edita(self):
        pedido = self.pedir(mesa=self.m1)
        ruta = f"/api/pedidos/{pedido.id}/destino/"
        self.assertIn(APIClient().post(ruta, {"mesa": "M2"}, format="json").status_code, (401, 403))
        self.assertEqual(self.api(self.cocinero).post(ruta, {"mesa": "M2"}, format="json").status_code, 403)


class Spec012Salon(Base):
    def salon(self):
        return self.api(self.mesero).get("/api/mesas/salon/").json()

    def test_L160_el_salon_lista_mesas_fisicas_y_ninguna_virtual(self):
        codigos = {m["codigo"] for m in self.salon()["mesas"]}
        self.assertEqual(codigos, {"M1", "M2"})

    def test_L161_L162_domicilios_en_su_zona_y_sin_tope(self):
        for _ in range(15):
            self.pedir(domicilio=True)
        s = self.salon()
        self.assertEqual(len(s["domicilios"]), 15)
        self.assertEqual({m["codigo"] for m in s["mesas"]}, {"M1", "M2"})

    def test_L163_domicilio_cobrado_no_entregado_sigue_visible_y_se_distingue(self):
        pedido = self.pedir(domicilio=True)
        from ventas.operaciones import cerrar_cuenta
        cerrar_cuenta(pedido.cuenta, self.cajero, self.efectivo.id)
        dom = next(d for d in self.salon()["domicilios"] if d["pedido_id"] == pedido.id)
        self.assertIs(dom["cobrada"], True, "sigue visible y marcado como cobrado")
        otro = self.pedir(domicilio=True)
        sin_cobrar = next(d for d in self.salon()["domicilios"] if d["pedido_id"] == otro.id)
        self.assertIs(sin_cobrar["cobrada"], False, "y se distingue de uno sin cobrar")

    def test_L164_marcar_entregado_lo_retira_de_la_zona(self):
        pedido = self.pedir(domicilio=True)
        self.api(self.mesero).post(f"/api/pedidos/{pedido.id}/entregar/")
        self.assertNotIn(pedido.id, [d["pedido_id"] for d in self.salon()["domicilios"]])

    def test_L165_L166_domicilio_se_entrega_sin_estar_listo_y_por_cualquier_mesero(self):
        pedido = self.pedir(domicilio=True, usuario=self.mesero)
        self.assertEqual(pedido.estado, Pedido.PENDIENTE)
        r = self.api(self.otro_mesero).post(f"/api/pedidos/{pedido.id}/entregar/")
        self.assertEqual(r.status_code, 200, r.content[:200])

    def test_L167_escanear_el_qr_de_mesa_la_deja_libre(self):
        self.api(self.mesero).get("/api/mesas/validar/M1/")
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.estado, Mesa.LIBRE)

    def test_L168_generar_el_qr_de_pedido_la_deja_libre(self):
        firmar_pedido("M1", "x", [{"plato_id": self.arroz.id, "cantidad": 1, "observacion": ""}])
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.estado, Mesa.LIBRE)

    def test_L169_confirmar_deja_la_mesa_ocupada(self):
        self.pedir(mesa=self.m1)
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.estado, Mesa.OCUPADA)

    def test_L170_L171_apartar_y_luego_confirmar_la_ocupa(self):
        self.api(self.mesero).post("/api/mesas/M1/estado/", {"estado": "apartada"}, format="json")
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.estado, Mesa.APARTADA)
        self.pedir(mesa=self.m1)
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.estado, Mesa.OCUPADA)

    def test_L172_L173_liberar_con_pedido_en_cocina_funciona_y_no_toca_el_pedido(self):
        pedido = self.pedir(mesa=self.m1)
        antes = pedido.estado
        r = self.api(self.mesero).post("/api/mesas/M1/estado/", {"estado": "libre"}, format="json")
        self.assertEqual(r.status_code, 200)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, antes)

    def test_L175_revertir_devuelve_el_estado_anterior(self):
        self.pedir(mesa=self.m1)
        c = self.api(self.mesero)
        c.post("/api/mesas/M1/estado/", {"estado": "libre"}, format="json")
        c.post("/api/mesas/M1/estado/", {"estado": "ocupada"}, format="json")
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.estado, Mesa.OCUPADA)


class Spec013Cuenta(Base):
    def test_L159_L160_primer_pedido_abre_cuenta_y_el_segundo_se_suma(self):
        p1 = self.pedir(mesa=self.m1)
        p2 = self.pedir(mesa=self.m1)
        self.assertEqual(p1.cuenta_id, p2.cuenta_id)
        self.assertEqual(Cuenta.objects.filter(mesa=self.m1).count(), 1)

    def test_L161_un_domicilio_abre_su_propia_cuenta(self):
        a = self.pedir(domicilio=True)
        b = self.pedir(domicilio=True)
        self.assertNotEqual(a.cuenta_id, b.cuenta_id)

    def test_L162_L163_el_total_es_la_suma_y_el_salon_lo_muestra(self):
        self.pedir(mesa=self.m1, items=[(self.arroz, 2)])
        self.pedir(mesa=self.m1, items=[(self.pollo, 1)])
        mesa = next(m for m in self.api(self.mesero).get("/api/mesas/salon/").json()["mesas"]
                    if m["codigo"] == "M1")
        self.assertEqual(mesa["cuenta_total"], 40000)

    def test_L164_cerrar_exige_medio_de_pago(self):
        pedido = self.pedir(mesa=self.m1)
        r = self.api(self.cajero).post(f"/api/cuentas/{pedido.cuenta_id}/cerrar/", {}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_L165_L166_al_cerrar_se_congela_y_cambiar_el_precio_no_lo_altera(self):
        pedido = self.pedir(mesa=self.m1)
        self.api(self.cajero).post(f"/api/cuentas/{pedido.cuenta_id}/cerrar/",
                                   {"medio_pago": self.efectivo.id}, format="json")
        cuenta = Cuenta.objects.get(pk=pedido.cuenta_id)
        total = cuenta.total_congelado
        self.assertIsNotNone(cuenta.subtotal_congelado)
        self.arroz.precio = 99999; self.arroz.save()
        cuenta.refresh_from_db()
        self.assertEqual(cuenta.total_congelado, total)

    def test_L167_una_cuenta_cerrada_no_recibe_pedidos_nuevos(self):
        p1 = self.pedir(mesa=self.m1)
        self.api(self.cajero).post(f"/api/cuentas/{p1.cuenta_id}/cerrar/",
                                   {"medio_pago": self.efectivo.id}, format="json")
        p2 = self.pedir(mesa=self.m1)
        self.assertNotEqual(p2.cuenta_id, p1.cuenta_id, "el pedido nuevo abre otra cuenta")

    def test_L168_la_propina_se_puede_quitar(self):
        pedido = self.pedir(mesa=self.m1)
        self.api(self.cajero).post(f"/api/cuentas/{pedido.cuenta_id}/cerrar/",
                                   {"medio_pago": self.efectivo.id, "aplica_propina": False}, format="json")
        self.assertEqual(Cuenta.objects.get(pk=pedido.cuenta_id).propina_congelada, 0)

    def test_L170_la_lista_de_cuentas_abiertas_trae_el_total(self):
        pedido = self.pedir(mesa=self.m1, items=[(self.pollo, 1)])
        abiertas = self.api(self.mesero).get("/api/cuentas/").json()
        cuenta = next(c for c in abiertas if c["id"] == pedido.cuenta_id)
        self.assertEqual(cuenta["subtotal"], 20000)

    def test_L171_L172_anular_exige_motivo_y_anula_sus_pedidos(self):
        pedido = self.pedir(mesa=self.m1)
        c = self.api(self.cajero)
        self.assertEqual(c.post(f"/api/cuentas/{pedido.cuenta_id}/anular/", {}, format="json").status_code, 400)
        c.post(f"/api/cuentas/{pedido.cuenta_id}/anular/", {"motivo": "cliente se fue"}, format="json")
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.ANULADO)
        self.assertIsNotNone(Cuenta.objects.get(pk=pedido.cuenta_id).anulada_por)

    def test_L173_liberar_la_mesa_no_altera_su_cuenta_abierta(self):
        pedido = self.pedir(mesa=self.m1)
        self.api(self.mesero).post("/api/mesas/M1/estado/", {"estado": "libre"}, format="json")
        self.assertEqual(Cuenta.objects.get(pk=pedido.cuenta_id).estado, Cuenta.ABIERTA)

    def test_L174_cerrar_la_cuenta_no_libera_la_mesa_sola(self):
        pedido = self.pedir(mesa=self.m1)
        self.api(self.cajero).post(f"/api/cuentas/{pedido.cuenta_id}/cerrar/",
                                   {"medio_pago": self.efectivo.id}, format="json")
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.estado, Mesa.OCUPADA)

    def test_L175_sin_sesion_no_se_cierra_ni_se_anula(self):
        pedido = self.pedir(mesa=self.m1)
        anon = APIClient()
        self.assertIn(anon.post(f"/api/cuentas/{pedido.cuenta_id}/cerrar/",
                                {"medio_pago": self.efectivo.id}, format="json").status_code, (401, 403))
        self.assertIn(anon.post(f"/api/cuentas/{pedido.cuenta_id}/anular/",
                                {"motivo": "xx"}, format="json").status_code, (401, 403))


class Spec005Estaciones(Base):
    def test_L127_una_comanda_ya_tomada_no_se_vuelve_a_tomar(self):
        pedido = self.pedir(mesa=self.m1)
        comanda = pedido.comandas.first()
        c = self.api(self.cocinero)
        primero = c.post(f"/api/comandas/{comanda.id}/en-preparacion/")
        segundo = c.post(f"/api/comandas/{comanda.id}/en-preparacion/")
        self.assertEqual(primero.status_code, 200)
        self.assertEqual(segundo.status_code, 409, "la segunda toma debería rechazarse")
        self.assertIn("detalle", segundo.json())

    def test_L127_dos_cocineros_a_la_vez_solo_uno_la_toma(self):
        """
        Corregido 2026-09-14. Dos peticiones en el mismo instante, como en
        ADR-008: sin el bloqueo las dos leían "pendiente" y las dos la tomaban.
        """
        comanda = self.pedir(mesa=self.m1).comandas.first()
        salidas = en_paralelo(2, lambda i: self.api(self.cocinero).post(
            f"/api/comandas/{comanda.id}/en-preparacion/").status_code)
        self.assertEqual(sorted(salidas), [200, 409], salidas)

    def test_dos_listo_a_la_vez_avisan_una_sola_vez(self):
        """El mismo fallo en "Listo": dos toques seguidos avisaban dos veces."""
        comanda = self.pedir(mesa=self.m1).comandas.first()
        salidas = en_paralelo(2, lambda i: self.api(self.cocinero).post(
            f"/api/comandas/{comanda.id}/lista/").status_code)
        self.assertEqual(sorted(salidas), [200, 409], salidas)
        self.assertEqual(Notificacion.objects.filter(comanda=comanda).count(), 1)

    def test_dos_estaciones_terminan_a_la_vez_y_el_pedido_queda_listo(self):
        """
        Cocina y bar marcan "Listo" en el mismo instante. Cada una calcula el
        estado del pedido mirando las comandas de la otra: sin bloquear el
        pedido, las dos veían a la otra sin terminar y el pedido se quedaba
        "en preparación" con todo listo.
        """
        pedido = self.pedir(mesa=self.m1, items=[(self.arroz, 1), (self.jugo, 1)])
        ids = list(pedido.comandas.values_list("id", flat=True))
        self.assertEqual(len(ids), 2)
        salidas = en_paralelo(2, lambda i: self.api(self.cocinero).post(
            f"/api/comandas/{ids[i]}/lista/").status_code)
        self.assertEqual(salidas, [200, 200])
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.LISTO)


class Spec023TableroUnificado(Base):
    """
    SPEC-023, sección 7 (revisado 2026-09-16): con estaciones unificadas el
    tablero pide las comandas de TODAS las estaciones, solo las que están en
    curso, y cada tarjeta dice de qué estación viene.
    """

    def test_todas_las_estaciones_juntas_solo_en_curso_y_con_su_estacion(self):
        # Un pedido que llegó al bar ANTES de unificar, y otro ya entregado.
        del_bar = self.pedir(mesa=self.m1, items=[(self.jugo, 1)])
        entregado = self.pedir(mesa=self.m2, items=[(self.arroz, 1)])
        Pedido.objects.filter(pk=entregado.pk).update(estado=Pedido.ENTREGADO)

        r = self.api(self.cocinero).get("/api/comandas/", {"activas": 1})
        self.assertEqual(r.status_code, 200)
        tarjetas = r.json()["results"]
        self.assertEqual([t["pedido"] for t in tarjetas], [del_bar.id])
        self.assertEqual(tarjetas[0]["estacion_nombre"], "Bar")
        self.assertFalse(tarjetas[0]["estacion_por_defecto"])


class Spec013CobrarLiberaLaMesa(Base):
    """SPEC-013, revisado 2026-09-16: cobrar libera la mesa; pagado, no se edita."""

    def cobrar(self, pedido, liberar):
        return self.api(self.cajero).post(
            f"/api/cuentas/{pedido.cuenta_id}/cerrar/",
            {"medio_pago": self.efectivo.id, "liberar_mesa": liberar}, format="json")

    def test_cobrar_libera_la_mesa_y_el_anticipado_no(self):
        normal = self.pedir(mesa=self.m1)
        self.assertEqual(self.cobrar(normal, True).status_code, 200)
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.estado, Mesa.LIBRE)

        anticipado = self.pedir(mesa=self.m2)
        self.assertEqual(self.cobrar(anticipado, False).status_code, 200)
        self.m2.refresh_from_db()
        self.assertEqual(self.m2.estado, Mesa.OCUPADA)

    def test_un_pedido_cobrado_no_acepta_platos_y_lo_nuevo_abre_otra_cuenta(self):
        pedido = self.pedir(mesa=self.m1)
        self.cobrar(pedido, False)
        r = self.api(self.mesero).post(
            f"/api/pedidos/{pedido.id}/items/agregar/", {"plato_id": self.pollo.id}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("pedido nuevo", r.json()["detalle"])
        self.assertEqual(pedido.detalles.count(), 1)

        detalle = pedido.detalles.first()
        r = self.api(self.mesero).post(
            f"/api/pedidos/{pedido.id}/items/cantidad/", {"detalle_id": detalle.id, "cantidad": 3}, format="json")
        self.assertEqual(r.status_code, 400)

        otro = self.pedir(mesa=self.m1)
        self.assertNotEqual(otro.cuenta_id, pedido.cuenta_id)


class Spec013CostoDeEnvio(Base):
    """SPEC-013/025, 2026-09-16: costo de envío al confirmar un domicilio."""

    def test_domicilio_con_costo_de_envio_suma_al_total(self):
        pedido = self.pedir(domicilio=True, costo_envio=8000)
        r = self.api(self.mesero).get(f"/api/cuentas/{pedido.cuenta_id}/")
        datos = r.json()
        self.assertEqual(datos["envio"], 8000)
        self.assertEqual(datos["total"], datos["subtotal"] + datos["propina"] + datos["impuesto"] + 8000)

    def test_domicilio_sin_costo_de_envio_queda_en_cero(self):
        pedido = self.pedir(domicilio=True)
        self.assertEqual(pedido.cuenta.costo_envio, 0)

    def test_una_mesa_no_acepta_costo_de_envio(self):
        pedido = self.pedir(mesa=self.m1, costo_envio=5000)
        self.assertEqual(pedido.cuenta.costo_envio, 0)

    def test_costo_de_envio_negativo_se_rechaza(self):
        texto = firmar_pedido(
            "", "Cliente", [{"plato_id": self.arroz.id, "cantidad": 1, "observacion": ""}],
            es_domicilio=True)
        r = self.api(self.mesero).post(
            "/api/pedidos/confirmar/", {"texto": texto, "costo_envio": -1000}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Pedido.objects.exists())
