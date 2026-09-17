"""
Las operaciones sobre cuentas, cajas y turnos (SPEC-013 y SPEC-014).

Fuera de las vistas por la misma razón que `estaciones/ruteo.py` y
`pedidos/novedades.py`: una responsabilidad, testeable sin HTTP.
"""

from django.db import transaction
from django.db.models import Max, Sum
from django.utils import timezone

from configuracion.helpers import obtener_configuracion

from .models import Caja, Cuenta, MovimientoCaja, Turno

# Claves de configuración (SPEC-007): nunca porcentajes ni reglas escritos a mano.
CLAVE_PROPINA = "propina-porcentaje"
CLAVE_IMPUESTO = "impuesto-porcentaje"
CLAVE_MESEROS_COBRAN = "meseros-pueden-cobrar"

# La única caja que se cuenta a mano al cerrar turno.
NOMBRE_EFECTIVO = "Efectivo"


class OperacionInvalida(Exception):
    """No se puede hacer; el mensaje es para mostrárselo a quien cobra."""


def _porcentaje(clave):
    """
    Lee un porcentaje de configuración. Un valor vacío o mal escrito vale 0:
    cobrar de más por un parámetro con un dedazo es peor que no cobrarlo, y
    el 0 se nota enseguida.
    """
    try:
        valor = float(obtener_configuracion().get(clave) or 0)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, valor)


# --------------------------------------------------------------------------
# Quién puede cobrar (SPEC-014)
# --------------------------------------------------------------------------

def puede_cobrar(usuario):
    """
    El administrador y el cajero siempre. El mesero **solo si el parámetro lo
    permite** — mixto y configurable: unos restaurantes dejan que el mesero
    cobre y otros lo reservan a caja.

    Se comprueba AQUÍ, en el servidor. Esconder el botón no es un permiso: si
    la regla viviera solo en la interfaz, cualquiera con el enlace cobraría.
    """
    if not (usuario and usuario.is_authenticated):
        return False
    if usuario.is_superuser or usuario.is_staff:
        return True

    roles = set(usuario.groups.values_list("name", flat=True))
    if "cajero" in roles:
        return True
    if "mesero" in roles:
        # Desde 2026-09-16 es un parámetro sí/no y llega como booleano; se
        # sigue aceptando el texto por si una base vieja no migró todavía.
        valor = str(obtener_configuracion().get(CLAVE_MESEROS_COBRAN, "si")).strip().lower()
        # Arranca encendido: si arrancara apagado, un restaurante recién
        # instalado no podría cobrar hasta crear un cajero — una trampa.
        return valor not in ("no", "false", "0", "")
    return False


# --------------------------------------------------------------------------
# Cajas y movimientos (SPEC-014)
# --------------------------------------------------------------------------

def turno_abierto_de(usuario):
    return Turno.objects.filter(responsable=usuario, estado=Turno.ABIERTO).first()


def usuarios_para_turno():
    """
    A quiénes se les puede abrir un turno (SPEC-014, 2026-09-03): mesero o
    cajero, activos. No es "quien tiene sesión" — caja abre el turno DE un
    mesero, no necesariamente el propio de quien está frente a la pantalla.
    """
    from django.contrib.auth.models import User
    return (
        User.objects.filter(
            groups__name__in=["mesero", "cajero"], is_active=True)
        .distinct().order_by("username")
    )


def turnos_abiertos():
    """Todos los turnos abiertos ahora mismo, de cualquier persona."""
    return Turno.objects.filter(estado=Turno.ABIERTO).select_related("responsable")


def caja_efectivo():
    """
    La caja física, la que se cuenta con la mano.

    Desde SPEC-020 se busca por **tipo**, no por nombre: el nombre lo escribe
    cada restaurante y "Caja mayor" o "Efectivo 1" dejaban de encontrarse. Se
    conserva la búsqueda por nombre como último recurso, para una base que
    todavía no tenga el tipo puesto.
    """
    return (
        Caja.objects.filter(tipo=Caja.EFECTIVO, activo=True).first()
        or Caja.objects.filter(nombre__iexact=NOMBRE_EFECTIVO, activo=True).first()
    )


def registrar_movimiento(caja, tipo, monto, autor, concepto=MovimientoCaja.OTRO,
                         descripcion="", cuenta=None, turno=None, categoria=None):
    """
    Toda plata que se mueve deja una fila aquí (SPEC-014, regla 2): no hay
    forma de cambiar un saldo sin dejar rastro, porque el saldo ES la suma de
    estas filas.

    `turno` vacío significa "fuera de turno": se registra igual y queda
    visible, en vez de perderse en silencio.
    """
    if monto <= 0:
        raise OperacionInvalida("El monto debe ser mayor que cero.")
    return MovimientoCaja.objects.create(
        caja=caja, tipo=tipo, concepto=concepto, monto=monto,
        descripcion=descripcion, cuenta=cuenta, categoria=categoria,
        turno=turno if turno is not None else turno_abierto_de(autor),
        autor=autor,
    )


def trasladar(caja_origen, caja_destino, monto, autor, descripcion=""):
    """
    Mover plata entre cajas — consignar el efectivo en el banco, por ejemplo.

    Son dos movimientos: sale de una y entra a la otra. Los dos saldos quedan
    bien solos, sin tocar ningún campo de saldo.
    """
    if caja_origen == caja_destino:
        raise OperacionInvalida("El origen y el destino son la misma caja.")
    texto = descripcion or f"Traslado {caja_origen.nombre} -> {caja_destino.nombre}"
    with transaction.atomic():
        # Solo el origen se bloquea: es de donde sale la plata, y es el único
        # que puede quedar en negativo. El destino solo recibe.
        caja_origen = Caja.objects.select_for_update().get(pk=caja_origen.pk)
        verificar_alcanza(caja_origen, monto)
        registrar_movimiento(caja_origen, MovimientoCaja.EGRESO, monto, autor,
                             concepto=MovimientoCaja.TRASLADO, descripcion=texto)
        registrar_movimiento(caja_destino, MovimientoCaja.INGRESO, monto, autor,
                             concepto=MovimientoCaja.TRASLADO, descripcion=texto)


# --------------------------------------------------------------------------
# Activos líquidos (SPEC-020)
# --------------------------------------------------------------------------

def fijar_saldo_inicial(caja, monto, autor):
    """
    Con cuánto arrancaba esta caja el día que el restaurante empezó a usar el
    sistema. Se hace **una sola vez por caja**.

    Queda como un movimiento y no como un campo a propósito: el saldo es la
    suma del libro sin excepciones (SPEC-014, regla 1). Un campo aparte sería
    la primera excepción, y a partir de ahí el saldo dejaría de cuadrar con su
    propio libro.
    """
    if monto <= 0:
        raise OperacionInvalida("El saldo inicial debe ser mayor que cero.")

    with transaction.atomic():
        # Bloquear la caja ANTES de mirar si ya tiene saldo inicial. Sin esto,
        # dos personas que lo fijen a la vez leen las dos "no tiene", las dos
        # pasan la comprobación, y la caja arranca con el doble de plata que
        # nunca tuvo. Es el patrón de ADR-008.
        caja = Caja.objects.select_for_update().get(pk=caja.pk)
        # Se exige que la caja esté VACÍA, no solo que no tenga saldo inicial.
        #
        # Si ya tiene movimientos, el monto que escriba el administrador se
        # SUMARÍA a lo que hay. Y lo que va a escribir es lo que ve en
        # pantalla — o sea el saldo actual — con lo que la caja terminaría con
        # el doble. Para ese caso la herramienta correcta es el ajuste, que
        # calcula la diferencia y deja constancia del motivo.
        if caja.movimientos.exists():
            raise OperacionInvalida(
                f"«{caja.nombre}» ya tiene movimientos, así que su saldo de "
                "arranque no se puede declarar ahora: se sumaría a lo que ya "
                "hay. Usa «Ajustar» y escribe el saldo real.")
        return registrar_movimiento(
            caja, MovimientoCaja.INGRESO, monto, autor,
            concepto=MovimientoCaja.SALDO_INICIAL,
            descripcion="Saldo con el que arrancó la caja")


def pesos(monto):
    """
    `$ 1.790.800`. Con punto de millar, que es como se escribe en Colombia.

    Existe como funcion porque el atajo de formatear y despues cambiar las
    comas por puntos sobre la frase COMPLETA tambien se come las comas del
    texto: "dice el sistema, ajusta el saldo" salia como "dice el sistema.
    ajusta el saldo". Se formatea el numero, no la oracion.
    """
    return f"$ {monto:,.0f}".replace(",", ".")


def verificar_alcanza(caja, monto, sugerencia=None):
    """
    Que no se saque de una caja más de lo que tiene.

    Sin esto el saldo quedaba **negativo**, y un saldo negativo no significa
    nada: no existe un cajón con menos cero pesos. Lo que hay detrás es
    siempre otra cosa —un monto mal escrito, o una caja cuyo saldo de arranque
    nadie declaró— y conviene decirlo en ese momento, no dejar el número roto.

    **Debe llamarse con la caja ya bloqueada.** Leer el saldo, decidir y
    escribir sin bloquear es el patrón de ADR-008: dos gastos simultáneos de
    100.000 sobre una caja con 150.000 leerían los dos "alcanza", pasarían los
    dos, y la caja terminaría en −50.000.
    """
    saldo = caja.saldo()
    if monto <= saldo:
        return

    falta = f"«{caja.nombre}» tiene {pesos(saldo)} y estás sacando {pesos(monto)}."
    if sugerencia:
        detalle = sugerencia
    elif not caja.movimientos.exists():
        detalle = ("Está en cero porque todavía no se ha declarado con cuánto "
                   "arrancó. Que el administrador lo registre primero.")
    else:
        detalle = ("Si de verdad hay más plata de la que dice el sistema, "
                   "ajusta el saldo antes de registrar esto.")
    raise OperacionInvalida(f"{falta} {detalle}")


def registrar_gasto(caja, monto, categoria, autor, descripcion=""):
    """
    Plata que sale y no es un traslado: nómina, insumos, servicios…

    La categoría es obligatoria. Sin ella nunca se podría responder "¿cuánto
    se fue en nómina el mes pasado?", que es la única razón por la que este
    módulo existe.

    La descripción **sigue existiendo y sigue siendo libre**: la categoría dice
    de qué tipo es el gasto, la descripción dice cuál fue.
    """
    if categoria is None:
        raise OperacionInvalida("Elige en qué categoría va este gasto.")
    if not getattr(categoria, "activo", True):
        raise OperacionInvalida(f"La categoría «{categoria}» está desactivada.")

    with transaction.atomic():
        caja = Caja.objects.select_for_update().get(pk=caja.pk)
        verificar_alcanza(caja, monto)
        return registrar_movimiento(
            caja, MovimientoCaja.EGRESO, monto, autor,
            concepto=MovimientoCaja.GASTO, descripcion=descripcion,
            categoria=categoria)


def registrar_egreso(caja, monto, autor, descripcion=""):
    """
    Una salida suelta que no es un gasto con categoría — el camino que ya
    existía antes de SPEC-020. Comprueba lo mismo: de una caja no sale más de
    lo que tiene.
    """
    with transaction.atomic():
        caja = Caja.objects.select_for_update().get(pk=caja.pk)
        verificar_alcanza(caja, monto)
        return registrar_movimiento(
            caja, MovimientoCaja.EGRESO, monto, autor, descripcion=descripcion)


def ajustar_saldo(caja, saldo_real, autor, motivo):
    """
    Corregir una caja contra la realidad: el extracto del banco, o el conteo
    del cajón.

    **No reescribe nada.** Calcula la diferencia y la registra como su propio
    movimiento, con autor y motivo. El saldo vuelve a coincidir con la realidad
    *y* queda constando quién lo ajustó, cuánto y por qué.

    Un ajuste anónimo sería maquillaje; uno firmado es un registro contable.
    """
    motivo = (motivo or "").strip()
    if len(motivo) < 4:
        raise OperacionInvalida("Escribe por qué estás ajustando este saldo.")
    if saldo_real < 0:
        raise OperacionInvalida("El saldo no puede ser negativo.")

    with transaction.atomic():
        # Mismo bloqueo que arriba: la diferencia se calcula contra el saldo
        # actual, así que dos ajustes simultáneos leerían el mismo saldo viejo
        # y el segundo dejaría la caja en un número que nadie pidió.
        caja = Caja.objects.select_for_update().get(pk=caja.pk)
        diferencia = saldo_real - caja.saldo()
        if diferencia == 0:
            return None

        tipo = MovimientoCaja.INGRESO if diferencia > 0 else MovimientoCaja.EGRESO
        return registrar_movimiento(
            caja, tipo, abs(diferencia), autor,
            concepto=MovimientoCaja.DIFERENCIA_ARQUEO,
            descripcion=f"Ajuste de saldo: {motivo}")


# --------------------------------------------------------------------------
# Turno (SPEC-014)
# --------------------------------------------------------------------------

def abrir_turno(usuario, fondos=None, observacion=""):
    """
    Abre el turno con un fondo inicial **por caja** (SPEC-014, 2026-09-03).

    `fondos` es {caja_id: monto}. Antes solo se aceptaba efectivo, pero si el
    datáfono arranca el día con el saldo del cierre anterior o Nequi trae plata
    de ayer, ignorarlo hace que el cuadre nazca torcido y la diferencia final
    no signifique nada.

    Ningún fondo se guarda como campo del turno: cada uno es un movimiento de
    ingreso a su caja, para que el saldo siga siendo la suma del libro sin
    excepciones. Un fondo en cero **no** genera movimiento — una fila de cero
    pesos solo ensucia el libro.
    """
    if turno_abierto_de(usuario):
        # En tercera persona: quien abre este turno no es necesariamente
        # quien está frente a la pantalla — caja abre turnos EN NOMBRE de
        # los meseros (SPEC-014, 2026-09-03).
        raise OperacionInvalida(
            f"{usuario.username} ya tiene un turno abierto. Ciérralo antes de abrir otro.")

    # Se validan TODOS los montos antes de crear nada: si el tercero viene mal
    # escrito, no debe quedar un turno abierto con dos fondos puestos.
    limpios = {}
    for caja_id, monto in (fondos or {}).items():
        try:
            monto = int(monto or 0)
        except (TypeError, ValueError):
            raise OperacionInvalida("Los fondos iniciales deben ser números.")
        if monto < 0:
            raise OperacionInvalida("Un fondo inicial no puede ser negativo.")
        if monto:
            limpios[int(caja_id)] = monto

    cajas = {c.id: c for c in Caja.objects.filter(id__in=limpios, activo=True)}
    faltantes = set(limpios) - set(cajas)
    if faltantes:
        raise OperacionInvalida("Alguna de las cajas del fondo inicial ya no existe.")

    with transaction.atomic():
        turno = Turno.objects.create(responsable=usuario, observacion_apertura=observacion)
        for caja_id, monto in limpios.items():
            registrar_movimiento(
                cajas[caja_id], MovimientoCaja.INGRESO, monto, usuario,
                concepto=MovimientoCaja.FONDO_INICIAL,
                descripcion="Fondo inicial de turno", turno=turno,
            )
    return turno


def turnos_viejos_abiertos():
    """
    Turnos que siguen abiertos de días anteriores.

    Existe porque en el sistema que se va a reemplazar había turnos abiertos
    desde hacía semanas — uno del 7 de agosto seguía abierto el 3 de
    septiembre. Nadie los cerró y nada avisaba.

    Solo informa. No cierra nada solo: quien maneja la plata decide.
    """
    hoy = timezone.localtime().date()
    return (
        Turno.objects.filter(estado=Turno.ABIERTO, abierto_en__date__lt=hoy)
        .select_related("responsable")
    )


def cuadre_de(turno):
    """
    Esperado = fondo inicial + ventas en efectivo + ingresos − egresos
    Diferencia = contado − esperado

    La diferencia se reporta como sale. **No se ajusta el esperado para que
    dé cero** (SPEC-014, regla 6): ese número es justamente el que interesa.
    """
    movs = turno.movimientos.all()

    def suma(**filtros):
        return movs.filter(**filtros).aggregate(t=Sum("monto"))["t"] or 0

    efectivo = caja_efectivo()
    esperado_efectivo = 0
    if efectivo:
        esperado_efectivo = (
            suma(caja=efectivo, tipo=MovimientoCaja.INGRESO)
            - suma(caja=efectivo, tipo=MovimientoCaja.EGRESO)
        )

    # Lo que entró por cada caja: el efectivo se cuenta a mano, lo demás se
    # compara contra el banco.
    por_caja = []
    for caja in Caja.objects.filter(activo=True):
        entra = suma(caja=caja, tipo=MovimientoCaja.INGRESO)
        sale = suma(caja=caja, tipo=MovimientoCaja.EGRESO)
        if entra or sale:
            por_caja.append({
                "caja": caja.nombre, "ingresos": entra,
                "egresos": sale, "neto": entra - sale,
            })

    contado = turno.efectivo_contado
    return {
        "esperado_efectivo": esperado_efectivo,
        # Dos números distintos, y los dos hacen falta (SPEC-020):
        #
        # `esperado_efectivo` es lo que movió ESTE turno. Responde "de la plata
        # que pasó por mis manos, ¿cuadra?".
        #
        # `esperado_en_cajon` es lo que dice el libro que hay en el cajón AHORA
        # —incluida la base que quedó de ayer y lo de los compañeros—. Responde
        # "¿cuadra el cajón?", que es contra lo que se compara al hacer el
        # arqueo del cierre.
        #
        # Sin distinguirlos, la pantalla mostraría una diferencia y el servidor
        # registraría otra.
        "esperado_en_cajon": efectivo.saldo() if efectivo else 0,
        "efectivo_contado": contado,
        "diferencia": (contado - esperado_efectivo) if contado is not None else None,
        "por_caja": por_caja,
        "ventas": suma(concepto=MovimientoCaja.VENTA),
    }


def puede_cerrar_turno(usuario, turno):
    """
    El dueño del turno siempre. Otra persona, si puede cobrar (SPEC-014,
    revisado 2026-09-03): caja abre Y cierra los turnos de los meseros, así
    que quien maneja caja (cajero o administrador) puede cerrar cualquiera,
    no solo el propio. `cerrar_turno` exige motivo cuando es ajeno — eso es
    lo que deja el rastro, no restringir quién puede hacerlo.
    """
    if turno.responsable_id == usuario.id:
        return True
    return puede_cobrar(usuario)


def cerrar_turno(turno, efectivo_contado, observacion="", autor=None,
                 base_dejada=None, destino_efectivo=None, motivo_diferencia=""):
    """
    `autor` es quien está cerrando. Normalmente el mismo responsable; si es el
    administrador cerrando un turno ajeno, exige motivo y queda registrado.

    **`base_dejada` es lo que agrega SPEC-020.** Si viene, además de cerrar el
    turno se cierra el cajón: la plata sale y queda solo esa base para el día
    siguiente. Si no viene, el turno se cierra y el efectivo se queda donde
    está — es el caso de "todavía quedan compañeros vendiendo, la caja del día
    la cierra el último".

    Antes de esto el efectivo **nunca salía del libro**: se contaba y se
    guardaba el número, pero el saldo de Efectivo seguía creciendo día tras día
    como si nadie hubiera sacado la plata del cajón.
    """
    autor = autor or turno.responsable
    if not puede_cerrar_turno(autor, turno):
        raise OperacionInvalida("Solo el administrador puede cerrar el turno de otra persona.")

    ajeno = turno.responsable_id != autor.id
    if ajeno and len((observacion or "").strip()) < 4:
        # Cerrar la caja de otro no es una operación normal. Sin motivo, dentro
        # de un mes nadie sabría por qué el turno de esa persona lo cerró
        # alguien más.
        raise OperacionInvalida(
            "Escribe el motivo: estás cerrando el turno de otra persona.")

    if efectivo_contado is None or str(efectivo_contado).strip() == "":
        raise OperacionInvalida("Indica cuánto efectivo contaste en el cajón.")

    efectivo_contado = int(efectivo_contado)
    cierra_cajon = base_dejada is not None
    if cierra_cajon:
        base_dejada = int(base_dejada)
        if base_dejada < 0:
            raise OperacionInvalida("La base no puede ser negativa.")
        if base_dejada > efectivo_contado:
            raise OperacionInvalida(
                f"No puedes dejar {pesos(base_dejada)} de base si contaste "
                f"{pesos(efectivo_contado)}.")

    with transaction.atomic():
        # Mismo patrón que en las cuentas. Aquí no se duplica dinero, pero un
        # doble cierre pisaría el efectivo contado del primero con el del
        # segundo y el cuadre diría otra cosa que la que se contó.
        turno = Turno.objects.select_for_update().get(pk=turno.pk)
        if turno.estado == Turno.CERRADO:
            raise OperacionInvalida("Ese turno ya está cerrado.")

        if cierra_cajon:
            _cerrar_el_cajon(efectivo_contado, base_dejada, destino_efectivo,
                             autor, motivo_diferencia)

        turno.estado = Turno.CERRADO
        turno.cerrado_en = timezone.now()
        turno.efectivo_contado = efectivo_contado
        turno.base_dejada = base_dejada
        turno.observacion_cierre = observacion
        turno.cerrado_por = autor
        turno.save(update_fields=["estado", "cerrado_en", "efectivo_contado",
                                  "base_dejada", "observacion_cierre",
                                  "cerrado_por"])
    return turno


def _cerrar_el_cajon(contado, base, destino_id, autor, motivo):
    """
    El arqueo del efectivo (SPEC-020). Dos movimientos, en este orden:

    1. **La diferencia**, si lo contado no coincide con lo que decía el libro.
       Se registra como su propio movimiento, con autor y motivo obligatorio.
       No se disimula ni se mezcla con el retiro: el saldo vuelve a coincidir
       con la realidad *y* queda escrito que faltó (o sobró) plata.
    2. **El retiro**, por lo que sale del cajón. Si se consigna, es un traslado
       a la caja de banco elegida; si no, un egreso — la caja fuerte, o el
       dueño se lo lleva.

    Al terminar, el cajón queda exactamente en `base`.
    """
    efectivo = caja_efectivo()
    if efectivo is None:
        raise OperacionInvalida(
            "No hay ninguna caja de tipo efectivo configurada.")

    efectivo = Caja.objects.select_for_update().get(pk=efectivo.pk)
    diferencia = contado - efectivo.saldo()

    if diferencia != 0:
        motivo = (motivo or "").strip()
        if len(motivo) < 4:
            falta = "faltaron" if diferencia < 0 else "sobraron"
            raise OperacionInvalida(
                f"El cajón no cuadra: {falta} {pesos(abs(diferencia))}. "
                "Escribe qué pasó antes de cerrar.")
        registrar_movimiento(
            efectivo,
            MovimientoCaja.INGRESO if diferencia > 0 else MovimientoCaja.EGRESO,
            abs(diferencia), autor,
            concepto=MovimientoCaja.DIFERENCIA_ARQUEO,
            descripcion=f"Diferencia de arqueo: {motivo}")

    retiro = contado - base
    if retiro <= 0:
        return

    destino = Caja.objects.filter(
        id=destino_id, activo=True).exclude(pk=efectivo.pk).first() if destino_id else None
    if destino is not None:
        trasladar(efectivo, destino, retiro, autor,
                  descripcion=f"Consignación del cierre en {destino.nombre}")
    else:
        registrar_movimiento(
            efectivo, MovimientoCaja.EGRESO, retiro, autor,
            concepto=MovimientoCaja.RETIRO_CIERRE,
            descripcion="Retiro del cajón al cerrar")


# --------------------------------------------------------------------------
# Cuenta (SPEC-013)
# --------------------------------------------------------------------------

def calcular_totales(cuenta):
    """
    Totales de la cuenta. Si está CERRADA devuelve los congelados —
    justamente para eso se congelaron.
    """
    if cuenta.estado == Cuenta.CERRADA:
        return {
            "subtotal": cuenta.subtotal_congelado or 0,
            "propina": cuenta.propina_congelada or 0,
            "impuesto": cuenta.impuesto_congelado or 0,
            "envio": cuenta.costo_envio,
            "total": cuenta.total_congelado or 0,
            "congelado": True,
        }

    subtotal = cuenta.subtotal_vivo()
    propina = round(subtotal * _porcentaje(CLAVE_PROPINA) / 100) if cuenta.aplica_propina else 0
    impuesto = round(subtotal * _porcentaje(CLAVE_IMPUESTO) / 100)
    # El envío es fijo (SPEC-013): no depende de los renglones, así que se
    # suma tal cual esté guardado, en vivo o congelado.
    return {
        "subtotal": subtotal,
        "propina": propina,
        "impuesto": impuesto,
        "envio": cuenta.costo_envio,
        "total": subtotal + propina + impuesto + cuenta.costo_envio,
        "congelado": False,
    }


def cuenta_para(mesa=None, es_domicilio=False):
    """
    La cuenta a la que debe entrar un pedido que se está confirmando.

    Busca la cuenta ABIERTA de esa mesa; si no hay, la crea. La cuenta no se
    abre a mano (SPEC-013): un marcado más que recordar sería trabajo
    administrativo puro, que es lo primero que se deja de hacer en un viernes
    lleno.

    Un domicilio abre siempre la suya: no hay mesa donde acumular.
    """
    if es_domicilio or mesa is None:
        return Cuenta.objects.create(mesa=None, es_domicilio=True)

    abierta = Cuenta.objects.filter(mesa=mesa, estado=Cuenta.ABIERTA).first()
    if abierta:
        return abierta
    return Cuenta.objects.create(mesa=mesa, es_domicilio=False)


def cerrar_cuenta(cuenta, usuario, medio_pago_id, aplica_propina=None, liberar_mesa=False,
                  recibido_efectivo=None):
    """
    Cobrar. Exige medio de pago: sin él el cierre de caja no puede cuadrar
    nada, así que un cierre sin medio no significaría nada.

    `liberar_mesa` (SPEC-013, revisado 2026-09-16): cobrar significa que el
    cliente pagó para irse, y la mesa queda libre en el mismo paso. Con pago
    anticipado la pantalla lo manda en falso y la mesa sigue ocupada.

    `recibido_efectivo` (SPEC-025): solo tiene efecto si el medio elegido es
    de tipo Efectivo. El vuelto es informativo — no mueve dinero entre cajas,
    lo que entra sigue siendo el total (Regla 10 de SPEC-013).
    """
    if not puede_cobrar(usuario):
        raise OperacionInvalida("Tu rol no tiene habilitado el cobro.")

    medio = Caja.objects.filter(id=medio_pago_id, activo=True).first()
    if medio is None:
        raise OperacionInvalida("Indica con qué medio de pago se cobró.")

    with transaction.atomic():
        # La cuenta se RELEE bloqueada, y el estado se comprueba AQUÍ dentro.
        #
        # Comprobarlo antes de la transacción, sobre el objeto que llegó de la
        # vista, no sirve de nada: dos cajeros — o un cajero que toca "Cobrar"
        # dos veces porque la pantalla tardó — leen los dos "abierta", los dos
        # pasan la comprobación y los dos registran su ingreso. La caja termina
        # con el doble de plata y ambos ven OK. Medido: 61.600 cobrados una vez
        # entraban como 123.200, y como los movimientos son solo-inserción
        # (ADR-007) la fila falsa ya no se puede quitar.
        #
        # Con el bloqueo, el segundo espera a que el primero termine, relee
        # "cerrada" y recibe un error claro en vez de cobrar de nuevo.
        cuenta = Cuenta.objects.select_for_update().get(pk=cuenta.pk)
        if cuenta.estado == Cuenta.CERRADA:
            raise OperacionInvalida("Esta cuenta ya fue cobrada.")
        if cuenta.estado == Cuenta.ANULADA:
            raise OperacionInvalida("Esta cuenta está anulada.")

        # SPEC-016: serializa los consecutivos del mismo medio de pago.
        medio = Caja.objects.select_for_update().get(pk=medio.pk)

        if aplica_propina is not None:
            cuenta.aplica_propina = bool(aplica_propina)

        totales = calcular_totales(cuenta)
        if totales["subtotal"] <= 0:
            raise OperacionInvalida("La cuenta no tiene consumo que cobrar.")

        if recibido_efectivo is not None and medio.tipo == Caja.EFECTIVO:
            if recibido_efectivo < totales["total"]:
                raise OperacionInvalida(
                    f"Faltan {pesos(totales['total'] - recibido_efectivo)}: el cliente "
                    f"pagó {pesos(recibido_efectivo)} por una cuenta de {pesos(totales['total'])}."
                )
            cuenta.recibido_efectivo = recibido_efectivo
            cuenta.vuelto_efectivo = recibido_efectivo - totales["total"]

        cuenta.estado = Cuenta.CERRADA
        cuenta.cerrada_en = timezone.now()
        cuenta.cerrada_por = usuario
        cuenta.medio_pago = medio
        anio = timezone.localtime().year
        ultimo = Cuenta.objects.filter(
            medio_pago=medio, tiquete_anio=anio,
        ).aggregate(maximo=Max("tiquete_numero"))["maximo"] or 0
        cuenta.tiquete_anio = anio
        cuenta.tiquete_numero = ultimo + 1
        cuenta.subtotal_congelado = totales["subtotal"]
        cuenta.propina_congelada = totales["propina"]
        cuenta.impuesto_congelado = totales["impuesto"]
        cuenta.total_congelado = totales["total"]
        cuenta.save()

        # El dinero entra a la caja del medio elegido **sin importar quién
        # cerró** (SPEC-014): si un mesero cobra en Nequi, entra a Nequi
        # igual que si lo hubiera cobrado el cajero.
        #
        # Si no hay turno abierto queda sin turno, y se ve marcado como
        # "fuera de turno" — cobrar nunca se bloquea.
        registrar_movimiento(
            medio, MovimientoCaja.INGRESO, totales["total"], usuario,
            concepto=MovimientoCaja.VENTA,
            descripcion=f"Cuenta #{cuenta.id} - {cuenta.destino}",
            cuenta=cuenta,
        )

        if liberar_mesa and cuenta.mesa_id:
            from pedidos.models import Mesa

            cuenta.mesa.cambiar_estado(Mesa.LIBRE)

    return cuenta


def anular_cuenta(cuenta, usuario, motivo):
    """
    Anular, nunca borrar (Regla 2 de SPEC-008). Exige motivo.

    Anular una cuenta ABIERTA anula sus pedidos con ella. Anular una CERRADA
    es reversar un cobro: más grave, y por eso queda igual de registrado.
    """
    from pedidos.models import Pedido

    motivo = (motivo or "").strip()
    if len(motivo) < 4:
        raise OperacionInvalida("Escribe el motivo de la anulación.")

    with transaction.atomic():
        # Mismo bloqueo y misma razón que en `cerrar_cuenta`: dos anulaciones
        # simultáneas de una cuenta ya cobrada registrarían DOS egresos, y la
        # caja quedaría con menos plata de la que salió de verdad.
        cuenta = Cuenta.objects.select_for_update().get(pk=cuenta.pk)
        if cuenta.estado == Cuenta.ANULADA:
            raise OperacionInvalida("Esta cuenta ya está anulada.")

        # Anular una cuenta YA COBRADA saca la plata de la caja con el
        # movimiento contrario. El original no se toca: nada se borra, y el
        # libro queda contando la historia completa.
        if cuenta.estado == Cuenta.CERRADA and cuenta.medio_pago and cuenta.total_congelado:
            # SPEC-020: la devolución también es una salida de caja. Se toma
            # la Cuenta y después la Caja, igual que todas las operaciones que
            # pueden revertir una venta, para evitar saldos negativos y cruces
            # de bloqueo entre anulaciones concurrentes.
            caja = Caja.objects.select_for_update().get(pk=cuenta.medio_pago_id)
            verificar_alcanza(
                caja,
                cuenta.total_congelado,
                sugerencia=(
                    f"Registra primero de dónde sale esa plata de «{caja.nombre}» "
                    "(un ingreso o traslado) y vuelve a intentar."
                ),
            )
            registrar_movimiento(
                caja, MovimientoCaja.EGRESO, cuenta.total_congelado,
                usuario, concepto=MovimientoCaja.ANULACION,
                descripcion=f"Anulacion cuenta #{cuenta.id}: {motivo}",
                cuenta=cuenta,
            )

        cuenta.marcar_anulada(usuario, motivo)
        # Los pedidos caen con ella: no tiene sentido dejar comida "en curso"
        # de una cuenta que no existe.
        cuenta.pedidos.exclude(estado=Pedido.ANULADO).update(
            estado=Pedido.ANULADO,
            motivo_anulacion=f"Cuenta #{cuenta.id} anulada: {motivo}",
        )

    return cuenta
