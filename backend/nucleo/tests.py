from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from configuracion.models import Parametro


class PerfilPersonalTests(TransactionTestCase):
    """SPEC-021: el perfil expone todos los roles y el permiso de cobro."""

    def setUp(self):
        cache.clear()
        self.mesero = User.objects.create_user("perfil_mesero", password="x")
        self.cajero = User.objects.create_user("perfil_cajero", password="x")
        self.parametro, _ = Parametro.objects.get_or_create(
            clave="meseros-pueden-cobrar",
            defaults={
                "etiqueta": "Los meseros pueden cobrar",
                "grupo": Parametro.GRUPO_OPERACION,
                "tipo": Parametro.TEXTO,
                "valor": "no",
            },
        )

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def cliente(self, usuario):
        cliente = APIClient()
        cliente.force_authenticate(usuario)
        return cliente

    def test_expone_todos_los_roles_y_prioriza_cajero(self):
        self.mesero.groups.add(Group.objects.get_or_create(name="mesero")[0])
        self.mesero.groups.add(Group.objects.get_or_create(name="cajero")[0])
        perfil = self.cliente(self.mesero).get("/api/auth/perfil/").json()
        self.assertEqual(perfil["roles"], ["cajero", "mesero"])
        self.assertEqual(perfil["rol"], "cajero")
        self.assertTrue(perfil["puede_cobrar"])

    def test_mesero_sigue_el_parametro_de_cobro(self):
        self.mesero.groups.add(Group.objects.get_or_create(name="mesero")[0])
        self.parametro.valor = "no"
        self.parametro.save()
        self.assertFalse(self.cliente(self.mesero).get("/api/auth/perfil/").json()["puede_cobrar"])

        self.parametro.valor = "si"
        self.parametro.save()
        self.assertTrue(self.cliente(self.mesero).get("/api/auth/perfil/").json()["puede_cobrar"])

    def test_cajero_puede_cobrar_sin_importar_el_parametro(self):
        self.cajero.groups.add(Group.objects.get_or_create(name="cajero")[0])
        self.parametro.valor = "no"
        self.parametro.save()
        self.assertTrue(self.cliente(self.cajero).get("/api/auth/perfil/").json()["puede_cobrar"])


class ParametroCobroTests(TransactionTestCase):
    """
    SPEC-014, revisado 2026-09-16: "Los meseros también pueden cobrar" se
    elige Sí/No en Configuración → Cobro. Se prueba con el parámetro tal como
    queda después de la migración: booleano, en el grupo nuevo.
    """

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.admin = User.objects.create_user("cobro_admin", password="x", is_staff=True)
        self.mesero = User.objects.create_user("cobro_mesero", password="x")
        self.mesero.groups.add(Group.objects.get_or_create(name="mesero")[0])
        self.parametro = Parametro.objects.create(
            clave="meseros-pueden-cobrar", etiqueta="Los meseros también pueden cobrar",
            grupo=Parametro.GRUPO_COBRO, tipo=Parametro.BOOLEANO, valor="si",
        )

    def api(self, usuario):
        cliente = APIClient()
        cliente.force_authenticate(usuario)
        return cliente

    def puede_cobrar(self):
        return self.api(self.mesero).get("/api/auth/perfil/").json()["puede_cobrar"]

    def test_el_selector_si_no_cambia_quien_cobra_sin_reiniciar(self):
        self.assertTrue(self.puede_cobrar())
        # Lo mismo que hace el selector del panel: guarda "no" por la API.
        r = self.api(self.admin).patch(
            f"/api/configuracion/{self.parametro.id}/", {"valor": "no"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertFalse(self.puede_cobrar())
        # Y el servidor lo impide, no solo la interfaz.
        self.assertEqual(self.api(self.mesero).get("/api/movimientos/").status_code, 403)

        self.api(self.admin).patch(
            f"/api/configuracion/{self.parametro.id}/", {"valor": "si"}, format="json")
        self.assertTrue(self.puede_cobrar())

    def test_la_migracion_conserva_el_valor_escrito_a_mano(self):
        import importlib

        from django.apps import apps as registro

        migracion = importlib.import_module("configuracion.migrations.0007_grupo_cobro")
        casos = {"no": "no", "No ": "no", "false": "no", "si": "si", "Sí": "si", "": "si"}
        for escrito, esperado in casos.items():
            Parametro.objects.filter(clave="meseros-pueden-cobrar").update(
                valor=escrito, tipo=Parametro.TEXTO, grupo=Parametro.GRUPO_CONTACTO)
            migracion.mover_a_cobro(registro, None)
            p = Parametro.objects.get(clave="meseros-pueden-cobrar")
            self.assertEqual((p.valor, p.tipo, p.grupo), (esperado, "booleano", "cobro"), escrito)
