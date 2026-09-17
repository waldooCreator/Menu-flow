/**
 * Cliente HTTP único hacia la API de Django. Todo el frontend —página del
 * cliente, panel de mesero/estación, panel de administración— pasa por
 * aquí. Django es solo API y permisos (ADR-006); nada se renderiza en
 * el servidor.
 */

import axios from "axios";
import { useAuthStore } from "../stores/auth";

const cliente = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

// El token se agrega en cada petición si hay sesión — no se guarda un
// cliente distinto para "modo autenticado" vs "modo público": la misma
// instancia sirve para ambos, según haya o no token.
cliente.interceptors.request.use((config) => {
  const auth = useAuthStore();
  if (auth.token) {
    config.headers.Authorization = `Token ${auth.token}`;
  }
  return config;
});

// Si el token expiró o es inválido, se cierra la sesión local — evita
// quedar en un estado donde el panel cree que hay sesión pero la API
// la rechaza en cada petición.
cliente.interceptors.response.use(
  (respuesta) => respuesta,
  (error) => {
    if (error.response?.status === 401) {
      const auth = useAuthStore();
      auth.cerrarSesion();
    }
    return Promise.reject(error);
  }
);

export default cliente;
