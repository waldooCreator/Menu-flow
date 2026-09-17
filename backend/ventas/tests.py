"""
Pruebas de CONCURRENCIA: qué queda en la base cuando dos operaciones caen en
el mismo milisegundo.

Son distintas de una prueba de carga. Una prueba de carga mide velocidad y con
usuarios repartidos al azar casi nunca hace que dos peticiones toquen la misma
cuenta en la misma fracción de segundo — por eso habría dado todo verde
mientras la caja se cobraba dos veces. Estas fuerzan la coincidencia con una
barrera: los hilos esperan y salen todos a la vez.

Cada caso aquí nació de un fallo real medido el 2026-09-03, no de imaginar qué
podría pasar.

`TransactionTestCase` y no `TestCase`: `TestCase` mete cada prueba en una
transacción que nunca se confirma, así que los otros hilos no verían nada. Aquí
hacen falta confirmaciones de verdad.
"""

import threading

from django.contrib.auth.models import Group, User
from django.db import connections
from django.db.models import ProtectedError
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from estaciones.models import Estacion
from menu.models import Categoria, Plato
from pedidos.firma import firmar_pedido
from pedidos.models import Mesa, Pedido
from ventas.models import Caja, CategoriaGasto, Cuenta, MovimientoCaja, Turno
from ventas.operaciones import (
    OperacionInvalida,
    abrir_turno,
    ajustar_saldo,
    anular_cuenta,
    calcular_totales,
    cerrar_cuenta,
    cerrar_turno,
    cuadre_de,
    fijar_saldo_inicial,
    registrar_gasto,
    registrar_movimiento,
    trasladar,
)


def en_paralelo(cantidad, trabajo):
    """
    Lanza `cantidad` hilos que esperan en una barrera y salen en el mismo
    instante. Devuelve la lista de resultados en orden de hilo.

    Cada hilo cierra SU conexión: Django abre una por hilo, y dejarlas
    abiertas agota el pool de Postgres.
    """
    barrera = threading.Barrier(cantidad)
    salidas = [None] * cantidad

    def correr(i):
        try:
            barrera.wait()
            salidas[i] = trabajo(i)
        except Exception as e:  # noqa: BLE001 — se reporta, no se traga
            salidas[i] = ("EXCEPCION", f"{type(e).__name__}: {e}")
        finally:
            connections.close_all()

    hilos = [threading.Thread(target=correr, args=(i,)) for i in range(cantidad)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    return salidas


class BaseConcurrencia(TransactionTestCase):
    def setUp(self):
        self.mesero = User.objects.create_user("mesero_prueba", password="x")
        self.mesero.groups.add(Group.objects.get_or_create(name="mesero")[0])
        self.admin = User.objects.create_user("admin_prueba", password="x", is_staff=True)

        estacion = Estacion.objects.create(nombre="Cocina", por_defecto=True)
        categoria = Categoria.objects.create(nombre="Platos", estacion=estacion)
        self.plato = Plato.objects.create(categoria=categoria, nombre="Arroz", precio=10000)
        self.mesa = Mesa.objects.create(codigo="M-TEST", nombre="Mesa de prueba")
        self.caja = Caja.objects.create(nombre="Efectivo")

    def qr(self, nombre, mesa_codigo=None):
        return firmar_pedido(
            mesa_codigo if mesa_codigo is not None else self.mesa.codigo,
            nombre,
            [{"plato_id": self.plato.id, "cantidad": 2, "observacion": ""}],
            False,
        )

    def confirmar(self, texto):
        c = APIClient()
        c.force_authenticate(self.mesero)
        r = c.post("/api/pedidos/confirmar/", {"texto": texto}, format="json")
        return r.status_code


class ConfirmarPedidoConcurrente(BaseConcurrencia):
    def test_varios_meseros_misma_mesa_no_pierden_pedidos(self):
        """
        Tres meseros confirmando a la vez en la misma mesa.

        Antes: los tres leían "no hay cuenta abierta", los tres intentaban
        crearla, la restricción de la base dejaba pasar a uno y los otros dos
        se caían con un 500. Con 10 simultáneos sobrevivía UN pedido de diez.
        """
        textos = [self.qr(f"Cliente {i}") for i in range(3)]
        codigos = en_paralelo(3, lambda i: self.confirmar(textos[i]))

        self.assertEqual(codigos, [201, 201, 201], f"alguno falló: {codigos}")
        self.assertEqual(
            Pedido.objects.filter(mesa=self.mesa).count(), 3,
            "los tres pedidos deben quedar registrados")
        self.assertEqual(
            Cuenta.objects.filter(mesa=self.mesa, estado=Cuenta.ABIERTA).count(), 1,
            "SPEC-013 regla 1: una sola cuenta abierta por mesa")

    def test_diez_a_la_vez_es_el_mismo_caso_en_grande(self):
        textos = [self.qr(f"C{i}") for i in range(10)]
        codigos = en_paralelo(10, lambda i: self.confirmar(textos[i]))

        self.assertTrue(all(c == 201 for c in codigos), f"hubo fallos: {codigos}")
        self.assertEqual(Pedido.objects.filter(mesa=self.mesa).count(), 10)
        self.assertEqual(
            Cuenta.objects.filter(mesa=self.mesa, estado=Cuenta.ABIERTA).count(), 1)

    def test_mismo_qr_dos_veces_da_409_no_500(self):
        """
        El QR repetido siempre creó un solo pedido — eso lo garantiza el
        `unique` de codigo_qr. Lo que fallaba era la forma de decirlo: salía un
        500 en vez del 409 con su explicación.
        """
        mismo = self.qr("Cliente")
        codigos = sorted(en_paralelo(2, lambda i: self.confirmar(mismo)))

        self.assertEqual(codigos, [201, 409], f"se esperaba 201 y 409, salió {codigos}")
        self.assertEqual(Pedido.objects.count(), 1)

    def test_mismo_qr_de_domicilio_tambien_da_409(self):
        """El domicilio no tiene mesa que bloquear: lo frena el `unique`."""
        texto = firmar_pedido(
            "", "Cliente", [{"plato_id": self.plato.id, "cantidad": 1, "observacion": ""}],
            True)
        codigos = sorted(en_paralelo(2, lambda i: self.confirmar(texto)))

        self.assertEqual(codigos, [201, 409], f"se esperaba 201 y 409, salió {codigos}")
        self.assertEqual(Pedido.objects.count(), 1)


class CobroConcurrente(BaseConcurrencia):
    def setUp(self):
        super().setUp()
        self.confirmar(self.qr("Cliente"))
        self.cuenta = Cuenta.objects.get(mesa=self.mesa, estado=Cuenta.ABIERTA)

    def _cobrar(self):
        try:
            cerrar_cuenta(self.cuenta, self.admin, self.caja.id)
            return "cobrada"
        except Exception as e:  # noqa: BLE001
            return f"rechazada: {e}"

    def test_dos_cajeros_no_cobran_dos_veces(self):
        """
        El fallo más grave que apareció: los dos cajeros recibían 200 OK y la
        caja quedaba con el doble de plata. Nadie se enteraba hasta el cuadre,
        y como los movimientos son solo-inserción (ADR-007) la fila falsa ya
        no se podía quitar.
        """
        salidas = en_paralelo(2, lambda i: self._cobrar())

        ingresos = MovimientoCaja.objects.filter(
            cuenta=self.cuenta, tipo=MovimientoCaja.INGRESO)
        self.assertEqual(ingresos.count(), 1, f"cobro duplicado. Salidas: {salidas}")
        self.assertEqual(sum(1 for s in salidas if s == "cobrada"), 1)
        self.assertEqual(sum(1 for s in salidas if str(s).startswith("rechazada")), 1)

        self.cuenta.refresh_from_db()
        self.assertEqual(self.cuenta.estado, Cuenta.CERRADA)
        self.assertEqual(self.caja.saldo(), self.cuenta.total_congelado)

    def test_cinco_toques_seguidos_cobran_una_sola_vez(self):
        """El caso real: la pantalla tarda y el cajero toca varias veces."""
        en_paralelo(5, lambda i: self._cobrar())

        self.assertEqual(
            MovimientoCaja.objects.filter(
                cuenta=self.cuenta, tipo=MovimientoCaja.INGRESO).count(), 1)

    def test_dos_anulaciones_no_sacan_la_plata_dos_veces(self):
        """
        Mismo defecto que el cobro, al revés: anular una cuenta ya cobrada dos
        veces registraría dos egresos y la caja diría que salió el doble.
        """
        cerrar_cuenta(self.cuenta, self.admin, self.caja.id)
        self.cuenta.refresh_from_db()

        def anular(_):
            try:
                anular_cuenta(self.cuenta, self.admin, "prueba de concurrencia")
                return "anulada"
            except Exception as e:  # noqa: BLE001
                return f"rechazada: {e}"

        salidas = en_paralelo(2, anular)

        egresos = MovimientoCaja.objects.filter(
            cuenta=self.cuenta, tipo=MovimientoCaja.EGRESO)
        self.assertEqual(egresos.count(), 1, f"anulación duplicada. Salidas: {salidas}")
        self.assertEqual(self.caja.saldo(), 0, "lo que entró y salió debe cuadrar en cero")

    def test_anular_venta_antigua_con_caja_vacia_se_rechaza(self):
        """SPEC-020: una devolución no puede sacar plata que ya salió del cajón."""
        cerrar_cuenta(self.cuenta, self.admin, self.caja.id)
        self.cuenta.refresh_from_db()
        registrar_movimiento(
            self.caja, MovimientoCaja.EGRESO, self.cuenta.total_congelado,
            self.admin, descripcion="retiro de cierre de prueba",
        )

        with self.assertRaises(OperacionInvalida) as error:
            anular_cuenta(self.cuenta, self.admin, "devolución de prueba")

        self.assertIn("Registra primero de dónde sale", str(error.exception))
        self.cuenta.refresh_from_db()
        self.assertEqual(self.cuenta.estado, Cuenta.CERRADA)
        self.assertEqual(self.caja.saldo(), 0)

    def test_reponer_plata_y_anular_venta_antigua(self):
        cerrar_cuenta(self.cuenta, self.admin, self.caja.id)
        self.cuenta.refresh_from_db()
        registrar_movimiento(
            self.caja, MovimientoCaja.EGRESO, self.cuenta.total_congelado,
            self.admin, descripcion="retiro de cierre de prueba",
        )
        with self.assertRaises(OperacionInvalida):
            anular_cuenta(self.cuenta, self.admin, "devolución de prueba")

        registrar_movimiento(
            self.caja, MovimientoCaja.INGRESO, self.cuenta.total_congelado,
            self.admin, descripcion="reposición para devolución",
        )
        anular_cuenta(self.cuenta, self.admin, "devolución de prueba")
        self.assertEqual(self.caja.saldo(), 0)
        self.cuenta.refresh_from_db()
        self.assertEqual(self.cuenta.estado, Cuenta.ANULADA)


class TurnoDeCaja(TransactionTestCase):
    """
    SPEC-014, revisión del 2026-09-03: fondo por caja y cierre ajeno.

    Los dos salieron de revisar el sistema que se va a reemplazar: su
    formulario de apertura pide fondo para los ocho medios de pago, y su
    reporte tenía turnos abiertos desde hacía casi un mes.
    """

    def setUp(self):
        self.cajero = User.objects.create_user("cajero_prueba", password="x")
        self.cajero.groups.add(Group.objects.get_or_create(name="cajero")[0])
        self.otro = User.objects.create_user("otro_cajero", password="x")
        self.otro.groups.add(Group.objects.get_or_create(name="cajero")[0])
        self.admin = User.objects.create_user("admin_prueba", password="x", is_staff=True)

        self.efectivo = Caja.objects.create(nombre="Efectivo")
        self.nequi = Caja.objects.create(nombre="Nequi")
        self.datafono = Caja.objects.create(nombre="Datafono")

    def test_fondo_inicial_en_varias_cajas(self):
        from ventas.operaciones import abrir_turno

        turno = abrir_turno(self.cajero, fondos={
            self.efectivo.id: 200000, self.nequi.id: 50000})

        self.assertEqual(turno.movimientos.count(), 2)
        self.assertEqual(self.efectivo.saldo(), 200000)
        self.assertEqual(self.nequi.saldo(), 50000)
        self.assertEqual(self.datafono.saldo(), 0)

    def test_un_fondo_en_cero_no_deja_movimiento(self):
        """Una fila de cero pesos solo ensucia el libro."""
        from ventas.operaciones import abrir_turno

        turno = abrir_turno(self.cajero, fondos={
            self.efectivo.id: 100000, self.nequi.id: 0})

        self.assertEqual(turno.movimientos.count(), 1)

    def test_un_monto_invalido_no_deja_turno_a_medias(self):
        """
        Se validan todos los montos antes de crear nada: si el tercero viene
        mal escrito, no debe quedar un turno abierto con dos fondos puestos.
        """
        from ventas.operaciones import OperacionInvalida, abrir_turno

        with self.assertRaises(OperacionInvalida):
            abrir_turno(self.cajero, fondos={
                self.efectivo.id: 100000, self.nequi.id: "no es un numero"})

        self.assertEqual(Turno.objects.count(), 0)
        self.assertEqual(self.efectivo.saldo(), 0)

    def test_quien_puede_cobrar_cierra_el_turno_de_otro_con_motivo(self):
        """
        Revisado 2026-09-03: caja abre Y cierra los turnos de los meseros
        (no solo el propio), así que cualquiera con permiso de cobro puede
        cerrar el turno de otro — no hace falta ser administrador. El motivo
        obligatorio es lo que deja el rastro, no restringir quién puede.
        """
        from ventas.operaciones import OperacionInvalida, abrir_turno, cerrar_turno

        turno = abrir_turno(self.otro, fondos={self.efectivo.id: 100000})

        with self.assertRaises(OperacionInvalida):
            cerrar_turno(turno, efectivo_contado=100000, autor=self.cajero)
        turno.refresh_from_db()
        self.assertEqual(turno.estado, Turno.ABIERTO, "sin motivo no se cierra")

        cerrar_turno(turno, efectivo_contado=100000, autor=self.cajero,
                     observacion="lo cerré yo desde caja")
        turno.refresh_from_db()
        self.assertEqual(turno.estado, Turno.CERRADO)
        self.assertEqual(turno.cerrado_por, self.cajero)

    def test_quien_no_puede_cobrar_no_cierra_el_turno_de_otro(self):
        from django.contrib.auth.models import User

        from ventas.operaciones import OperacionInvalida, abrir_turno, cerrar_turno

        cocinero = User.objects.create_user("cocinero_prueba", password="x")
        cocinero.groups.add(Group.objects.get_or_create(name="cocina")[0])

        turno = abrir_turno(self.otro, fondos={self.efectivo.id: 100000})
        with self.assertRaises(OperacionInvalida):
            cerrar_turno(turno, efectivo_contado=100000, autor=cocinero,
                         observacion="motivo cualquiera")
        turno.refresh_from_db()
        self.assertEqual(turno.estado, Turno.ABIERTO)

    def test_el_admin_cierra_el_ajeno_pero_debe_dar_motivo(self):
        from ventas.operaciones import OperacionInvalida, abrir_turno, cerrar_turno

        turno = abrir_turno(self.otro, fondos={self.efectivo.id: 100000})

        with self.assertRaises(OperacionInvalida):
            cerrar_turno(turno, efectivo_contado=100000, autor=self.admin)

        cerrar_turno(turno, efectivo_contado=100000, autor=self.admin,
                     observacion="quedo abierto desde el lunes")
        turno.refresh_from_db()
        self.assertEqual(turno.estado, Turno.CERRADO)
        self.assertEqual(turno.cerrado_por, self.admin)

    def test_cerrar_el_propio_no_pide_motivo(self):
        from ventas.operaciones import abrir_turno, cerrar_turno

        turno = abrir_turno(self.cajero, fondos={self.efectivo.id: 100000})
        cerrar_turno(turno, efectivo_contado=95000, autor=self.cajero)

        turno.refresh_from_db()
        self.assertEqual(turno.estado, Turno.CERRADO)
        self.assertEqual(turno.cerrado_por, self.cajero)
        # El cuadre no se maquilla: faltan 5.000 y así se reporta.
        from ventas.operaciones import cuadre_de
        self.assertEqual(cuadre_de(turno)["diferencia"], -5000)

    def test_avisa_de_turnos_abiertos_de_dias_anteriores(self):
        from datetime import timedelta

        from django.utils import timezone as tz

        from ventas.operaciones import abrir_turno, turnos_viejos_abiertos

        de_hoy = abrir_turno(self.cajero, fondos={})
        viejo = abrir_turno(self.otro, fondos={})
        # `abierto_en` es auto_now_add: se corre a mano para simular el olvido.
        Turno.objects.filter(pk=viejo.pk).update(
            abierto_en=tz.now() - timedelta(days=8))

        ids = [t.id for t in turnos_viejos_abiertos()]
        self.assertIn(viejo.id, ids)
        self.assertNotIn(de_hoy.id, ids, "el turno de hoy no es un olvido")

    def test_abrir_turno_exige_elegir_usuario(self):
        """
        SPEC-014, 2026-09-03: caja abre el turno DE un mesero elegido, no
        automáticamente de quien tiene la sesión.
        """
        c = APIClient(); c.force_authenticate(self.cajero)
        r = c.post("/api/turnos/abrir/", {"fondos": {}}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("usuario", r.json()["detalle"].lower())

    def test_abrir_turno_para_otro_usuario(self):
        c = APIClient(); c.force_authenticate(self.cajero)
        r = c.post("/api/turnos/abrir/",
                    {"usuario_id": self.otro.id, "fondos": {self.efectivo.id: 50000}},
                    format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["responsable"], self.otro.username)
        self.assertTrue(Turno.objects.filter(responsable=self.otro, estado=Turno.ABIERTO).exists())

    def test_no_se_puede_abrir_turno_a_nombre_de_cualquiera(self):
        """No a cocina, no a un usuario inactivo: solo mesero/cajero activos."""
        from django.contrib.auth.models import User

        cocinero = User.objects.create_user("cocinero_prueba2", password="x")
        cocinero.groups.add(Group.objects.get_or_create(name="cocina")[0])

        c = APIClient(); c.force_authenticate(self.cajero)
        r = c.post("/api/turnos/abrir/", {"usuario_id": cocinero.id}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Turno.objects.filter(responsable=cocinero).exists())

    def test_lista_de_candidatos_solo_mesero_y_cajero_activos(self):
        from django.contrib.auth.models import User

        from ventas.operaciones import usuarios_para_turno

        cocinero = User.objects.create_user("cocinero_prueba3", password="x")
        cocinero.groups.add(Group.objects.get_or_create(name="cocina")[0])
        inactivo = User.objects.create_user("mesero_inactivo", password="x", is_active=False)
        inactivo.groups.add(Group.objects.get_or_create(name="mesero")[0])

        candidatos = {u.username for u in usuarios_para_turno()}
        self.assertIn(self.cajero.username, candidatos)
        self.assertIn(self.otro.username, candidatos)
        self.assertNotIn(cocinero.username, candidatos)
        self.assertNotIn(inactivo.username, candidatos)

    def test_turno_actual_trae_otros_turnos_abiertos(self):
        from ventas.operaciones import abrir_turno

        propio = abrir_turno(self.cajero, fondos={self.efectivo.id: 100000})
        ajeno = abrir_turno(self.otro, fondos={self.efectivo.id: 50000})

        c = APIClient(); c.force_authenticate(self.cajero)
        r = c.get("/api/turnos/actual/")
        data = r.json()
        self.assertEqual(data["turno"]["id"], propio.id)
        ids_otros = [t["id"] for t in data["otros_turnos_abiertos"]]
        self.assertIn(ajeno.id, ids_otros)
        self.assertNotIn(propio.id, ids_otros, "el propio no debe repetirse en 'otros'")


class LibroDeCaja(TransactionTestCase):
    """
    El libro (SPEC-014): que entro y salio, con filtros y totales.

    Nacio de un hueco encontrado el 2026-09-03: se podia registrar un
    movimiento pero no habia forma de VER la lista — la pantalla los pedia
    solo para contar las ventas fuera de turno. Un libro que no se puede
    leer no es un libro.
    """

    def setUp(self):
        self.cajero = User.objects.create_user("cajero_libro", password="x")
        self.cajero.groups.add(Group.objects.get_or_create(name="cajero")[0])
        self.efectivo = Caja.objects.create(nombre="Efectivo")
        self.nequi = Caja.objects.create(nombre="Nequi")
        self.c = APIClient()
        self.c.force_authenticate(self.cajero)

    def _mover(self, caja, tipo, monto, descripcion=""):
        return self.c.post("/api/movimientos/", {
            "caja": caja.id, "tipo": tipo, "monto": monto, "descripcion": descripcion,
        }, format="json")

    def test_los_totales_son_del_rango_no_de_la_pagina(self):
        """
        Los totales se calculan ANTES del tope de filas: si no, conciliar
        contra el banco daria un numero distinto segun cuanto quepa en
        pantalla, que es peor que no tenerlo.
        """
        self._mover(self.efectivo, "ingreso", 100000)
        self._mover(self.efectivo, "egreso", 30000)
        self._mover(self.nequi, "ingreso", 50000)

        r = self.c.get("/api/movimientos/").json()
        self.assertEqual(r["totales"]["ingresos"], 150000)
        self.assertEqual(r["totales"]["egresos"], 30000)
        self.assertEqual(r["totales"]["neto"], 120000)
        self.assertEqual(r["totales"]["cantidad"], 3)

    def test_filtro_por_caja_y_por_tipo(self):
        self._mover(self.efectivo, "ingreso", 100000)
        self._mover(self.nequi, "ingreso", 50000)
        self._mover(self.efectivo, "egreso", 20000)

        solo_nequi = self.c.get(f"/api/movimientos/?caja={self.nequi.id}").json()
        self.assertEqual(solo_nequi["totales"]["cantidad"], 1)
        self.assertEqual(solo_nequi["totales"]["ingresos"], 50000)

        solo_egresos = self.c.get("/api/movimientos/?tipo=egreso").json()
        self.assertEqual(solo_egresos["totales"]["cantidad"], 1)
        self.assertEqual(solo_egresos["totales"]["egresos"], 20000)

    def test_filtro_por_fechas(self):
        self._mover(self.efectivo, "ingreso", 100000)

        vacio = self.c.get("/api/movimientos/?desde=2020-01-01&hasta=2020-01-31").json()
        self.assertEqual(vacio["totales"]["cantidad"], 0)
        self.assertEqual(vacio["movimientos"], [])

        hoy = timezone.localtime().date().isoformat()
        con_datos = self.c.get(f"/api/movimientos/?desde={hoy}&hasta={hoy}").json()
        self.assertEqual(con_datos["totales"]["cantidad"], 1)

    def test_un_traslado_deja_dos_movimientos_y_no_cambia_el_neto(self):
        """
        Trasladar mueve plata ENTRE cajas: los saldos cambian, pero no entra
        ni sale nada del negocio, asi que el neto del libro es el mismo.
        """
        self._mover(self.efectivo, "ingreso", 100000)
        neto_antes = self.c.get("/api/movimientos/").json()["totales"]["neto"]

        r = self.c.post("/api/cajas/trasladar/", {
            "origen": self.efectivo.id, "destino": self.nequi.id,
            "monto": 40000, "descripcion": "Consignacion",
        }, format="json")
        self.assertEqual(r.status_code, 200, r.content)

        self.assertEqual(self.efectivo.saldo(), 60000)
        self.assertEqual(self.nequi.saldo(), 40000)

        libro = self.c.get("/api/movimientos/").json()
        self.assertEqual(libro["totales"]["neto"], neto_antes,
                         "un traslado no crea ni destruye plata")
        traslados = [m for m in libro["movimientos"] if m["concepto"] == "traslado"]
        self.assertEqual(len(traslados), 2, "un traslado son dos movimientos")

    def test_no_se_traslada_a_la_misma_caja(self):
        r = self.c.post("/api/cajas/trasladar/", {
            "origen": self.efectivo.id, "destino": self.efectivo.id, "monto": 1000,
        }, format="json")
        self.assertEqual(r.status_code, 400)

    def test_quien_no_puede_cobrar_no_ve_el_libro(self):
        cocinero = User.objects.create_user("cocinero_libro", password="x")
        cocinero.groups.add(Group.objects.get_or_create(name="cocina")[0])
        c = APIClient(); c.force_authenticate(cocinero)
        self.assertEqual(c.get("/api/movimientos/").status_code, 403)

    def test_el_historial_de_turnos_es_solo_del_administrador(self):
        """
        Copiado del sistema que se va a reemplazar: "Reporte de turnos" es la
        unica seccion de Cajeros que el rol cajero NO ve. Quien maneja la
        plata no audita su propio cuadre.
        """
        self.assertEqual(self.c.get("/api/turnos/").status_code, 403)

        admin = User.objects.create_user("admin_libro", password="x", is_staff=True)
        ca = APIClient(); ca.force_authenticate(admin)
        self.assertEqual(ca.get("/api/turnos/").status_code, 200)


class HistorialDeVentas(TransactionTestCase):
    """
    SPEC-015. La regla que mas importa: **la propina nunca va dentro del
    total de ventas.** Es de los meseros, no del restaurante, y mezclarlas le
    haria creer al dueño que vendio mas de lo que vendio.
    """

    def setUp(self):
        self.cajero = User.objects.create_user("cajero_ventas", password="x")
        self.cajero.groups.add(Group.objects.get_or_create(name="cajero")[0])
        self.mesero = User.objects.create_user("mesero_ventas", password="x")
        self.mesero.groups.add(Group.objects.get_or_create(name="mesero")[0])

        estacion = Estacion.objects.create(nombre="Cocina", por_defecto=True)
        categoria = Categoria.objects.create(nombre="Platos", estacion=estacion)
        self.plato = Plato.objects.create(categoria=categoria, nombre="Arroz", precio=10000)
        self.mesa = Mesa.objects.create(codigo="M-V", nombre="Mesa venta")
        self.efectivo = Caja.objects.create(nombre="Efectivo")
        self.nequi = Caja.objects.create(nombre="Nequi")

        self.c = APIClient()
        self.c.force_authenticate(self.cajero)

    def _vender(self, caja, cantidad=1, mesa=None, es_domicilio=False):
        """
        Crea un pedido, lo confirma y lo cobra. Devuelve la cuenta.

        El nombre del cliente lleva un contador porque el QR se firma con una
        marca de tiempo al SEGUNDO: dos ventas identicas en el mismo segundo
        producirian el mismo codigo y la segunda seria rechazada como QR
        repetido — que es justo lo que debe pasar en produccion, pero aqui
        solo estorbaria.
        """
        self._n = getattr(self, "_n", 0) + 1
        cliente = APIClient()
        cliente.force_authenticate(self.mesero)
        texto = firmar_pedido(
            "" if es_domicilio else (mesa or self.mesa).codigo, f"Cliente {self._n}",
            [{"plato_id": self.plato.id, "cantidad": cantidad, "observacion": ""}],
            es_domicilio,
        )
        r = cliente.post("/api/pedidos/confirmar/", {"texto": texto}, format="json")
        cuenta = Cuenta.objects.get(pk=r.json()["cuenta_id"])
        cerrar_cuenta(cuenta, self.cajero, caja.id)
        cuenta.refresh_from_db()
        return cuenta

    def test_la_propina_no_esta_dentro_del_vendido(self):
        cuenta = self._vender(self.efectivo)
        r = self.c.get("/api/ventas/").json()
        t = r["totales"]

        self.assertEqual(t["vendido"], cuenta.subtotal_congelado)
        self.assertEqual(t["propinas"], cuenta.propina_congelada)
        self.assertEqual(t["cobrado"], cuenta.total_congelado)
        # Lo cobrado ES la suma de las tres partes; lo vendido NO incluye propina.
        self.assertEqual(t["cobrado"], t["vendido"] + t["impuestos"] + t["propinas"])
        if t["propinas"]:
            self.assertNotEqual(t["vendido"], t["cobrado"],
                                "si hay propina, vendido y cobrado no pueden ser iguales")

    def test_una_venta_anulada_no_suma(self):
        self._vender(self.efectivo)
        anulada = self._vender(self.efectivo)
        antes = self.c.get("/api/ventas/").json()["totales"]

        anular_cuenta(anulada, self.cajero, "se cobro de mas")

        despues = self.c.get("/api/ventas/").json()["totales"]
        self.assertEqual(despues["cantidad"], antes["cantidad"] - 1)
        self.assertEqual(despues["anuladas"], 1)
        self.assertEqual(despues["cobrado"], antes["cobrado"] - anulada.total_congelado)

    def test_las_anuladas_se_ven_si_se_piden_y_nunca_suman(self):
        self._vender(self.efectivo)
        anulada = self._vender(self.efectivo)
        anular_cuenta(anulada, self.cajero, "error de digitacion")

        sin = self.c.get("/api/ventas/").json()
        con = self.c.get("/api/ventas/?anuladas=1").json()

        self.assertEqual(len(sin["ventas"]), 1)
        self.assertEqual(len(con["ventas"]), 2, "mostrarlas es el punto: nada se esconde")
        # Mostrarlas NO cambia ningun total.
        self.assertEqual(sin["totales"], con["totales"])

        fila = next(v for v in con["ventas"] if v["estado"] == "anulada")
        self.assertEqual(fila["motivo_anulacion"], "error de digitacion")
        self.assertEqual(fila["anulada_por"], self.cajero.username)

    def test_el_desglose_por_medio_suma_lo_cobrado(self):
        self._vender(self.efectivo)
        self._vender(self.nequi)
        self._vender(self.nequi)

        r = self.c.get("/api/ventas/").json()
        suma_desglose = sum(m["cobrado"] for m in r["por_medio_pago"])
        self.assertEqual(suma_desglose, r["totales"]["cobrado"])
        self.assertEqual(len(r["por_medio_pago"]), 2)

        nequi = next(m for m in r["por_medio_pago"] if m["medio_pago"] == "Nequi")
        self.assertEqual(nequi["cantidad"], 2)

    def test_filtro_por_medio_de_pago(self):
        self._vender(self.efectivo)
        en_nequi = self._vender(self.nequi)

        r = self.c.get(f"/api/ventas/?medio_pago={self.nequi.id}").json()
        self.assertEqual(r["totales"]["cantidad"], 1)
        self.assertEqual(r["totales"]["cobrado"], en_nequi.total_congelado)

    def test_filtro_por_tipo_mesa_o_domicilio(self):
        self._vender(self.efectivo)
        self._vender(self.efectivo, es_domicilio=True)

        solo_mesa = self.c.get("/api/ventas/?tipo=mesa").json()
        solo_dom = self.c.get("/api/ventas/?tipo=domicilio").json()
        self.assertEqual(solo_mesa["totales"]["cantidad"], 1)
        self.assertEqual(solo_dom["totales"]["cantidad"], 1)
        self.assertTrue(solo_dom["ventas"][0]["es_domicilio"])

    def test_filtro_por_fechas(self):
        self._vender(self.efectivo)

        vacio = self.c.get("/api/ventas/?desde=2020-01-01&hasta=2020-01-31").json()
        self.assertEqual(vacio["totales"]["cantidad"], 0)
        self.assertEqual(vacio["ventas"], [])
        self.assertEqual(vacio["por_medio_pago"], [])

        hoy = timezone.localtime().date().isoformat()
        con = self.c.get(f"/api/ventas/?desde={hoy}&hasta={hoy}").json()
        self.assertEqual(con["totales"]["cantidad"], 1)

    def test_una_cuenta_abierta_no_es_una_venta(self):
        """Nadie pagó nada todavía: no puede aparecer en el historial."""
        cliente = APIClient()
        cliente.force_authenticate(self.mesero)
        texto = firmar_pedido(self.mesa.codigo, "Cliente",
                              [{"plato_id": self.plato.id, "cantidad": 1, "observacion": ""}], False)
        cliente.post("/api/pedidos/confirmar/", {"texto": texto}, format="json")

        r = self.c.get("/api/ventas/?anuladas=1").json()
        self.assertEqual(r["totales"]["cantidad"], 0)
        self.assertEqual(r["ventas"], [])

    def test_quien_no_puede_cobrar_no_ve_el_historial(self):
        cocinero = User.objects.create_user("cocinero_ventas", password="x")
        cocinero.groups.add(Group.objects.get_or_create(name="cocina")[0])
        c = APIClient(); c.force_authenticate(cocinero)
        self.assertEqual(c.get("/api/ventas/").status_code, 403)

    def test_el_detalle_trae_los_precios_congelados(self):
        cuenta = self._vender(self.efectivo, cantidad=2)
        # El precio de hoy cambia; el de la venta NO puede cambiar (SPEC-008).
        self.plato.precio = 99000
        self.plato.save()

        d = self.c.get(f"/api/cuentas/{cuenta.id}/").json()
        renglon = d["pedidos"][0]["detalles"][0]
        self.assertEqual(renglon["precio"], 10000, "el precio congelado no cambia")
        self.assertEqual(renglon["cantidad"], 2)
        self.assertEqual(d["cerrada_por"], self.cajero.username)

    def test_filtro_por_mesa(self):
        otra = Mesa.objects.create(codigo="M-V2", nombre="Mesa dos")
        self._vender(self.efectivo)
        en_otra = self._vender(self.efectivo, mesa=otra)

        r = self.c.get(f"/api/ventas/?mesa={otra.id}").json()
        self.assertEqual(r["totales"]["cantidad"], 1)
        self.assertEqual(r["totales"]["cobrado"], en_otra.total_congelado)

    def test_filtro_por_rango_de_monto(self):
        chica = self._vender(self.efectivo, cantidad=1)     # 10.000 + propina
        grande = self._vender(self.efectivo, cantidad=10)   # 100.000 + propina

        solo_grandes = self.c.get(
            f"/api/ventas/?monto_min={chica.total_congelado + 1}").json()
        self.assertEqual(solo_grandes["totales"]["cantidad"], 1)
        self.assertEqual(solo_grandes["ventas"][0]["total"], grande.total_congelado)

        solo_chicas = self.c.get(
            f"/api/ventas/?monto_max={chica.total_congelado}").json()
        self.assertEqual(solo_chicas["totales"]["cantidad"], 1)

    def test_un_monto_mal_escrito_avisa_en_vez_de_reventar(self):
        r = self.c.get("/api/ventas/?monto_min=mucha%20plata")
        self.assertEqual(r.status_code, 400)
        self.assertIn("número", r.json()["detalle"])

    def test_filtro_por_franja_horaria(self):
        venta = self._vender(self.efectivo)
        hora = timezone.localtime(venta.cerrada_en).hour

        dentro = self.c.get(f"/api/ventas/?hora_desde={hora}&hora_hasta={hora}").json()
        self.assertEqual(dentro["totales"]["cantidad"], 1)

        # Una franja que no incluye esa hora no debe devolverla.
        fuera_desde = (hora + 2) % 24
        fuera_hasta = (hora + 4) % 24
        if fuera_desde <= fuera_hasta:
            fuera = self.c.get(
                f"/api/ventas/?hora_desde={fuera_desde}&hora_hasta={fuera_hasta}").json()
            self.assertEqual(fuera["totales"]["cantidad"], 0)

    def test_la_franja_que_cruza_medianoche_funciona(self):
        """
        "De 10 de la noche a 2 de la mañana" es el horario real de un
        restaurante. Sin tratar el cruce aparte, ese filtro no devolveria
        nada nunca, porque 22 no es menor que 2.
        """
        venta = self._vender(self.efectivo)
        hora = timezone.localtime(venta.cerrada_en).hour

        # Una franja que cruza medianoche y SI incluye la hora de la venta.
        r = self.c.get(f"/api/ventas/?hora_desde={hora}&hora_hasta={(hora - 2) % 24}").json()
        self.assertEqual(r["totales"]["cantidad"], 1,
                         "la franja que cruza medianoche debe incluir su hora de inicio")

    def test_filtro_por_quien_cobro(self):
        self._vender(self.efectivo)

        r = self.c.get(f"/api/ventas/?cobrado_por={self.cajero.id}").json()
        self.assertEqual(r["totales"]["cantidad"], 1)

        otro = User.objects.create_user("otro_cobrador", password="x")
        vacio = self.c.get(f"/api/ventas/?cobrado_por={otro.id}").json()
        self.assertEqual(vacio["totales"]["cantidad"], 0)

    def test_orden_por_monto(self):
        self._vender(self.efectivo, cantidad=1)
        grande = self._vender(self.efectivo, cantidad=10)

        por_monto = self.c.get("/api/ventas/?orden=monto").json()
        self.assertEqual(por_monto["ventas"][0]["total"], grande.total_congelado,
                         "de mayor a menor, la mas grande va primero")

        ascendente = self.c.get("/api/ventas/?orden=monto_asc").json()
        self.assertEqual(ascendente["ventas"][-1]["total"], grande.total_congelado)

    def test_las_opciones_solo_traen_lo_que_tiene_ventas(self):
        """Ofrecer un filtro que no devuelve nada es peor que no ofrecerlo."""
        Mesa.objects.create(codigo="M-VACIA", nombre="Mesa sin ventas")
        self._vender(self.efectivo)

        opciones = self.c.get("/api/ventas/").json()["opciones"]
        nombres = [m["nombre"] for m in opciones["mesas"]]
        self.assertIn(self.mesa.nombre, nombres)
        self.assertNotIn("Mesa sin ventas", nombres)
        self.assertEqual([c["username"] for c in opciones["cobradores"]],
                         [self.cajero.username])

    def test_los_filtros_se_combinan(self):
        otra = Mesa.objects.create(codigo="M-V3", nombre="Mesa tres")
        self._vender(self.efectivo, cantidad=1)
        objetivo = self._vender(self.nequi, cantidad=10, mesa=otra)

        r = self.c.get(
            f"/api/ventas/?mesa={otra.id}&medio_pago={self.nequi.id}"
            f"&monto_min={objetivo.total_congelado}").json()
        self.assertEqual(r["totales"]["cantidad"], 1)
        self.assertEqual(r["totales"]["cobrado"], objetivo.total_congelado)


class TiquetesDeVenta(TransactionTestCase):
    """SPEC-016: numeración por medio, datos congelados y exportación."""

    def setUp(self):
        self.mesero = User.objects.create_user("mesero_tiquete", password="x")
        self.mesero.groups.add(Group.objects.get_or_create(name="mesero")[0])
        self.admin = User.objects.create_user("admin_tiquete", password="x", is_staff=True)
        estacion = Estacion.objects.create(nombre="Cocina tiquete", por_defecto=True)
        categoria = Categoria.objects.create(nombre="Platos tiquete", estacion=estacion)
        self.plato = Plato.objects.create(categoria=categoria, nombre="Plato tiquete", precio=12000)
        self.mesa = Mesa.objects.create(codigo="M-TIQUETE", nombre="Mesa tiquete")
        self.efectivo = Caja.objects.create(nombre="Efectivo tiquete", prefijo="Ef")
        self.nequi = Caja.objects.create(nombre="Nequi tiquete", prefijo="Ne")
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.mesero)
        self.numero = 0

    def vender(self, caja):
        self.numero += 1
        texto = firmar_pedido(
            self.mesa.codigo,
            f"Cliente tiquete {self.numero}",
            [{"plato_id": self.plato.id, "cantidad": 1, "observacion": ""}],
            False,
        )
        respuesta = self.cliente.post("/api/pedidos/confirmar/", {"texto": texto}, format="json")
        cuenta = Cuenta.objects.get(pk=respuesta.json()["cuenta_id"])
        cerrar_cuenta(cuenta, self.admin, caja.id)
        cuenta.refresh_from_db()
        return cuenta

    def test_numera_por_medio_y_reinicia_independientemente(self):
        primero = self.vender(self.efectivo)
        segundo = self.vender(self.efectivo)
        otro_medio = self.vender(self.nequi)
        anio = timezone.localtime().year
        self.assertEqual(primero.numero_tiquete, f"Ef-{anio}-00001")
        self.assertEqual(segundo.numero_tiquete, f"Ef-{anio}-00002")
        self.assertEqual(otro_medio.numero_tiquete, f"Ne-{anio}-00001")

    def test_el_endpoint_devuelve_el_tiquete_con_precio_congelado(self):
        cuenta = self.vender(self.efectivo)
        respuesta = APIClient()
        respuesta.force_authenticate(self.admin)
        datos = respuesta.get(f"/api/ventas/{cuenta.id}/tiquete/").json()
        self.assertEqual(datos["numero"], cuenta.numero_tiquete)
        self.assertEqual(datos["items"][0]["nombre"], "Plato tiquete")
        self.assertEqual(datos["items"][0]["precio"], 12000)

    def test_excel_respeta_el_historial_filtrado(self):
        self.vender(self.efectivo)
        respuesta = APIClient()
        respuesta.force_authenticate(self.admin)
        exportacion = respuesta.get("/api/ventas/exportar/")
        self.assertEqual(exportacion.status_code, 200)
        self.assertEqual(
            exportacion["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(exportacion.content.startswith(b"PK"))

    def test_seleccion_multiple_y_consolidado(self):
        primera = self.vender(self.efectivo)
        segunda = self.vender(self.nequi)
        respuesta = APIClient()
        respuesta.force_authenticate(self.admin)

        tiquetes = respuesta.post(
            "/api/ventas/tiquetes/", {"ids": [primera.id, segunda.id]}, format="json",
        )
        self.assertEqual(tiquetes.status_code, 200)
        self.assertEqual(len(tiquetes.json()["tiquetes"]), 2)

        consolidado = respuesta.get("/api/ventas/consolidado/?agrupar=medio_pago")
        self.assertEqual(consolidado.status_code, 200)
        self.assertEqual(consolidado.json()["total"]["cantidad"], 2)


class ReportesDeVenta(TransactionTestCase):
    """
    SPEC-018. Las reglas que sostienen los cuatro reportes: solo cuentas
    cerradas, atribucion al mesero que TOMO el pedido, y subtotal sin propina.
    """

    def setUp(self):
        self.cajero = User.objects.create_user("cajero_rep", password="x")
        self.cajero.groups.add(Group.objects.get_or_create(name="cajero")[0])
        self.ana = User.objects.create_user("ana", password="x")
        self.ana.groups.add(Group.objects.get_or_create(name="mesero")[0])
        self.beto = User.objects.create_user("beto", password="x")
        self.beto.groups.add(Group.objects.get_or_create(name="mesero")[0])

        estacion = Estacion.objects.create(nombre="Cocina", por_defecto=True)
        cat = Categoria.objects.create(nombre="Platos", estacion=estacion)
        self.arroz = Plato.objects.create(categoria=cat, nombre="Arroz", precio=10000)
        self.sopa = Plato.objects.create(categoria=cat, nombre="Sopa", precio=5000)
        self.mesa = Mesa.objects.create(codigo="M-R", nombre="Mesa reporte")
        self.efectivo = Caja.objects.create(nombre="Efectivo")

        self.c = APIClient()
        self.c.force_authenticate(self.cajero)
        self._n = 0

    def _pedir(self, mesero, plato, cantidad=1):
        """Confirma un pedido a nombre de `mesero`. Devuelve la cuenta."""
        self._n += 1
        cli = APIClient()
        cli.force_authenticate(mesero)
        texto = firmar_pedido(
            self.mesa.codigo, f"C{self._n}",
            [{"plato_id": plato.id, "cantidad": cantidad, "observacion": ""}], False)
        r = cli.post("/api/pedidos/confirmar/", {"texto": texto}, format="json")
        return Cuenta.objects.get(pk=r.json()["cuenta_id"])

    def test_una_cuenta_anulada_no_suma_en_ningun_reporte(self):
        from ventas.reportes import todos

        cuenta = self._pedir(self.ana, self.arroz, 3)
        cerrar_cuenta(cuenta, self.cajero, self.efectivo.id)
        anular_cuenta(cuenta, self.cajero, "el cliente se arrepintio")

        r = todos()
        self.assertEqual(r["resumen"]["ventas"], 0)
        self.assertEqual(r["resumen"]["cobrado"], 0)
        self.assertEqual(r["productos"], [])
        self.assertEqual(r["meseros"], [])

    def test_una_mesa_con_dos_meseros_reparte_la_venta(self):
        """
        Lo que mas importa del reporte por mesero: atribuir la cuenta completa
        a quien cobro seria mentir sobre el trabajo del otro.
        """
        from ventas.reportes import ventas_por_mesero

        cuenta = self._pedir(self.ana, self.arroz, 2)      # 20.000, de Ana
        self._pedir(self.beto, self.sopa, 1)               # 5.000, de Beto, misma mesa
        cuenta.refresh_from_db()
        cerrar_cuenta(cuenta, self.cajero, self.efectivo.id)

        por_mesero = {m["mesero"]: m["vendido"] for m in ventas_por_mesero()}
        self.assertEqual(por_mesero, {"ana": 20000, "beto": 5000})

    def test_el_reporte_por_mesero_no_incluye_propina(self):
        from ventas.reportes import ventas_por_mesero

        cuenta = self._pedir(self.ana, self.arroz, 1)
        cerrar_cuenta(cuenta, self.cajero, self.efectivo.id)
        cuenta.refresh_from_db()

        vendido = ventas_por_mesero()[0]["vendido"]
        self.assertEqual(vendido, cuenta.subtotal_congelado)
        if cuenta.propina_congelada:
            self.assertLess(vendido, cuenta.total_congelado,
                            "la propina no puede estar dentro de lo vendido")

    def test_productos_agrupa_por_el_nombre_con_que_se_vendio(self):
        """
        Si un plato se renombra, lo vendido con el nombre viejo se vendio con
        ese nombre. Agrupar por el plato de hoy reescribiria la historia.
        """
        from ventas.reportes import productos_mas_vendidos

        cuenta = self._pedir(self.ana, self.arroz, 4)
        cerrar_cuenta(cuenta, self.cajero, self.efectivo.id)

        self.arroz.nombre = "Arroz con pollo"
        self.arroz.save()

        top = productos_mas_vendidos()
        self.assertEqual(top[0]["nombre"], "Arroz", "debe conservar el nombre de la venta")
        self.assertEqual(top[0]["cantidad"], 4)
        self.assertEqual(top[0]["total"], 40000)

    def test_las_horas_traen_las_24_aunque_esten_en_cero(self):
        """Un grafico con huecos donde no hubo ventas se lee mal."""
        from ventas.reportes import demanda_por_dia_semana, demanda_por_hora

        cuenta = self._pedir(self.ana, self.arroz, 1)
        cerrar_cuenta(cuenta, self.cajero, self.efectivo.id)

        horas = demanda_por_hora()
        self.assertEqual(len(horas), 24)
        self.assertEqual([h["hora"] for h in horas], list(range(24)))
        self.assertEqual(sum(h["ventas"] for h in horas), 1)

        dias = demanda_por_dia_semana()
        self.assertEqual(len(dias), 7)
        self.assertEqual(dias[0]["dia"], "Lunes", "la semana arranca el lunes")

    def test_el_ticket_promedio_sale_de_las_cuentas_cobradas(self):
        from ventas.reportes import resumen

        c1 = self._pedir(self.ana, self.arroz, 1)
        cerrar_cuenta(c1, self.cajero, self.efectivo.id)
        c2 = self._pedir(self.ana, self.arroz, 3)
        cerrar_cuenta(c2, self.cajero, self.efectivo.id)
        c1.refresh_from_db(); c2.refresh_from_db()

        r = resumen()
        self.assertEqual(r["ventas"], 2)
        self.assertEqual(r["cobrado"], c1.total_congelado + c2.total_congelado)
        self.assertEqual(r["ticket_promedio"],
                         round((c1.total_congelado + c2.total_congelado) / 2))

    def test_un_rango_sin_ventas_devuelve_todo_vacio_sin_reventar(self):
        from ventas.reportes import todos

        cuenta = self._pedir(self.ana, self.arroz, 1)
        cerrar_cuenta(cuenta, self.cajero, self.efectivo.id)

        r = todos(desde="2020-01-01", hasta="2020-01-31")
        self.assertEqual(r["resumen"]["ventas"], 0)
        self.assertEqual(r["resumen"]["ticket_promedio"], 0)
        self.assertEqual(r["productos"], [])
        self.assertEqual(r["por_dia"], [])
        self.assertEqual(len(r["por_hora"]), 24, "las horas siempre son 24")

    def test_quien_no_puede_cobrar_no_ve_los_reportes(self):
        cocinero = User.objects.create_user("cocinero_rep", password="x")
        cocinero.groups.add(Group.objects.get_or_create(name="cocina")[0])
        c = APIClient(); c.force_authenticate(cocinero)
        self.assertEqual(c.get("/api/reportes/").status_code, 403)

    def test_el_endpoint_trae_los_cuatro_reportes_en_una_llamada(self):
        cuenta = self._pedir(self.ana, self.arroz, 2)
        cerrar_cuenta(cuenta, self.cajero, self.efectivo.id)

        r = self.c.get("/api/reportes/")
        self.assertEqual(r.status_code, 200)
        for clave in ("resumen", "productos", "meseros", "por_dia", "por_hora", "por_dia_semana"):
            self.assertIn(clave, r.json())


class ActivosLiquidos(TransactionTestCase):
    """
    SPEC-020. Cuanta plata hay, donde esta, y que pasa cuando entra o sale.

    El caso que mas importa aqui es el cierre del turno: hasta esta spec, el
    efectivo se contaba pero **nunca salia del libro**, asi que el saldo de
    Efectivo crecia dia tras dia como si nadie hubiera sacado la plata del
    cajon.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser("admin_act", password="x")
        self.cajero = User.objects.create_user("cajero_act", password="x")
        self.cajero.groups.add(Group.objects.get_or_create(name="cajero")[0])

        self.efectivo = Caja.objects.create(nombre="Efectivo", tipo=Caja.EFECTIVO)
        self.banco = Caja.objects.create(nombre="Bancolombia", tipo=Caja.BANCO)
        # `get_or_create` y no `create`: la migracion de datos ya siembra las
        # categorias de arranque, y `TransactionTestCase` vacia las tablas
        # entre pruebas — asi que "Insumos" existe o no segun el orden en que
        # corran. Con esto la prueba no depende de eso.
        self.insumos, _ = CategoriaGasto.objects.get_or_create(nombre="Insumos")

        self.c = APIClient()
        self.c.force_authenticate(self.admin)

    # ---- Saldo de arranque -------------------------------------------------

    def test_el_saldo_de_arranque_queda_como_movimiento(self):
        """
        Y no como campo: el saldo sigue siendo la suma del libro, sin
        excepciones (SPEC-014, regla 1).
        """
        fijar_saldo_inicial(self.banco, 5_000_000, self.admin)

        self.assertEqual(self.banco.saldo(), 5_000_000)
        mov = self.banco.movimientos.get()
        self.assertEqual(mov.concepto, MovimientoCaja.SALDO_INICIAL)
        self.assertEqual(mov.tipo, MovimientoCaja.INGRESO)

    def test_el_saldo_de_arranque_no_se_puede_fijar_dos_veces(self):
        fijar_saldo_inicial(self.banco, 5_000_000, self.admin)
        with self.assertRaises(OperacionInvalida):
            fijar_saldo_inicial(self.banco, 9_000_000, self.admin)
        self.assertEqual(self.banco.saldo(), 5_000_000, "el primero manda")

    def test_no_se_declara_el_arranque_de_una_caja_que_ya_tiene_movimientos(self):
        """
        La trampa que salio al ver la pantalla: el boton mostraba "con cuanto
        arranco" en una caja con 1.790.800 de historia. Lo que el
        administrador iba a escribir era el saldo que veia — y se habria
        SUMADO, dejando la caja con el doble. Para eso esta el ajuste.
        """
        # Un ingreso cualquiera basta para que la caja deje de estar vacia.
        registrar_movimiento(self.banco, MovimientoCaja.INGRESO, 50_000, self.cajero)

        with self.assertRaises(OperacionInvalida):
            fijar_saldo_inicial(self.banco, 5_000_000, self.admin)

    def test_dos_saldos_de_arranque_a_la_vez_solo_dejan_uno(self):
        """
        Mismo patron de ADR-008: leer, decidir y escribir sin bloquear la fila
        deja pasar a los dos. Aqui el resultado seria una caja que arranca con
        el doble de plata que nunca tuvo.
        """
        def fijar(_):
            try:
                fijar_saldo_inicial(self.banco, 5_000_000, self.admin)
                return "ok"
            except OperacionInvalida:
                return "rechazado"

        resultados = en_paralelo(2, fijar)

        self.assertEqual(sorted(resultados), ["ok", "rechazado"])
        self.assertEqual(self.banco.saldo(), 5_000_000)
        self.assertEqual(
            self.banco.movimientos.filter(
                concepto=MovimientoCaja.SALDO_INICIAL).count(), 1)

    # ---- Gastos ------------------------------------------------------------

    def test_un_gasto_baja_el_saldo_y_guarda_su_categoria(self):
        fijar_saldo_inicial(self.efectivo, 500_000, self.admin)
        registrar_gasto(self.efectivo, 120_000, self.insumos, self.cajero,
                        descripcion="Pollo del jueves")

        self.assertEqual(self.efectivo.saldo(), 380_000)
        mov = self.efectivo.movimientos.get(concepto=MovimientoCaja.GASTO)
        self.assertEqual(mov.tipo, MovimientoCaja.EGRESO)
        self.assertEqual(mov.categoria_id, self.insumos.id)
        self.assertEqual(mov.descripcion, "Pollo del jueves",
                         "la categoria NO reemplaza a la descripcion")

    def test_un_gasto_sin_categoria_no_se_registra(self):
        with self.assertRaises(OperacionInvalida):
            registrar_gasto(self.efectivo, 50_000, None, self.cajero)
        self.assertEqual(self.efectivo.movimientos.count(), 0)

    def test_una_categoria_con_gastos_no_se_puede_borrar(self):
        """
        `PROTECT`: borrarla dejaria movimientos historicos sin explicacion de
        en que se fue esa plata.
        """
        fijar_saldo_inicial(self.efectivo, 100_000, self.admin)
        registrar_gasto(self.efectivo, 50_000, self.insumos, self.cajero)
        with self.assertRaises(ProtectedError):
            self.insumos.delete()

    def test_dos_gastos_a_la_vez_no_descuadran_el_saldo(self):
        fijar_saldo_inicial(self.efectivo, 500_000, self.admin)

        def gastar(_):
            registrar_gasto(self.efectivo, 100_000, self.insumos, self.cajero)

        en_paralelo(3, gastar)

        self.assertEqual(self.efectivo.saldo(), 200_000,
                         "500.000 menos tres gastos de 100.000")

    # ---- Que no salga mas de lo que hay ------------------------------------

    def test_no_se_puede_gastar_mas_de_lo_que_hay(self):
        """
        Reportado por el autor el 2026-09-07: se podia registrar un gasto mas
        grande que el saldo y la caja quedaba en NEGATIVO. Un saldo negativo no
        significa nada — no existe un cajon con menos cero pesos.
        """
        fijar_saldo_inicial(self.efectivo, 100_000, self.admin)

        with self.assertRaises(OperacionInvalida):
            registrar_gasto(self.efectivo, 150_000, self.insumos, self.cajero)

        self.assertEqual(self.efectivo.saldo(), 100_000, "no se movio nada")

    def test_gastar_exactamente_lo_que_hay_si_se_puede(self):
        """El limite es "mas de lo que hay", no "todo lo que hay"."""
        fijar_saldo_inicial(self.efectivo, 100_000, self.admin)
        registrar_gasto(self.efectivo, 100_000, self.insumos, self.cajero)
        self.assertEqual(self.efectivo.saldo(), 0)

    def test_no_se_puede_trasladar_mas_de_lo_que_hay(self):
        fijar_saldo_inicial(self.efectivo, 100_000, self.admin)

        with self.assertRaises(OperacionInvalida):
            trasladar(self.efectivo, self.banco, 150_000, self.cajero)

        self.assertEqual(self.efectivo.saldo(), 100_000)
        self.assertEqual(self.banco.saldo(), 0, "el destino tampoco recibio nada")

    def test_dos_gastos_simultaneos_no_dejan_la_caja_en_negativo(self):
        """
        La carrera de ADR-008 aplicada a esto: con 150.000 en caja, dos gastos
        de 100.000 a la vez leerian los dos "alcanza", pasarian los dos, y la
        caja terminaria en -50.000. Solo uno debe entrar.
        """
        fijar_saldo_inicial(self.efectivo, 150_000, self.admin)

        def gastar(_):
            try:
                registrar_gasto(self.efectivo, 100_000, self.insumos, self.cajero)
                return "ok"
            except OperacionInvalida:
                return "rechazado"

        resultados = en_paralelo(2, gastar)

        self.assertEqual(sorted(resultados), ["ok", "rechazado"])
        self.assertEqual(self.efectivo.saldo(), 50_000)

    def test_el_mensaje_dice_que_falta_declarar_el_arranque(self):
        """
        Una caja en cero por falta de saldo inicial y una caja sin plata se ven
        igual en pantalla. El mensaje tiene que distinguirlas, o el cajero se
        queda sin saber que hacer.
        """
        with self.assertRaises(OperacionInvalida) as e:
            registrar_gasto(self.banco, 50_000, self.insumos, self.cajero)
        self.assertIn("arranc", str(e.exception).lower())

    def test_la_api_rechaza_un_egreso_mayor_que_el_saldo(self):
        fijar_saldo_inicial(self.efectivo, 100_000, self.admin)

        r = self.c.post("/api/movimientos/", {
            "caja": self.efectivo.id, "tipo": "egreso", "monto": 150_000,
        }, format="json")

        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.efectivo.saldo(), 100_000)

    # ---- Ajuste contra el extracto ----------------------------------------

    def test_ajustar_registra_la_diferencia_como_su_propio_movimiento(self):
        fijar_saldo_inicial(self.banco, 1_000_000, self.admin)
        ajustar_saldo(self.banco, 950_000, self.admin, "Comision del banco")

        self.assertEqual(self.banco.saldo(), 950_000)
        mov = self.banco.movimientos.get(concepto=MovimientoCaja.DIFERENCIA_ARQUEO)
        self.assertEqual(mov.tipo, MovimientoCaja.EGRESO)
        self.assertEqual(mov.monto, 50_000)
        self.assertIn("Comision del banco", mov.descripcion)

    def test_ajustar_hacia_arriba_registra_un_ingreso(self):
        fijar_saldo_inicial(self.banco, 1_000_000, self.admin)
        ajustar_saldo(self.banco, 1_020_000, self.admin, "Rendimientos")

        self.assertEqual(self.banco.saldo(), 1_020_000)
        self.assertEqual(
            self.banco.movimientos.get(
                concepto=MovimientoCaja.DIFERENCIA_ARQUEO).tipo,
            MovimientoCaja.INGRESO)

    def test_ajustar_sin_motivo_falla(self):
        fijar_saldo_inicial(self.banco, 1_000_000, self.admin)
        with self.assertRaises(OperacionInvalida):
            ajustar_saldo(self.banco, 950_000, self.admin, "")

    def test_ajustar_al_mismo_saldo_no_crea_movimiento(self):
        fijar_saldo_inicial(self.banco, 1_000_000, self.admin)
        ajustar_saldo(self.banco, 1_000_000, self.admin, "Cuadrado")
        self.assertEqual(self.banco.movimientos.count(), 1, "solo el de arranque")

    # ---- El cierre diario del efectivo ------------------------------------

    def _turno_con_efectivo(self, monto):
        """Un turno abierto con `monto` de fondo, para tener que retirar algo."""
        return abrir_turno(self.cajero, fondos={self.efectivo.id: monto})

    def test_al_cerrar_el_efectivo_sale_y_queda_la_base(self):
        """
        El corazon de SPEC-020. Antes de esto el efectivo nunca salia del
        libro y su saldo crecia para siempre.
        """
        turno = self._turno_con_efectivo(200_000)

        cerrar_turno(turno, efectivo_contado=200_000, autor=self.cajero,
                     base_dejada=50_000)

        self.assertEqual(self.efectivo.saldo(), 50_000,
                         "el cajon queda en la base declarada")
        retiro = self.efectivo.movimientos.get(concepto=MovimientoCaja.RETIRO_CIERRE)
        self.assertEqual(retiro.monto, 150_000)
        self.assertEqual(retiro.tipo, MovimientoCaja.EGRESO)

    def test_al_cerrar_las_cajas_de_banco_no_se_tocan(self):
        fijar_saldo_inicial(self.banco, 3_000_000, self.admin)
        turno = self._turno_con_efectivo(200_000)

        cerrar_turno(turno, efectivo_contado=200_000, autor=self.cajero,
                     base_dejada=0)

        self.assertEqual(self.banco.saldo(), 3_000_000,
                         "el banco no se cuenta ni se reinicia")

    def test_consignar_el_efectivo_lo_pasa_al_banco(self):
        turno = self._turno_con_efectivo(200_000)

        cerrar_turno(turno, efectivo_contado=200_000, autor=self.cajero,
                     base_dejada=50_000, destino_efectivo=self.banco.id)

        self.assertEqual(self.efectivo.saldo(), 50_000)
        self.assertEqual(self.banco.saldo(), 150_000,
                         "lo retirado entro al banco, no desaparecio")

    def test_el_descuadre_queda_escrito_con_su_motivo(self):
        """
        No se disimula: movimiento propio, con autor y motivo. El saldo vuelve
        a coincidir con la realidad Y queda constando que falto plata.
        """
        turno = self._turno_con_efectivo(200_000)

        cerrar_turno(turno, efectivo_contado=190_000, autor=self.cajero,
                     base_dejada=0, motivo_diferencia="Faltaron 10 mil, no se de donde")

        diferencia = self.efectivo.movimientos.get(
            concepto=MovimientoCaja.DIFERENCIA_ARQUEO)
        self.assertEqual(diferencia.monto, 10_000)
        self.assertEqual(diferencia.tipo, MovimientoCaja.EGRESO)
        self.assertEqual(diferencia.autor_id, self.cajero.id)
        self.assertIn("Faltaron 10 mil", diferencia.descripcion)
        self.assertEqual(self.efectivo.saldo(), 0, "el libro cuadra con el cajon")

    def test_cerrar_con_descuadre_y_sin_motivo_falla(self):
        turno = self._turno_con_efectivo(200_000)
        with self.assertRaises(OperacionInvalida):
            cerrar_turno(turno, efectivo_contado=190_000, autor=self.cajero,
                         base_dejada=0)
        turno.refresh_from_db()
        self.assertEqual(turno.estado, Turno.ABIERTO, "no se cerro a medias")

    def test_cerrar_sin_declarar_base_no_retira_nada(self):
        """
        El caso de "solo cierro mi turno, la caja del dia la cierra otro":
        quedan companeros vendiendo y el cajon no se puede vaciar todavia.
        """
        turno = self._turno_con_efectivo(200_000)

        cerrar_turno(turno, efectivo_contado=200_000, autor=self.cajero)

        self.assertEqual(self.efectivo.saldo(), 200_000, "la plata sigue en el cajon")
        self.assertFalse(
            self.efectivo.movimientos.filter(
                concepto=MovimientoCaja.RETIRO_CIERRE).exists())

    def test_no_se_puede_dejar_de_base_mas_de_lo_contado(self):
        turno = self._turno_con_efectivo(200_000)
        with self.assertRaises(OperacionInvalida):
            cerrar_turno(turno, efectivo_contado=200_000, autor=self.cajero,
                         base_dejada=300_000)

    # ---- La API ------------------------------------------------------------

    def test_los_activos_traen_cada_caja_y_los_totales(self):
        fijar_saldo_inicial(self.efectivo, 300_000, self.admin)
        fijar_saldo_inicial(self.banco, 2_000_000, self.admin)

        r = self.c.get("/api/activos/").json()

        self.assertEqual(r["total"], 2_300_000)
        self.assertEqual(r["total_efectivo"], 300_000)
        self.assertEqual(r["total_banco"], 2_000_000)
        self.assertEqual(len(r["cajas"]), 2)
        una = next(c for c in r["cajas"] if c["nombre"] == "Efectivo")
        self.assertEqual(una["saldo"], 300_000)
        self.assertEqual(una["tipo"], Caja.EFECTIVO)

    def test_el_saldo_de_cada_caja_cuadra_con_su_libro(self):
        """
        La comprobacion que sostiene todo: si estos dos numeros se separan, el
        modulo entero deja de significar algo.
        """
        fijar_saldo_inicial(self.efectivo, 500_000, self.admin)
        registrar_gasto(self.efectivo, 80_000, self.insumos, self.cajero)
        trasladar(self.efectivo, self.banco, 200_000, self.cajero)

        r = self.c.get("/api/activos/").json()
        libro = self.c.get(f"/api/movimientos/?caja={self.efectivo.id}").json()

        self.assertEqual(
            next(c for c in r["cajas"] if c["id"] == self.efectivo.id)["saldo"],
            libro["totales"]["neto"])

    def test_quien_no_puede_cobrar_no_ve_los_activos(self):
        cocinero = User.objects.create_user("cocinero_act", password="x")
        cocinero.groups.add(Group.objects.get_or_create(name="cocina")[0])
        c = APIClient(); c.force_authenticate(cocinero)
        self.assertEqual(c.get("/api/activos/").status_code, 403)

    def test_el_cajero_registra_gastos_pero_NO_ajusta_ni_fija_arranque(self):
        """
        Registrar lo del dia a dia es tarea de caja. Reescribir un saldo
        contra el extracto es una decision administrativa.
        """
        fijar_saldo_inicial(self.efectivo, 200_000, self.admin)
        c = APIClient(); c.force_authenticate(self.cajero)

        gasto = c.post("/api/movimientos/", {
            "caja": self.efectivo.id, "tipo": "egreso", "monto": 50_000,
            "concepto": MovimientoCaja.GASTO, "categoria": self.insumos.id,
        }, format="json")
        self.assertEqual(gasto.status_code, 201)

        self.assertEqual(c.post(
            f"/api/cajas/{self.banco.id}/saldo-inicial/",
            {"monto": 1_000_000}, format="json").status_code, 403)
        self.assertEqual(c.post(
            f"/api/cajas/{self.banco.id}/ajustar/",
            {"saldo_real": 10, "motivo": "porque si"}, format="json").status_code, 403)

    def test_la_api_rechaza_un_gasto_sin_categoria(self):
        r = self.c.post("/api/movimientos/", {
            "caja": self.efectivo.id, "tipo": "egreso", "monto": 50_000,
            "concepto": MovimientoCaja.GASTO,
        }, format="json")
        self.assertEqual(r.status_code, 400)


# ============================================================================
# SPEC-024 — Búsqueda en el libro e historial de turnos
# ============================================================================

class BaseBusqueda(TransactionTestCase):
    def setUp(self):
        self.admin = User.objects.create_user("busq_admin", password="x", is_staff=True)
        self.cajero = User.objects.create_user("busq_cajero", password="x")
        self.cajero.groups.add(Group.objects.get_or_create(name="cajero")[0])
        self.ana = User.objects.create_user("ana", password="x")
        self.beto = User.objects.create_user("beto", password="x")
        self.cocina = User.objects.create_user("busq_cocina", password="x")
        self.cocina.groups.add(Group.objects.get_or_create(name="cocina")[0])
        self.efectivo = Caja.objects.create(nombre="Efectivo", tipo=Caja.EFECTIVO, prefijo="Ef")
        self.banco = Caja.objects.create(nombre="Nequi", tipo=Caja.BANCO, prefijo="Nq")

    def api(self, usuario):
        c = APIClient()
        c.force_authenticate(usuario)
        return c

    def mov(self, monto, tipo=MovimientoCaja.INGRESO, caja=None, concepto=MovimientoCaja.OTRO,
            descripcion="", autor=None, turno=None, cuenta=None):
        return MovimientoCaja.objects.create(
            caja=caja or self.efectivo, tipo=tipo, concepto=concepto, monto=monto,
            descripcion=descripcion, autor=autor or self.cajero, turno=turno, cuenta=cuenta)


class BusquedaLibro(BaseBusqueda):
    def libro(self, **params):
        r = self.api(self.cajero).get("/api/movimientos/", params)
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def montos(self, **params):
        return sorted(m["monto"] for m in self.libro(**params)["movimientos"])

    def test_valor_exacto(self):
        for monto in (99_999, 100_000, 100_001):
            self.mov(monto)
        self.assertEqual(self.montos(monto=100000), [100_000])

    def test_rango_inclusivo_y_extremos_sueltos(self):
        for monto in (49_999, 50_000, 150_000, 150_001):
            self.mov(monto)
        self.assertEqual(self.montos(monto_min=50000, monto_max=150000), [50_000, 150_000])
        self.assertEqual(self.montos(monto_min=150000), [150_000, 150_001])
        self.assertEqual(self.montos(monto_max=50000), [49_999, 50_000])

    def test_un_valor_mal_escrito_se_explica(self):
        r = self.api(self.cajero).get("/api/movimientos/", {"monto": "cien"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("cien", r.json()["detalle"])

    def test_texto_sin_mayusculas_ni_tildes(self):
        self.mov(10_000, descripcion="Pago al Proveedor de gas", tipo=MovimientoCaja.EGRESO)
        self.mov(4_000, descripcion="Café para la cocina", tipo=MovimientoCaja.EGRESO)
        self.mov(5_000, descripcion="Otra cosa", tipo=MovimientoCaja.EGRESO)
        self.assertEqual(self.montos(q="proveedor"), [10_000])
        self.assertEqual(self.montos(q="cafe"), [4_000])

    def test_numero_de_tiquete_en_sus_tres_formas(self):
        cuenta = Cuenta.objects.create(
            estado=Cuenta.CERRADA, medio_pago=self.efectivo, tiquete_numero=123, tiquete_anio=2026,
            total_congelado=100_000, cerrada_en=timezone.now(), cerrada_por=self.cajero)
        self.mov(100_000, concepto=MovimientoCaja.VENTA, cuenta=cuenta)
        self.mov(80_000, concepto=MovimientoCaja.VENTA)
        for texto in ("Ef-2026-00123", "00123", "123"):
            self.assertEqual(self.montos(q=texto), [100_000], texto)
        venta = self.libro(q="123")["movimientos"][0]
        self.assertEqual(venta["tiquete"], "Ef-2026-00123")

    def test_concepto_y_quien_registro(self):
        self.mov(1_000, concepto=MovimientoCaja.GASTO, tipo=MovimientoCaja.EGRESO, autor=self.ana)
        self.mov(2_000, concepto=MovimientoCaja.VENTA, autor=self.beto)
        self.assertEqual(self.montos(concepto=MovimientoCaja.GASTO), [1_000])
        self.assertEqual(self.montos(autor=self.beto.id), [2_000])
        nombres = {p["username"] for p in self.libro()["personas"]}
        self.assertEqual(nombres, {"ana", "beto"})

    def test_totales_del_filtro_completo_y_cargar_mas(self):
        MovimientoCaja.objects.bulk_create([
            MovimientoCaja(caja=self.efectivo, tipo=MovimientoCaja.INGRESO, monto=1_000,
                           autor=self.cajero, concepto=MovimientoCaja.OTRO)
            for _ in range(250)
        ])
        primera = self.libro()
        self.assertEqual(len(primera["movimientos"]), 100)
        self.assertEqual(primera["totales"]["cantidad"], 250)
        self.assertEqual(primera["totales"]["ingresos"], 250_000)
        self.assertTrue(primera["hay_mas"])

        vistos = {m["id"] for m in primera["movimientos"]}
        for desde in (100, 200):
            vistos |= {m["id"] for m in self.libro(desde_fila=desde)["movimientos"]}
        self.assertEqual(len(vistos), 250)
        self.assertFalse(self.libro(desde_fila=200)["hay_mas"])

    def test_quien_no_puede_cobrar_no_busca(self):
        self.assertEqual(self.api(self.cocina).get("/api/movimientos/", {"monto": 1}).status_code, 403)


class HistorialTurnos(BaseBusqueda):
    def turno(self, responsable, esperado, contado, dias_atras=0, cerrado_por=None):
        """Un turno cuyo efectivo esperado es `esperado` y del que se contó `contado`."""
        t = Turno.objects.create(
            responsable=responsable,
            estado=Turno.CERRADO if contado is not None else Turno.ABIERTO,
            efectivo_contado=contado, cerrado_por=cerrado_por,
            cerrado_en=timezone.now() if contado is not None else None,
        )
        Turno.objects.filter(pk=t.pk).update(
            abierto_en=timezone.now() - timezone.timedelta(days=dias_atras))
        if esperado:
            self.mov(esperado, turno=t)
        # Lo que entra por otra caja no cuenta para el cuadre del efectivo.
        self.mov(7_777, caja=self.banco, turno=t)
        return t

    def historial(self, **params):
        r = self.api(self.admin).get("/api/turnos/", params)
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def ids(self, **params):
        return {t["id"] for t in self.historial(**params)["turnos"]}

    def test_la_diferencia_filtrada_es_la_misma_que_muestra_la_tabla(self):
        t = self.turno(self.ana, 100_000, 85_000)
        fila = self.historial()["turnos"][0]
        self.assertEqual(fila["cuadre"]["diferencia"], cuadre_de(t)["diferencia"])
        self.assertEqual(fila["cuadre"]["diferencia"], -15_000)
        self.assertIn(t.id, self.ids(cuadre="falto"))

    def test_filtros_de_cuadre(self):
        cuadro = self.turno(self.ana, 50_000, 50_000)
        falto = self.turno(self.ana, 50_000, 35_000)
        sobro = self.turno(self.beto, 50_000, 60_000)
        # Abierto sin conteo. Se abre a nombre de otra persona porque la base
        # no deja dos turnos abiertos de la misma.
        abierto = self.turno(self.cajero, 50_000, None)
        self.assertEqual(self.ids(cuadre="cuadro"), {cuadro.id})
        self.assertEqual(self.ids(cuadre="falto"), {falto.id})
        self.assertEqual(self.ids(cuadre="sobro"), {sobro.id})
        self.assertEqual(self.ids(cuadre="sin_contar"), {abierto.id})

    def test_diferencia_minima_en_valor_absoluto(self):
        grande = self.turno(self.ana, 50_000, 35_000)
        justo = self.turno(self.ana, 50_000, 60_000)
        chico = self.turno(self.ana, 50_000, 45_000)
        self.assertEqual(self.ids(diferencia_min=10000), {grande.id, justo.id})
        self.assertNotIn(chico.id, self.ids(diferencia_min=10000))

    def test_personas_estado_y_fechas(self):
        de_ana = self.turno(self.ana, 10_000, 10_000, dias_atras=10)
        de_beto = self.turno(self.beto, 10_000, 10_000, dias_atras=1, cerrado_por=self.ana)
        abierto = self.turno(self.beto, 0, None)
        self.assertEqual(self.ids(responsable=self.ana.id), {de_ana.id})
        self.assertEqual(self.ids(cerrado_por=self.ana.id), {de_beto.id})
        self.assertEqual(self.ids(estado="abierto"), {abierto.id})
        hace_3 = (timezone.localdate() - timezone.timedelta(days=3)).isoformat()
        self.assertEqual(self.ids(desde=hace_3), {de_beto.id, abierto.id})
        cerradores = self.historial()["personas"]["cerradores"]
        self.assertEqual({p["username"] for p in cerradores}, {"ana"})

    def test_orden_por_mayor_faltante_y_resumen_del_filtro(self):
        self.turno(self.ana, 50_000, 45_000)
        peor = self.turno(self.ana, 90_000, 40_000)
        self.turno(self.beto, 10_000, 12_500)
        datos = self.historial(orden="faltante")
        self.assertEqual(datos["turnos"][0]["id"], peor.id)
        self.assertEqual(datos["resumen"], {
            "total": 3, "con_faltante": 2, "faltante": 55_000, "con_sobrante": 1, "sobrante": 2_500,
        })

    def test_el_turno_101_se_puede_ver_y_cargar_mas(self):
        viejo = self.turno(self.ana, 0, 0, dias_atras=400)
        for i in range(105):
            self.turno(self.beto, 0, 0, dias_atras=i)
        primera = self.historial()
        self.assertEqual(len(primera["turnos"]), 25)
        self.assertEqual(primera["resumen"]["total"], 106)
        self.assertTrue(primera["hay_mas"])
        self.assertEqual(self.ids(responsable=self.ana.id), {viejo.id})
        self.assertIn(viejo.id, self.ids(desde_fila=100, limite=25))

    def test_el_cajero_no_ve_el_historial(self):
        self.assertEqual(self.api(self.cajero).get("/api/turnos/").status_code, 403)


class Spec025Vueltos(BaseConcurrencia):
    """SPEC-025, 2026-09-16: vuelto opcional, solo en efectivo."""

    def setUp(self):
        super().setUp()
        # `BaseConcurrencia.caja` es de tipo Banco por defecto; el vuelto
        # necesita una caja explícitamente Efectivo.
        self.efectivo = Caja.objects.create(nombre="Efectivo vuelto", tipo=Caja.EFECTIVO)

    def cerrar(self, cuenta, medio, recibido=None):
        cuerpo = {"medio_pago": medio.id}
        if recibido is not None:
            cuerpo["recibido_efectivo"] = recibido
        c = APIClient()
        c.force_authenticate(self.admin)
        return c.post(f"/api/cuentas/{cuenta.id}/cerrar/", cuerpo, format="json")

    def test_vuelto_se_calcula_y_se_guarda(self):
        self.confirmar(self.qr("Cliente"))
        cuenta = Cuenta.objects.get(mesa=self.mesa, estado=Cuenta.ABIERTA)
        total = calcular_totales(cuenta)["total"]
        r = self.cerrar(cuenta, self.efectivo, recibido=total + 10_000)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["vuelto_efectivo"], 10_000)
        cuenta.refresh_from_db()
        self.assertEqual(cuenta.recibido_efectivo, total + 10_000)
        self.assertEqual(cuenta.vuelto_efectivo, 10_000)

    def test_pagar_de_menos_se_rechaza_sin_cerrar_la_cuenta(self):
        self.confirmar(self.qr("Cliente"))
        cuenta = Cuenta.objects.get(mesa=self.mesa, estado=Cuenta.ABIERTA)
        total = calcular_totales(cuenta)["total"]
        r = self.cerrar(cuenta, self.efectivo, recibido=total - 5_000)
        self.assertEqual(r.status_code, 400)
        self.assertIn("Faltan", r.json()["detalle"])
        cuenta.refresh_from_db()
        self.assertEqual(cuenta.estado, Cuenta.ABIERTA)

    def test_sin_recibido_cobra_igual_sin_vuelto(self):
        self.confirmar(self.qr("Cliente"))
        cuenta = Cuenta.objects.get(mesa=self.mesa, estado=Cuenta.ABIERTA)
        r = self.cerrar(cuenta, self.efectivo)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIsNone(r.json()["vuelto_efectivo"])

    def test_recibido_se_ignora_en_un_medio_que_no_es_efectivo(self):
        self.confirmar(self.qr("Cliente"))
        cuenta = Cuenta.objects.get(mesa=self.mesa, estado=Cuenta.ABIERTA)
        r = self.cerrar(cuenta, self.caja, recibido=999_999_999)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIsNone(r.json()["vuelto_efectivo"])


class Spec025VueltosEnHistorial(BaseConcurrencia):
    """
    El detalle de Ventas toma sus datos de la lista de /ventas/, no de
    /cuentas/ (Historial de Ventas construye el detalle a partir de la fila
    de la lista). Un campo que solo se agregue a /cuentas/ o al tiquete no le
    llega — hallado al verificar en el navegador, 2026-09-16.
    """

    def test_envio_y_vuelto_aparecen_en_la_lista_de_ventas(self):
        self.confirmar(self.qr("Cliente"))
        cuenta = Cuenta.objects.get(mesa=self.mesa, estado=Cuenta.ABIERTA)
        cuenta.costo_envio = 5000
        cuenta.save(update_fields=["costo_envio"])
        efectivo = Caja.objects.create(nombre="Efectivo lista", tipo=Caja.EFECTIVO)
        total = calcular_totales(cuenta)["total"]
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.post(f"/api/cuentas/{cuenta.id}/cerrar/",
                   {"medio_pago": efectivo.id, "recibido_efectivo": total + 1_000}, format="json")
        self.assertEqual(r.status_code, 200, r.content)

        r = c.get("/api/ventas/")
        venta = next(v for v in r.json()["ventas"] if v["id"] == cuenta.id)
        self.assertEqual(venta["envio"], 5000)
        self.assertEqual(venta["vuelto_efectivo"], 1000)
        self.assertEqual(venta["recibido_efectivo"], total + 1_000)
