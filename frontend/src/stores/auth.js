import { defineStore } from "pinia";

const CLAVE_TOKEN = "terra_admin_token";
const CLAVE_PERFIL = "terra_perfil";

function perfilGuardado() {
  try {
    return JSON.parse(localStorage.getItem(CLAVE_PERFIL)) || null;
  } catch {
    return null;
  }
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem(CLAVE_TOKEN) || null,
    perfil: perfilGuardado(), // usuario, rol, roles y puede_cobrar
  }),

  getters: {
    autenticado: (s) => !!s.token,
    rol: (s) => s.perfil?.rol ?? null,
    roles: (s) => s.perfil?.roles ?? (s.perfil?.rol ? [s.perfil.rol] : []),
    puedeCobrar: (s) => s.perfil?.puede_cobrar ?? false,
    usuario: (s) => s.perfil?.usuario ?? null,
  },

  actions: {
    guardarToken(token) {
      this.token = token;
      localStorage.setItem(CLAVE_TOKEN, token);
    },

    guardarPerfil(perfil) {
      this.perfil = perfil;
      localStorage.setItem(CLAVE_PERFIL, JSON.stringify(perfil));
    },

    cerrarSesion() {
      this.token = null;
      this.perfil = null;
      localStorage.removeItem(CLAVE_TOKEN);
      localStorage.removeItem(CLAVE_PERFIL);
    },
  },
});
