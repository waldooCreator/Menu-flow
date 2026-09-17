import { createRouter, createWebHistory } from "vue-router";
import { obtenerPerfil } from "../api/auth";
import { useAuthStore } from "../stores/auth";

/** A qué pantalla entra cada rol al iniciar sesión. */
export const HOME_POR_ROL = {
  admin: "admin-configuracion",
  mesero: "mesero-escaner",
  // El cajero hace lo del mesero y además cobra (SPEC-014); entra por caja,
  // que es lo primero que abre al llegar.
  cajero: "mesero-caja",
  cocina: "estacion-tablero",
};

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "cliente-menu",
      component: () => import("../views/ClienteMenu.vue"),
    },
    {
      // Entrada por QR de mesa (SPEC-001): mismo componente, con la mesa
      // ya identificada por el código en la URL.
      path: "/m/:codigo",
      name: "cliente-mesa",
      component: () => import("../views/ClienteMenu.vue"),
    },
    {
      path: "/mesero",
      name: "mesero-escaner",
      component: () => import("../views/mesero/MeseroEscaner.vue"),
      meta: { roles: ["admin", "mesero", "cajero"] },
    },
    {
      // Turno de caja (SPEC-014): abrir, movimientos y cuadre.
      path: "/mesero/caja",
      name: "mesero-caja",
      component: () => import("../views/mesero/MeseroCaja.vue"),
      meta: { roles: ["admin", "mesero", "cajero"] },
    },
    {
      // El libro de caja (SPEC-014): que entro y salio, con filtros, y el
      // traslado entre cajas. Separado del turno porque se consulta en otro
      // momento — el turno se abre y se cierra, el libro se revisa.
      path: "/mesero/libro",
      name: "mesero-libro",
      component: () => import("../views/mesero/MeseroLibro.vue"),
      meta: { roles: ["admin", "mesero", "cajero"] },
    },
    {
      // Activos liquidos (SPEC-020): cuanta plata hay ahora y donde. El Libro
      // dice como se llego ahi; esta pantalla dice donde se quedo.
      path: "/mesero/activos",
      name: "mesero-activos",
      component: () => import("../views/mesero/MeseroActivos.vue"),
      meta: { roles: ["admin", "mesero", "cajero"] },
    },
    {
      // Historial de ventas (SPEC-015): que se vendio, cuando y por que
      // medio. Nada que ver con la DIAN — es el historial interno.
      path: "/mesero/ventas",
      name: "mesero-ventas",
      component: () => import("../views/mesero/MeseroVentas.vue"),
      meta: { roles: ["admin", "mesero", "cajero"] },
    },
    {
      // Los cuatro reportes de venta (SPEC-018), con graficos.
      path: "/mesero/reportes",
      name: "mesero-reportes",
      component: () => import("../views/mesero/MeseroReportes.vue"),
      meta: { roles: ["admin", "mesero", "cajero"] },
    },
    {
      // Directorio de clientes (SPEC-019). Se crean solos al confirmar un
      // domicilio; aqui se consultan, corrigen y borran.
      path: "/mesero/clientes",
      name: "mesero-clientes",
      component: () => import("../views/mesero/MeseroClientes.vue"),
      meta: { roles: ["admin", "mesero", "cajero"] },
    },
    {
      // Cuentas por cobrar (SPEC-013): lo servido y no pagado.
      path: "/mesero/cuentas",
      name: "mesero-cuentas",
      component: () => import("../views/mesero/MeseroCuentas.vue"),
      meta: { roles: ["admin", "mesero", "cajero"] },
    },
    {
      // Registro de pedidos en curso y edición de los ya enviados (SPEC-011).
      path: "/mesero/pedidos",
      name: "mesero-pedidos",
      component: () => import("../views/mesero/MeseroPedidos.vue"),
      meta: { roles: ["admin", "mesero", "cajero"] },
    },
    {
      // Vista de salón (SPEC-012): estado de ocupación de las mesas.
      path: "/mesero/salon",
      name: "mesero-salon",
      component: () => import("../views/mesero/MeseroSalon.vue"),
      meta: { roles: ["admin", "mesero", "cajero"] },
    },
    {
      // Camino B (SPEC-004): el mesero arma el pedido desde cero cuando el
      // cliente no usó la app.
      path: "/mesero/pedido",
      name: "mesero-pedido",
      component: () => import("../views/mesero/MeseroPedido.vue"),
      meta: { roles: ["admin", "mesero", "cajero"] },
    },
    {
      path: "/estacion",
      name: "estacion-tablero",
      component: () => import("../views/estacion/EstacionTablero.vue"),
      meta: { roles: ["admin", "cocina"] },
    },
    {
      path: "/admin/login",
      name: "admin-login",
      component: () => import("../views/admin/AdminLogin.vue"),
    },
    {
      path: "/admin",
      name: "admin-configuracion",
      component: () => import("../views/admin/AdminConfiguracion.vue"),
      meta: { roles: ["admin"] },
    },
    // Secciones del panel (SPEC-007): cada una con ruta propia para poder
    // enlazar directo y que el navegador recuerde dónde estabas.
    {
      path: "/admin/menu",
      name: "admin-menu",
      component: () => import("../views/admin/AdminMenu.vue"),
      meta: { roles: ["admin"] },
    },
    {
      path: "/admin/mesas",
      name: "admin-mesas",
      component: () => import("../views/admin/AdminMesas.vue"),
      meta: { roles: ["admin"] },
    },
    {
      path: "/admin/estaciones",
      name: "admin-estaciones",
      component: () => import("../views/admin/AdminEstaciones.vue"),
      meta: { roles: ["admin"] },
    },
    {
      path: "/admin/usuarios",
      name: "admin-usuarios",
      component: () => import("../views/admin/AdminUsuarios.vue"),
      meta: { roles: ["admin"] },
    },
    {
      path: "/admin/cobro",
      name: "admin-cobro",
      component: () => import("../views/admin/AdminCobro.vue"),
      meta: { roles: ["admin"] },
    },
    {
      // Historial de turnos y cuadres (SPEC-014). En el panel de admin a
      // proposito: el cajero no audita su propio cuadre — misma separacion
      // que el sistema que se va a reemplazar.
      path: "/admin/turnos",
      name: "admin-turnos",
      component: () => import("../views/admin/AdminTurnos.vue"),
      meta: { roles: ["admin"] },
    },
  ],
});

/**
 * Guardia por rol (decisión del autor, 2026-08-25): el mesero no entra a
 * cocina, cocina no entra al mesero, y ninguno al panel de administración.
 * El backend aplica lo mismo en la API — esto es la mitad visible.
 */
router.beforeEach(async (to) => {
  const auth = useAuthStore();

  // Con sesión abierta, el login redirige a la pantalla del rol.
  if (to.name === "admin-login" && auth.autenticado && auth.rol) {
    return { name: HOME_POR_ROL[auth.rol] ?? "admin-login" };
  }

  if (!to.meta.roles) return;
  if (!auth.autenticado) return { name: "admin-login" };

  // Sesión vieja sin perfil (de antes de los roles): se resuelve una vez.
  if (!auth.rol) {
    try {
      auth.guardarPerfil(await obtenerPerfil());
    } catch {
      auth.cerrarSesion();
      return { name: "admin-login" };
    }
  }

  if (!to.meta.roles.some((rol) => auth.roles.includes(rol))) {
    return { name: HOME_POR_ROL[auth.rol] ?? "admin-login" };
  }
});

export default router;
