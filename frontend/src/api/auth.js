import cliente from "./cliente";

export function iniciarSesion(username, password) {
  return cliente.post("/auth/login/", { username, password }).then((r) => r.data.token);
}

/** Quién soy y qué rol tengo — decide a qué pantalla entra cada usuario. */
export function obtenerPerfil() {
  return cliente.get("/auth/perfil/").then((r) => r.data);
}
