/** Destinos del personal agrupados por tarea (SPEC-021). */
export const GRUPOS = [
  {
    id: "servicio",
    titulo: "Servicio",
    destinos: [
      { ruta: "mesero-escaner", texto: "Recibir pedido", roles: ["admin", "mesero", "cajero"], icono: "qr" },
      { ruta: "mesero-salon", texto: "Salón", roles: ["admin", "mesero", "cajero"], icono: "salon" },
      { ruta: "mesero-pedidos", texto: "Pedidos", roles: ["admin", "mesero", "cajero"], icono: "pedido" },
      { ruta: "mesero-cuentas", texto: "Cuentas", roles: ["admin", "mesero", "cajero"], icono: "cuenta" },
    ],
  },
  {
    id: "caja",
    titulo: "Caja",
    requiereCobro: true,
    destinos: [
      { ruta: "mesero-caja", texto: "Turno", roles: ["admin", "mesero", "cajero"], icono: "turno" },
      { ruta: "mesero-libro", texto: "Libro", roles: ["admin", "mesero", "cajero"], icono: "libro" },
      { ruta: "mesero-activos", texto: "Activos", roles: ["admin", "mesero", "cajero"], icono: "activos" },
    ],
  },
  {
    id: "negocio",
    titulo: "Negocio",
    requiereCobro: true,
    destinos: [
      { ruta: "mesero-ventas", texto: "Ventas", roles: ["admin", "mesero", "cajero"], icono: "ventas" },
      { ruta: "mesero-reportes", texto: "Reportes", roles: ["admin", "mesero", "cajero"], icono: "reporte" },
      { ruta: "mesero-clientes", texto: "Clientes", roles: ["admin", "mesero", "cajero"], icono: "clientes" },
    ],
  },
  {
    id: "cocina",
    titulo: "Cocina",
    destinos: [
      { ruta: "estacion-tablero", texto: "Tablero", roles: ["admin", "cocina"], icono: "cocina" },
    ],
  },
  {
    id: "ajustes",
    titulo: "Ajustes",
    destinos: [
      { ruta: "admin-configuracion", texto: "Administración", roles: ["admin"], icono: "ajustes" },
    ],
  },
];

export function gruposVisibles(perfil = {}) {
  const roles = new Set(perfil.roles ?? (perfil.rol ? [perfil.rol] : []));
  return GRUPOS.map((grupo) => {
    const puedeVerCaja = !grupo.requiereCobro || perfil.puede_cobrar || roles.has("admin");
    const destinos = puedeVerCaja
      ? grupo.destinos.filter((destino) => destino.roles.some((rol) => roles.has(rol)))
      : [];
    return { ...grupo, destinos };
  }).filter((grupo) => grupo.destinos.length > 0);
}
