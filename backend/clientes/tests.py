"""
SPEC-019. Las reglas que sostienen el directorio de clientes.

`TransactionTestCase` por lo mismo que en `ventas/tests.py`: hay una prueba de
concurrencia con hilos, y `TestCase` los dejaria sin ver las confirmaciones.
"""

import threading

from django.contrib.auth.models import Group, User
from django.db import connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from clientes.models import Cliente, DireccionCliente, normalizar_direccion, normalizar_telefono
from clientes.operaciones import reconocer_o_crear, resumen_de
from estaciones.models import Estacion
from menu.models import Categoria, Plato
from pedidos.firma import firmar_pedido
from ventas.models import Caja, Cuenta
from ventas.operaciones import cerrar_cuenta


class Normalizacion(TransactionTestCase):
    def test_el_mismo_numero_escrito_de_varias_formas_es_uno_solo(self):
        formas = ["3202766485", "320 276 6485", "+57 320 276 6485",
                  "57 3202766485", "(320) 276-6485"]
        normalizados = {normalizar_telefono(f) for f in formas}
        self.assertEqual(normalizados, {"3202766485"},
                         f"deberian ser el mismo numero, salieron {normalizados}")

    def test_la_direccion_ignora_mayusculas_tildes_y_puntuacion(self):
        iguales = ["Barrio Libertad", "barrio libertad", "  BARRIO   LIBERTAD  ",
                   "Barrio Libertad."]
        self.assertEqual(len({normalizar_direccion(d) for d in iguales}), 1)

    def test_NO_se_ordenan_las_palabras_de_la_direccion(self):
        """
        Ordenarlas haria coincidir "barrio xxx" con "xxx barrio", pero tambien
        `calle 5 casa 20` con `calle 20 casa 5`, que son dos casas distintas.
        Equivocarse ahi es mandar la comida a otra direccion.
        """
        self.assertNotEqual(
            normalizar_direccion("calle 5 casa 20"),
            normalizar_direccion("calle 20 casa 5"))


class ReconocerCliente(TransactionTestCase):
    def test_un_telefono_nuevo_crea_el_cliente(self):
        cliente, _, es_nuevo = reconocer_o_crear("3202766485", "Maria Angelica", "Barrio xxx")
        self.assertTrue(es_nuevo)
        self.assertEqual(cliente.telefono, "3202766485")
        self.assertEqual(cliente.direcciones.count(), 1)

    def test_el_mismo_telefono_con_OTRO_nombre_es_el_mismo_cliente(self):
        """
        El caso que planteo el autor: pedido 1 dice "maria angelica", pedido 2
        dice "angelica lopez". El telefono manda.
        """
        c1, _, _ = reconocer_o_crear("3202766485", "maria angelica", "Barrio xxx")
        c2, _, es_nuevo = reconocer_o_crear("320 276 6485", "angelica lopez", "Barrio xxx")

        self.assertEqual(c1.id, c2.id, "debe ser el mismo cliente")
        self.assertFalse(es_nuevo)
        self.assertEqual(Cliente.objects.count(), 1)
        c2.refresh_from_db()
        self.assertEqual(c2.nombre, "angelica lopez", "gana el nombre mas reciente")

    def test_la_misma_direccion_escrita_distinto_no_se_duplica(self):
        reconocer_o_crear("3202766485", "Angelica", "Barrio Libertad")
        cliente, usada, _ = reconocer_o_crear("3202766485", "Angelica", "barrio libertad")

        self.assertEqual(cliente.direcciones.count(), 1, "es la misma direccion")
        self.assertEqual(usada.veces_usada, 2)

    def test_una_direccion_con_las_palabras_al_reves_se_guarda_APARTE(self):
        """
        "barrio xxx" y "xxx barrio" PUEDEN ser lo mismo, pero el sistema no
        puede saberlo. Se guardan las dos y que la persona elija: duplicar una
        direccion es ruido menor, mandar la comida a otra casa no.
        """
        reconocer_o_crear("3202766485", "Angelica", "barrio kennedy")
        cliente, _, _ = reconocer_o_crear("3202766485", "Angelica", "kennedy barrio")

        self.assertEqual(cliente.direcciones.count(), 2)

    def test_sin_telefono_no_se_crea_cliente(self):
        cliente, _, _ = reconocer_o_crear("", "Alguien", "Una direccion")
        self.assertIsNone(cliente)
        self.assertEqual(Cliente.objects.count(), 0)

    def test_dos_domicilios_del_mismo_telefono_a_la_vez_no_duplican(self):
        """Misma carrera que ADR-008, resuelta con el `unique` y relectura."""
        barrera = threading.Barrier(2)

        def crear(_):
            try:
                barrera.wait()
                reconocer_o_crear("3202766485", "Angelica", "Barrio xxx")
            finally:
                connections.close_all()

        hilos = [threading.Thread(target=crear, args=(i,)) for i in range(2)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        self.assertEqual(Cliente.objects.filter(telefono="3202766485").count(), 1)


class ClienteYSusVentas(TransactionTestCase):
    def setUp(self):
        self.cajero = User.objects.create_user("cajero_cli", password="x")
        self.cajero.groups.add(Group.objects.get_or_create(name="cajero")[0])
        self.mesero = User.objects.create_user("mesero_cli", password="x")
        self.mesero.groups.add(Group.objects.get_or_create(name="mesero")[0])

        estacion = Estacion.objects.create(nombre="Cocina", por_defecto=True)
        cat = Categoria.objects.create(nombre="Platos", estacion=estacion)
        self.plato = Plato.objects.create(categoria=cat, nombre="Arroz", precio=10000)
        self.efectivo = Caja.objects.create(nombre="Efectivo")
        self._n = 0

    def _domicilio(self, telefono, nombre, direccion, cobrar=True):
        self._n += 1
        cli = APIClient()
        cli.force_authenticate(self.mesero)
        # La observacion lleva el contador porque el QR se firma con marca de
        # tiempo al SEGUNDO: dos pedidos identicos en el mismo segundo darian
        # el mismo codigo y el segundo seria rechazado como QR repetido — que
        # es lo correcto en produccion, pero aqui solo estorba.
        texto = firmar_pedido(
            "", nombre,
            [{"plato_id": self.plato.id, "cantidad": 1, "observacion": f"#{self._n}"}],
            es_domicilio=True, telefono=telefono, direccion=direccion)
        r = cli.post("/api/pedidos/confirmar/", {"texto": texto}, format="json")
        cuenta = Cuenta.objects.get(pk=r.json()["cuenta_id"])
        if cobrar:
            cerrar_cuenta(cuenta, self.cajero, self.efectivo.id)
        return cuenta

    def test_confirmar_un_domicilio_engancha_el_cliente(self):
        cuenta = self._domicilio("3202766485", "Angelica", "Barrio xxx")
        cuenta.refresh_from_db()

        self.assertIsNotNone(cuenta.cliente)
        self.assertEqual(cuenta.cliente.telefono, "3202766485")
        self.assertEqual(cuenta.cliente.direcciones.count(), 1)

    def test_borrar_un_cliente_NO_borra_sus_ventas(self):
        """
        Requisito de la Ley 1581: el titular puede pedir que se supriman sus
        datos. Pero el historial contable no se reescribe (SPEC-008).
        """
        cuenta = self._domicilio("3202766485", "Angelica", "Barrio xxx")
        cuenta.refresh_from_db()
        total = cuenta.total_congelado

        Cliente.objects.get(telefono="3202766485").delete()

        cuenta.refresh_from_db()
        self.assertIsNone(cuenta.cliente, "el vinculo se suelta")
        self.assertEqual(cuenta.estado, Cuenta.CERRADA, "la venta sigue existiendo")
        self.assertEqual(cuenta.total_congelado, total, "y con su total intacto")
        self.assertEqual(DireccionCliente.objects.count(), 0, "sus direcciones si se van")

    def test_el_resumen_solo_cuenta_las_ventas_cobradas(self):
        self._domicilio("3202766485", "Angelica", "Barrio xxx")
        self._domicilio("3202766485", "Angelica", "Barrio xxx", cobrar=False)

        cliente = Cliente.objects.get(telefono="3202766485")
        self.assertEqual(resumen_de(cliente)["compras"], 1,
                         "una cuenta abierta todavia no es una compra")

    def test_verificar_avisa_si_el_cliente_ya_es_conocido(self):
        """
        Es el seguro contra el digito mal escrito: la pantalla dice a quien
        cree que esta atendiendo ANTES de confirmar.
        """
        self._domicilio("3202766485", "Angelica", "Barrio xxx")

        cli = APIClient()
        texto = firmar_pedido(
            "", "Angelica", [{"plato_id": self.plato.id, "cantidad": 1, "observacion": ""}],
            es_domicilio=True, telefono="3202766485", direccion="Barrio xxx")
        r = cli.post("/api/pedidos/verificar/", {"texto": texto}, format="json").json()

        self.assertIsNotNone(r["cliente_conocido"])
        self.assertEqual(r["cliente_conocido"]["nombre"], "Angelica")
        self.assertEqual(r["cliente_conocido"]["compras"], 1)
        self.assertEqual(len(r["cliente_conocido"]["direcciones"]), 1)

    def test_verificar_de_un_telefono_nuevo_dice_que_no_lo_conoce(self):
        cli = APIClient()
        texto = firmar_pedido(
            "", "Nuevo", [{"plato_id": self.plato.id, "cantidad": 1, "observacion": ""}],
            es_domicilio=True, telefono="3009998877", direccion="Otra parte")
        r = cli.post("/api/pedidos/verificar/", {"texto": texto}, format="json").json()

        self.assertIsNone(r["cliente_conocido"])

    def test_un_QR_viejo_sin_telefono_sigue_siendo_valido(self):
        """Compatibilidad: los QR emitidos antes de SPEC-019 no traen telefono."""
        cli = APIClient()
        cli.force_authenticate(self.mesero)
        texto = firmar_pedido(
            "", "Sin telefono",
            [{"plato_id": self.plato.id, "cantidad": 1, "observacion": ""}],
            es_domicilio=True)
        r = cli.post("/api/pedidos/confirmar/", {"texto": texto}, format="json")

        self.assertEqual(r.status_code, 201)
        self.assertIsNone(Cuenta.objects.get(pk=r.json()["cuenta_id"]).cliente)

    def test_quien_NO_puede_cobrar_no_ve_los_clientes(self):
        """
        El directorio es un fichero de datos personales: lo ve quien cobra y el
        administrador (SPEC-019). Se comprueba en el SERVIDOR, porque esconder
        el enlace no es un permiso.
        """
        from django.core.cache import cache

        from configuracion.models import Parametro
        from ventas.operaciones import CLAVE_MESEROS_COBRAN

        Parametro.objects.update_or_create(
            clave=CLAVE_MESEROS_COBRAN,
            defaults={"etiqueta": "Los meseros pueden cobrar", "valor": "no"})
        # La configuracion se cachea 60s: sin limpiarla, la prueba leeria la
        # anterior y pasaria por la razon equivocada.
        cache.clear()

        cli = APIClient()
        cli.force_authenticate(self.mesero)
        self.assertEqual(cli.get("/api/clientes/").status_code, 403)

        cli.force_authenticate(self.cajero)
        self.assertEqual(cli.get("/api/clientes/").status_code, 200)

    def test_sin_sesion_no_se_ve_el_directorio(self):
        self.assertIn(APIClient().get("/api/clientes/").status_code, (401, 403))

    def test_una_venta_de_MESA_no_engancha_ningun_cliente(self):
        from pedidos.models import Mesa

        mesa = Mesa.objects.create(codigo="M-CLI", nombre="Mesa cliente")
        cli = APIClient()
        cli.force_authenticate(self.mesero)
        texto = firmar_pedido(
            mesa.codigo, "Alguien",
            [{"plato_id": self.plato.id, "cantidad": 1, "observacion": ""}])
        r = cli.post("/api/pedidos/confirmar/", {"texto": texto}, format="json")

        self.assertIsNone(Cuenta.objects.get(pk=r.json()["cuenta_id"]).cliente)
        self.assertEqual(Cliente.objects.count(), 0)
