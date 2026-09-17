<script setup>
/**
 * Personal del restaurante (SPEC-007): meseros y cocina. Hasta hoy,
 * contratar a alguien exigía la terminal del servidor.
 *
 * Deliberadamente simple: usuario, clave, rol, activo. La clave la fija y
 * restablece el administrador en persona — sin correos de recuperación,
 * que es como funciona un restaurante real.
 *
 * No hay borrar: toda venta tiene un responsable (regla del proyecto), así
 * que quien se va se DESACTIVA — no entra más, pero su historial queda.
 */
import { onMounted, ref } from "vue";
import { listarUsuarios, guardarUsuario, restablecerClave } from "../../api/administracion";
import MarcoInterno from "../../components/MarcoInterno.vue";
import AdminPestanas from "../../components/AdminPestanas.vue";

const usuarios = ref([]);
const cargando = ref(true);
const mensaje = ref(null);

const nuevo = ref({ username: "", password: "", rol: "mesero" });
const cambiandoClave = ref(null); // id
const claveNueva = ref("");

const ETIQUETA_ROL = { mesero: "Mesero", cocina: "Cocina" };

function avisar(texto, error = false) {
  mensaje.value = { texto, error };
  setTimeout(() => (mensaje.value = null), 3500);
}

async function cargar() {
  usuarios.value = await listarUsuarios();
  cargando.value = false;
}

async function crear() {
  const { username, password, rol } = nuevo.value;
  if (!username.trim() || password.length < 6) {
    avisar("Usuario y una clave de al menos 6 caracteres.", true);
    return;
  }
  try {
    await guardarUsuario(null, { username: username.trim(), password, rol });
    nuevo.value = { username: "", password: "", rol: "mesero" };
    await cargar();
    avisar("Usuario creado — entrégale su clave en persona");
  } catch (e) {
    avisar(e.response?.data?.username?.[0] || "No se pudo crear.", true);
  }
}

async function cambiarRol(u, rol) {
  await guardarUsuario(u.id, { rol });
  await cargar();
  avisar(`${u.username} ahora es ${ETIQUETA_ROL[rol]}`);
}

async function alternarActivo(u) {
  u.is_active = !u.is_active;
  try {
    await guardarUsuario(u.id, { is_active: u.is_active });
    avisar(u.is_active ? `${u.username} puede entrar de nuevo` : `${u.username} ya no puede entrar — su historial queda`);
  } catch {
    u.is_active = !u.is_active;
    avisar("No se pudo cambiar.", true);
  }
}

async function guardarClave(u) {
  try {
    await restablecerClave(u.id, claveNueva.value);
    cambiandoClave.value = null;
    claveNueva.value = "";
    avisar(`Clave de ${u.username} actualizada`);
  } catch (e) {
    avisar(e.response?.data?.detalle || "No se pudo cambiar la clave.", true);
  }
}

onMounted(cargar);
</script>

<template>
  <MarcoInterno titulo="Personal" ancho="max-w-2xl">
    <AdminPestanas />

    <Transition
      enter-from-class="opacity-0 -translate-y-1" leave-to-class="opacity-0"
      enter-active-class="transition duration-200" leave-active-class="transition duration-200"
    >
      <p
        v-if="mensaje"
        class="mb-4 rounded-lg px-3.5 py-2.5 text-sm font-semibold"
        :class="mensaje.error ? 'bg-alerta/8 text-alerta' : 'bg-panel-marca/8 text-panel-marca'"
      >{{ mensaje.texto }}</p>
    </Transition>

    <p v-if="cargando" class="py-8 text-panel-tinta/50">Cargando…</p>

    <template v-else>
      <div class="overflow-hidden rounded-xl border border-panel-borde bg-white">
        <div class="divide-y divide-panel-borde">
          <div v-for="u in usuarios" :key="u.id" class="px-4 py-3" :class="{ 'opacity-50': !u.is_active }">
            <div class="flex flex-wrap items-center gap-3">
              <p class="min-w-0 basis-full text-[14px] font-semibold sm:flex-1 sm:basis-auto">{{ u.username }}</p>

              <select
                :value="u.rol_actual" @change="cambiarRol(u, $event.target.value)"
                class="cursor-pointer rounded-lg border border-panel-borde bg-white px-2.5 py-1.5 text-[12px]"
              >
                <option value="mesero">Mesero</option>
                <option value="cocina">Cocina</option>
              </select>

              <button
                @click="cambiandoClave = cambiandoClave === u.id ? null : u.id; claveNueva = ''"
                class="cursor-pointer rounded-lg border border-panel-borde px-3 py-1.5 text-[12px] font-semibold"
              >Clave</button>

              <button
                @click="alternarActivo(u)"
                class="cursor-pointer rounded-full px-3 py-1.5 text-[11px] font-bold tracking-wide uppercase"
                :class="u.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-alerta/10 text-alerta'"
              >{{ u.is_active ? "Activo" : "Inactivo" }}</button>
            </div>

            <div v-if="cambiandoClave === u.id" class="mt-2.5 flex gap-2">
              <input
                v-model="claveNueva" type="text" maxlength="128"
                placeholder="Clave nueva (mínimo 6)…" @keyup.enter="guardarClave(u)"
                class="flex-1 rounded-lg border border-panel-borde px-3 py-2 text-sm outline-none focus:border-panel-marca"
              />
              <button
                @click="guardarClave(u)"
                class="cursor-pointer rounded-lg bg-panel-marca px-3.5 py-2 text-[12px] font-semibold text-white"
              >Cambiar</button>
            </div>
          </div>

          <p v-if="usuarios.length === 0" class="px-4 py-4 text-[13px] text-panel-tinta/40">
            Sin personal todavía.
          </p>
        </div>
      </div>

      <!-- Nuevo usuario -->
      <div class="mt-5 rounded-xl border border-panel-borde bg-white p-4">
        <h2 class="mb-3 text-[13px] font-semibold">Contratar — nuevo acceso</h2>
        <div class="flex flex-col gap-2 sm:flex-row">
          <input
            v-model="nuevo.username" type="text" maxlength="150" autocomplete="off"
            placeholder="usuario (p.ej. carlos)"
            class="flex-1 rounded-lg border border-panel-borde px-3 py-2.5 text-sm outline-none focus:border-panel-marca"
          />
          <input
            v-model="nuevo.password" type="text" maxlength="128" autocomplete="off"
            placeholder="clave (mínimo 6)"
            class="flex-1 rounded-lg border border-panel-borde px-3 py-2.5 text-sm outline-none focus:border-panel-marca"
          />
          <select
            v-model="nuevo.rol"
            class="cursor-pointer rounded-lg border border-panel-borde bg-white px-3 py-2.5 text-sm"
          >
            <option value="mesero">Mesero</option>
            <option value="cocina">Cocina</option>
          </select>
          <button
            @click="crear"
            class="cursor-pointer rounded-lg bg-panel-marca px-4 py-2.5 text-[13px] font-semibold text-white"
          >Crear</button>
        </div>
      </div>
    </template>
  </MarcoInterno>
</template>
