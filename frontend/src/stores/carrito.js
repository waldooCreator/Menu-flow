import { defineStore } from "pinia";

/**
 * Carrito en memoria únicamente — como manda SPEC-002: el pedido no existe
 * en base de datos hasta que el mesero lo confirma. Recargar la página lo
 * pierde, a propósito.
 */
export const useCarritoStore = defineStore("carrito", {
  state: () => ({
    mesaCodigo: null,
    mesaNombre: null,
    nombreCliente: "",
    items: [], // [{ plato, cantidad, observaciones: string[], nota: string }]
  }),

  getters: {
    totalUnidades: (s) => s.items.reduce((n, i) => n + i.cantidad, 0),
    totalPrecio: (s) => s.items.reduce((t, i) => t + i.plato.precio * i.cantidad, 0),
    itemsAgotados: (s) => s.items.filter((i) => !i.plato.disponible),
    nombresAgotados: (s) => s.items
      .filter((i) => !i.plato.disponible)
      .map((i) => i.plato.nombre),
    /** Cuántas unidades de un plato hay en el carrito (0 si no está). */
    cantidadDe: (s) => (platoId) =>
      s.items.find((i) => i.plato.id === platoId)?.cantidad ?? 0,
  },

  actions: {
    fijarMesa(codigo, nombre) {
      this.mesaCodigo = codigo;
      this.mesaNombre = nombre;
    },

    agregar(plato) {
      const existente = this.items.find((i) => i.plato.id === plato.id);
      if (existente) existente.cantidad += 1;
      else this.items.push({ plato, cantidad: 1, observaciones: [], nota: "" });
    },

    cambiarCantidad(platoId, delta) {
      const item = this.items.find((i) => i.plato.id === platoId);
      if (!item) return;
      item.cantidad += delta;
      if (item.cantidad <= 0) {
        this.items = this.items.filter((i) => i.plato.id !== platoId);
      }
    },

    alternarObservacion(platoId, texto) {
      const item = this.items.find((i) => i.plato.id === platoId);
      if (!item) return;
      const i = item.observaciones.indexOf(texto);
      if (i === -1) item.observaciones.push(texto);
      else item.observaciones.splice(i, 1);
    },

    /** Forma compacta para el endpoint de firma — solo IDs y cantidades (SPEC-002). */
    aItemsParaFirmar() {
      return this.items.map((i) => ({
        plato_id: i.plato.id,
        cantidad: i.cantidad,
        observacion: [...i.observaciones, i.nota].filter(Boolean).join(", "),
      }));
    },

    vaciar() {
      this.items = [];
      this.nombreCliente = "";
    },
  },
});
