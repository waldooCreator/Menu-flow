<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { iniciarSesion, obtenerPerfil } from "../../api/auth";
import { obtenerConfiguracionPublica } from "../../api/configuracion";
import { aplicarTemaCliente } from "../../lib/tema";
import { useAuthStore } from "../../stores/auth";
import { HOME_POR_ROL } from "../../router";

const usuario = ref("");
const clave = ref("");
const error = ref(null);
const enviando = ref(false);
const nombre = ref("");

const auth = useAuthStore();
const router = useRouter();

onMounted(async () => {
  try {
    const cfg = await obtenerConfiguracionPublica();
    aplicarTemaCliente(cfg);
    nombre.value = cfg["nombre-restaurante"] || "";
  } catch {
    // Los valores por defecto de :root cubren si la API no responde.
  }
});

async function enviar() {
  error.value = null;
  enviando.value = true;
  try {
    auth.guardarToken(await iniciarSesion(usuario.value, clave.value));
    const perfil = await obtenerPerfil();
    auth.guardarPerfil(perfil);
    // Cada rol entra directo a SU pantalla: mesero, cocina o admin.
    router.push({ name: HOME_POR_ROL[perfil.rol] ?? "admin-login" });
  } catch {
    auth.cerrarSesion();
    error.value = "Usuario o contraseña incorrectos.";
  } finally {
    enviando.value = false;
  }
}
</script>

<template>
  <div class="grid min-h-screen place-items-center bg-lienzo px-4 font-sans text-tinta">
    <form
      @submit.prevent="enviar"
      class="flex w-full max-w-95 flex-col gap-4 rounded-3xl border border-marca/10 bg-white p-9"
    >
      <div class="mb-1 text-center">
        <p class="font-display text-4xl font-light text-marca">{{ nombre || "…" }}</p>
        <p class="mt-2 text-[11px] font-semibold tracking-[0.18em] text-marca/60 uppercase">
          Acceso del equipo
        </p>
      </div>

      <label class="flex flex-col gap-1.5 text-[13px] font-medium text-marca/80">
        Usuario
        <input
          v-model="usuario" type="text" autocomplete="username" required
          class="rounded-xl border border-marca/15 px-4 py-3 text-[15px] text-tinta outline-none focus:border-marca"
        />
      </label>

      <label class="flex flex-col gap-1.5 text-[13px] font-medium text-marca/80">
        Contraseña
        <input
          v-model="clave" type="password" autocomplete="current-password" required
          class="rounded-xl border border-marca/15 px-4 py-3 text-[15px] text-tinta outline-none focus:border-marca"
        />
      </label>

      <p v-if="error" class="text-[13px] font-semibold text-alerta">{{ error }}</p>

      <button
        type="submit" :disabled="enviando"
        class="mt-1 min-h-13 cursor-pointer rounded-full bg-marca text-sm font-semibold tracking-[0.10em] text-lienzo uppercase transition-transform active:scale-[0.985] disabled:opacity-60"
      >{{ enviando ? "Entrando…" : "Entrar" }}</button>
    </form>
  </div>
</template>
