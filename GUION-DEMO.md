# Guion de demostración

Todo corre en local: Postgres en Docker, Django y Vue en el PC.

> **El sitio está vestido de Springfield** (boceto para la reunión): paleta Simpson,
> tipografía cartoon, cielo del intro en la portada. Es todo configuración — para volver
> al tema Terra: `manage.py cargar_configuracion_demo`; para re-aplicar Springfield:
> `manage.py cargar_tema_springfield`. Ese cambio de marca en un comando es, en sí mismo,
> un argumento de venta para mostrar.

## Antes de empezar (5 minutos antes de la reunión)

**1. Levantar los tres servicios**

```bash
docker compose up -d db
```

```bash
cd backend && ./.venv/Scripts/python.exe manage.py runserver 0.0.0.0:8000
```

```bash
cd frontend && npm run dev
```

**2. Dejar el sistema en cero**

Borra los pedidos de prueba anteriores. No toca el menú, las mesas ni la configuración.

```bash
cd backend && ./.venv/Scripts/python.exe manage.py limpiar_pedidos --si
```

**3. Iniciar sesión ANTES de que llegue el cliente**

Cada rol tiene su propio usuario y solo ve SU pantalla (el mesero no entra a
cocina, cocina no entra al mesero, y ninguno al panel de administración):

| Usuario  | Contraseña       | Entra directo a |
|----------|------------------|-----------------|
| `admin`  | `admin_dev_2026` | Panel admin (y puede ver todo) |
| `mesero` | `mesero2026`     | Pantalla del mesero |
| `cocina` | `cocina2026`     | Tablero de cocina |

La sesión vive por navegador: para tener mesero Y cocina abiertos a la vez,
usa **dos navegadores distintos** (p.ej. mesero en Chrome y cocina en Edge, o
una ventana normal y una de incógnito). La alternativa simple: entra como
`admin` en un solo navegador y muévete entre pestañas — el admin ve todas las
pantallas.

---

## Los tres enlaces

| Pantalla | Enlace | Quién la usa |
|---|---|---|
| **Cliente** | `http://localhost:5173/m/x7f2q9` | El comensal en la mesa |
| **Mesero** | `http://localhost:5173/mesero` | El mesero |
| **Cocina** | `http://localhost:5173/estacion` | La estación de preparación |

Ábrelos en **tres pestañas distintas** antes de empezar, en ese orden. Así solo cambias
de pestaña durante la demostración en vez de escribir direcciones.

> El `x7f2q9` del final es el código de la Mesa 12. Es el que iría impreso en el QR
> pegado en esa mesa. La otra mesa sembrada es `b3k9m2` (Mesa 5).

---

## El recorrido, paso a paso

### 1. Cliente (pestaña 1)

- Muestra el menú: las fotos, las categorías, los filtros
- Agrega dos o tres platos con el botón **+**
- **Importante:** agrega al menos una bebida. Así el pedido se parte en dos comandas
  (Cocina y Bar) y se ve el ruteo automático, que es lo que impresiona
- Abre **Ver pedido**, marca alguna observación ("sin cebolla")
- Pulsa **Generar QR del pedido**
- Toma captura de pantalla del QR

### 2. Mesero (pestaña 2)

El mesero tiene tres formas de tomar un pedido:

- **Escanear con cámara** — apunta al QR que el cliente muestra en su pantalla
  (ideal si el cliente está en el celular y el mesero en otro equipo)
- **Subir imagen del QR** — elige la captura (la vía segura para la demo)
- **Crear pedido** — el Camino B: si el cliente no usó la app, el mesero arma el
  pedido él mismo con el mismo menú, elige la mesa y lo envía

Con el QR leído: aparece el pedido exacto, con **Mesa 12** y las observaciones.
Pulsa **Enviar a cocina**.

### 3. Cocina (pestaña 3)

- La comanda aparece en la columna **Por preparar**, con los platos y las
  observaciones visibles de un vistazo y el cronómetro en verde
- Pulsa **Empezar a preparar** → la tarjeta pasa a **En preparación**
- Pulsa **✓ Listo — avisar al mesero** → pasa a **Listas** y se dispara el aviso
- Cambia el selector de arriba a **Bar** y repite con la otra comanda
- Cuando el mesero finaliza el pedido, las tarjetas salen solas del tablero

### 4. Mesero otra vez (pestaña 2)

- La campana arriba a la derecha ya muestra el contador
- Ábrela: dice qué estación tiene listo el pedido y de qué mesa
- Pulsa **Finalizar pedido**

---

## Qué señalar mientras lo muestras

- **El pedido se parte solo.** El cliente pidió comida y bebida; cocina y bar reciben
  cada uno lo suyo, sin que nadie los separe a mano.
- **Las observaciones viajan.** "Sin cebolla" llega hasta la pantalla de cocina.
- **El cronómetro cambia de color.** Verde, ámbar a los 10 minutos, rojo a los 20.
- **Nadie va a preguntar si ya está listo.** Cocina marca, el mesero se entera.
- **Cada venta queda con responsable.** El pedido queda amarrado al mesero que lo
  confirmó — de ahí sale la parte contable y auditable.

---

## Si algo falla

**El cliente entró por el enlace sin mesa** (`/` en vez de `/m/x7f2q9`): no pasa nada.
El mesero verá un recuadro amarillo pidiendo elegir la mesa de una lista. Es
comportamiento previsto, no un error — de hecho puedes mostrarlo como una función.

**Las fotos no cargan:** revisa que Django esté corriendo. El frontend pide las imágenes
a través de él.

**La notificación no aparece:** refresca la pestaña del mesero. Se actualiza sola cada
3 segundos y también al volver a la pestaña.

---

## Mostrarlo desde el celular

Funciona, y es la forma más convincente de enseñar la parte del cliente —porque es
exactamente como lo usaría un comensal.

**Requisito:** el celular y el PC deben estar en la misma red. Si el PC está usando los
datos del celular por USB o por zona Wi-Fi, ya lo están.

Al levantar Vite, la consola muestra las direcciones de red. Usa la que dice **Wi-Fi**:

```
http://192.168.80.19:5173/m/x7f2q9
```

Esa dirección **cambia** según la red. Revisa siempre la que imprime Vite al arrancar.

Desde el celular puedes abrir cualquiera de las tres pantallas cambiando el final de la
dirección (`/m/x7f2q9`, `/mesero`, `/estacion`).

> Ojo: la **cámara** del escáner solo funciona en el PC (localhost) — los navegadores
> exigen HTTPS para dar acceso a la cámara, y por IP local no lo hay. Desde el celular
> usa la opción de **subir imagen**, que funciona igual.

> Idea: deja el **cliente en el celular** y **mesero y cocina en el PC**. Escaneas o pasas
> la captura del QR y se ve mucho más real que hacerlo todo en la misma pantalla.
