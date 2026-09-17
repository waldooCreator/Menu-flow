"""
La cuenta: lo que una mesa debe, y el registro de que se cobró (SPEC-013).

Es la mitad de dinero del sistema, deliberadamente separada de la mitad de
cocina que vive en `pedidos` y `estaciones`.

> `Pedido` responde "manden esto a preparar" y avanza pendiente → listo →
> entregado. `Cuenta` responde "esta mesa debe $X" y avanza abierta →
> cerrada. **Son ortogonales**: un pedido entregado con cuenta abierta es lo
> normal — se comieron la comida y todavía no pagan.

Se llama CUENTA y no factura a propósito: "factura" sugiere emisión ante la
DIAN, que este proyecto descarta.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class Caja(models.Model):
    """
    Una bolsa de dinero: EFECTIVO, NEQUI, DAVIPLATA, BANCOLOMBIA…

    Es **lo mismo** que un medio de pago, visto en dos momentos: al cobrar se
    elige, y ahí se acumula. Por eso una sola entidad y no dos (SPEC-014,
    igual que el sistema que se va a reemplazar).

    Configurable desde el panel: cada restaurante cobra por donde puede.
    Una caja con movimientos no se borra — se desactiva.
    """

    # Los dos tipos NO son cosmeticos: son dos formas distintas de cuadrar
    # (SPEC-020). El efectivo se cuenta con la mano y se retira al cerrar el
    # turno; una cuenta de banco no se puede contar, se concilia contra el
    # extracto, y su saldo corre sin reiniciarse.
    EFECTIVO = "efectivo"
    BANCO = "banco"
    TIPOS = [(EFECTIVO, "Efectivo"), (BANCO, "Banco o billetera")]

    nombre = models.CharField(max_length=40, unique=True)
    tipo = models.CharField(
        max_length=10, choices=TIPOS, default=BANCO,
        help_text="Efectivo se cuenta a mano y se retira al cerrar el turno. "
                  "Banco cubre Nequi, Daviplata, el datafono y las cuentas: "
                  "no se cuentan, se concilian contra el extracto.",
    )
    prefijo = models.CharField(
        max_length=4, blank=True, default="",
        help_text="Sigla del consecutivo del tiquete, p.ej. Ef",
    )
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "caja"
        verbose_name_plural = "cajas"

    def __str__(self):
        return self.nombre

    def saldo(self):
        """
        Suma de sus movimientos. **No hay campo `saldo`** a propósito
        (SPEC-014): un número guardado que se va incrementando puede
        desincronizarse, y cuando pasa no hay forma de saber dónde se rompió.
        Derivándolo, el saldo cuadra con su libro por construcción.
        """
        from django.db.models import Case, IntegerField, Sum, When

        total = self.movimientos.aggregate(
            t=Sum(Case(
                When(tipo=MovimientoCaja.INGRESO, then="monto"),
                When(tipo=MovimientoCaja.EGRESO, then=-models.F("monto")),
                output_field=IntegerField(),
            ))
        )["t"]
        return total or 0

    def tiene_saldo_inicial(self):
        """
        Si ya se declaro con cuanto arrancaba esta caja (SPEC-020).

        Se pregunta al libro y no a un campo por lo mismo que el saldo: el
        saldo inicial ES un movimiento, no una excepcion.
        """
        return self.movimientos.filter(
            concepto=MovimientoCaja.SALDO_INICIAL).exists()


class CategoriaGasto(models.Model):
    """
    En que se va la plata: nomina, insumos, servicios, arriendo… (SPEC-020).

    Configurable desde el panel a proposito: cada restaurante gasta en cosas
    distintas, y una lista fija obligaria a meter todo en "Otros" — que es
    justo lo que impide responder "¿cuanto se fue en nomina el mes pasado?".

    La categoria NO reemplaza a la descripcion. Dice de que **tipo** es el
    gasto; la descripcion dice **cual** fue. Sin descripcion, la gente
    terminaria creando categorias llamadas "Insumos - pollo".
    """

    nombre = models.CharField(max_length=60, unique=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "categoría de gasto"
        verbose_name_plural = "categorías de gasto"

    def __str__(self):
        return self.nombre


class Cuenta(models.Model):
    ABIERTA = "abierta"
    CERRADA = "cerrada"
    ANULADA = "anulada"

    ESTADOS = [
        (ABIERTA, "Abierta"),
        (CERRADA, "Cerrada"),
        (ANULADA, "Anulada"),
    ]

    # A quien se le vendio, si es domicilio (SPEC-019). Opcional a proposito:
    # una venta de mesa no tiene cliente, y forzar uno obligaria a inventar
    # datos.
    #
    # `SET_NULL` es lo que permite BORRAR un cliente sin borrar sus ventas —
    # requisito de la Ley 1581. La venta conserva su nombre congelado y su
    # historia contable; solo desaparece el dato personal.
    cliente = models.ForeignKey(
        "clientes.Cliente", on_delete=models.SET_NULL, related_name="cuentas",
        null=True, blank=True,
    )

    # Sin mesa = domicilio. Igual criterio que `Pedido` (SPEC-002).
    mesa = models.ForeignKey(
        "pedidos.Mesa", on_delete=models.PROTECT, related_name="cuentas",
        null=True, blank=True,
    )
    es_domicilio = models.BooleanField(default=False)
    estado = models.CharField(max_length=10, choices=ESTADOS, default=ABIERTA)

    # Costo del domicilio (SPEC-013/025, 2026-09-16). Fijo por cuenta: no se
    # recalcula si el pedido cambia, a diferencia del subtotal. En una mesa
    # se queda en 0.
    costo_envio = models.PositiveIntegerField(default=0)

    abierta_en = models.DateTimeField(auto_now_add=True)

    # Si el cliente aceptó la propina. Voluntaria por definición: el sistema
    # tiene que permitir quitarla, mostrarla como obligatoria sería mentir.
    aplica_propina = models.BooleanField(default=True)

    # ---- Congelados al cerrar -------------------------------------------
    # Una cuenta cerrada es un hecho consumado: si mañana se corrige un
    # renglón histórico, lo que se cobró esa noche no puede cambiar. Y un
    # reporte de un mes no tiene que resumar miles de renglones.
    cerrada_en = models.DateTimeField(null=True, blank=True)
    cerrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="cuentas_cerradas", null=True, blank=True,
    )
    medio_pago = models.ForeignKey(
        Caja, on_delete=models.PROTECT, related_name="cuentas",
        null=True, blank=True,
    )
    subtotal_congelado = models.PositiveIntegerField(null=True, blank=True)
    propina_congelada = models.PositiveIntegerField(null=True, blank=True)
    impuesto_congelado = models.PositiveIntegerField(null=True, blank=True)
    total_congelado = models.PositiveIntegerField(null=True, blank=True)

    # Vueltos (SPEC-025, 2026-09-16). Solo tienen valor si se cobró en
    # efectivo y quien cobró indicó con cuánto pagó el cliente; si no, quedan
    # nulos y el tiquete no muestra la línea.
    recibido_efectivo = models.PositiveIntegerField(null=True, blank=True)
    vuelto_efectivo = models.PositiveIntegerField(null=True, blank=True)

    # SPEC-016: el consecutivo se congela junto con la venta.
    tiquete_numero = models.PositiveIntegerField(null=True, blank=True)
    tiquete_anio = models.PositiveIntegerField(null=True, blank=True)

    # ---- Anulación (SPEC-008: nada se borra) ----------------------------
    motivo_anulacion = models.CharField(max_length=200, blank=True)
    anulada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="cuentas_anuladas", null=True, blank=True,
    )
    anulada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-abierta_en"]
        constraints = [
            # Una sola cuenta ABIERTA por mesa (SPEC-013, regla 1). Lo
            # garantiza la base, no el código: dos meseros confirmando a la
            # vez en la misma mesa no pueden abrir dos cuentas.
            models.UniqueConstraint(
                fields=["mesa"],
                condition=models.Q(estado="abierta", mesa__isnull=False),
                name="una_cuenta_abierta_por_mesa",
            ),
            models.UniqueConstraint(
                fields=["medio_pago", "tiquete_anio", "tiquete_numero"],
                condition=models.Q(
                    medio_pago__isnull=False,
                    tiquete_anio__isnull=False,
                    tiquete_numero__isnull=False,
                ),
                name="tiquete_unico_por_medio_anio_numero",
            ),
        ]

    def __str__(self):
        destino = "Domicilio" if self.es_domicilio else (
            self.mesa.nombre if self.mesa else "Sin mesa")
        return f"Cuenta #{self.id} — {destino} ({self.get_estado_display()})"

    @property
    def destino(self):
        if self.es_domicilio:
            return "Domicilio"
        return self.mesa.nombre if self.mesa else "Sin mesa"

    @property
    def esta_abierta(self):
        return self.estado == self.ABIERTA

    @property
    def numero_tiquete(self):
        if not self.tiquete_numero or not self.tiquete_anio or not self.medio_pago:
            return None
        prefijo = self.medio_pago.prefijo or self.medio_pago.nombre[:2]
        return f"{prefijo}-{self.tiquete_anio}-{self.tiquete_numero:05d}"

    def subtotal_vivo(self):
        """
        Suma de los renglones de sus pedidos NO anulados, a precio
        congelado. Se recalcula mientras la cuenta esté abierta; al cerrar
        se guarda y no se vuelve a tocar.
        """
        from pedidos.models import DetallePedido, Pedido

        renglones = DetallePedido.objects.filter(
            pedido__cuenta=self,
        ).exclude(pedido__estado=Pedido.ANULADO)
        return sum(r.precio_congelado * r.cantidad for r in renglones)

    def marcar_anulada(self, usuario, motivo):
        self.estado = self.ANULADA
        self.motivo_anulacion = motivo
        self.anulada_por = usuario
        self.anulada_en = timezone.now()
        self.save(update_fields=["estado", "motivo_anulacion", "anulada_por", "anulada_en"])


class Turno(models.Model):
    """
    El periodo de trabajo de quien responde por el dinero (SPEC-014).

    El fondo inicial NO es un campo aquí: es un `MovimientoCaja` de ingreso.
    Así el saldo de la caja sigue siendo la suma de su libro, sin excepciones.
    Lo que sí se guarda es el **efectivo contado** al cerrar: eso no se puede
    derivar de nada, alguien lo contó a mano.
    """

    ABIERTO = "abierto"
    CERRADO = "cerrado"

    ESTADOS = [(ABIERTO, "Abierto"), (CERRADO, "Cerrado")]

    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="turnos",
    )
    estado = models.CharField(max_length=10, choices=ESTADOS, default=ABIERTO)

    abierto_en = models.DateTimeField(auto_now_add=True)
    observacion_apertura = models.CharField(max_length=200, blank=True)

    cerrado_en = models.DateTimeField(null=True, blank=True)
    observacion_cierre = models.CharField(max_length=200, blank=True)
    # Normalmente es el mismo `responsable`. Se guarda aparte porque el
    # administrador puede cerrar el turno de otro (SPEC-014): un turno que
    # alguien dejó abierto desde hace semanas deja a esa persona sin poder
    # abrir el de hoy. Cerrarlo desde afuera es una intervención
    # administrativa, y tiene que quedar constando quién la hizo.
    cerrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="turnos_cerrados", null=True, blank=True,
    )
    # Lo que la persona contó en el cajón. Se guarda como salió: el cuadre no
    # se maquilla para que dé cero (SPEC-014, regla 6).
    efectivo_contado = models.PositiveIntegerField(null=True, blank=True)
    # Cuánto se dejó en el cajón para el día siguiente (SPEC-020). El resto
    # sale como retiro, así el efectivo no crece indefinidamente en el libro.
    base_dejada = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-abierto_en"]
        constraints = [
            # Un turno abierto por persona, garantizado por la base.
            models.UniqueConstraint(
                fields=["responsable"],
                condition=models.Q(estado="abierto"),
                name="un_turno_abierto_por_persona",
            ),
        ]

    def __str__(self):
        return f"Turno #{self.id} — {self.responsable.username} ({self.get_estado_display()})"


class MovimientoCaja(models.Model):
    """
    El libro. **Toda plata que se mueve deja una fila aquí** — no hay forma de
    cambiar un saldo sin dejar rastro (SPEC-014, regla 2).

    De solo inserción: un error se corrige con el movimiento contrario, nunca
    editando ni borrando el original (regla 3, y el mismo criterio de ADR-007).
    """

    INGRESO = "ingreso"
    EGRESO = "egreso"
    TIPOS = [(INGRESO, "Ingreso"), (EGRESO, "Egreso")]

    VENTA = "venta"
    ANULACION = "anulacion"
    FONDO_INICIAL = "fondo_inicial"
    TRASLADO = "traslado"
    OTRO = "otro"
    # SPEC-020
    SALDO_INICIAL = "saldo_inicial"
    GASTO = "gasto"
    RETIRO_CIERRE = "retiro_cierre"
    DIFERENCIA_ARQUEO = "diferencia_arqueo"

    CONCEPTOS = [
        (VENTA, "Venta"),
        (ANULACION, "Anulación de venta"),
        (FONDO_INICIAL, "Fondo inicial de turno"),
        (TRASLADO, "Traslado entre cajas"),
        (SALDO_INICIAL, "Saldo con el que arrancó la caja"),
        (GASTO, "Gasto"),
        (RETIRO_CIERRE, "Retiro al cerrar el turno"),
        (DIFERENCIA_ARQUEO, "Diferencia de arqueo"),
        (OTRO, "Ingreso o gasto"),
    ]

    caja = models.ForeignKey(Caja, on_delete=models.PROTECT, related_name="movimientos")
    tipo = models.CharField(max_length=10, choices=TIPOS)
    concepto = models.CharField(max_length=20, choices=CONCEPTOS, default=OTRO)
    monto = models.PositiveIntegerField()
    descripcion = models.CharField(max_length=200, blank=True)

    # Vacío = ocurrió fuera de turno. Se cobra igual (decisión del autor):
    # bloquear el cobro por un olvido administrativo detendría el servicio.
    # Queda visible en el reporte en vez de perderse en silencio.
    turno = models.ForeignKey(
        Turno, on_delete=models.PROTECT, related_name="movimientos",
        null=True, blank=True,
    )
    cuenta = models.ForeignKey(
        Cuenta, on_delete=models.PROTECT, related_name="movimientos",
        null=True, blank=True,
    )
    # Solo la llevan los gastos (SPEC-020). Es `PROTECT` porque una categoria
    # con gastos registrados no se borra: se desactiva. Borrarla dejaria
    # movimientos historicos sin explicacion de en que se fue esa plata.
    categoria = models.ForeignKey(
        CategoriaGasto, on_delete=models.PROTECT, related_name="movimientos",
        null=True, blank=True,
    )

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="movimientos_caja",
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "movimiento de caja"
        verbose_name_plural = "movimientos de caja"

    def __str__(self):
        signo = "+" if self.tipo == self.INGRESO else "−"
        return f"{signo}{self.monto} {self.caja.nombre} ({self.get_concepto_display()})"
