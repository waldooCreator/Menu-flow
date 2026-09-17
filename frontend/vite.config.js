import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

const backend = process.env.BACKEND_URL ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [vue(), tailwindcss()],

  server: {
    // Escucha en todas las interfaces de red, no solo en localhost: es lo que
    // permite abrir el sistema desde el celular usando la IP del PC.
    host: true,

    /**
     * El frontend pide a rutas relativas (`/api`, `/media`) y Vite las
     * reenvía a Django. Dos ventajas para la demo:
     *
     *  - Desde el celular funciona igual: la petición sale al mismo origen
     *    desde el que se cargó la página, sin tener que saber la IP del PC.
     *  - No hay CORS de por medio, porque para el navegador todo es un
     *    mismo origen.
     */
    //
    // `BACKEND_URL` permite apuntar a otro puerto cuando el 8000 ya lo usa
    // otro proyecto en el mismo PC (pasó el 2026-09-16).
    proxy: {
      '/api': { target: backend, changeOrigin: false },
      '/media': { target: backend, changeOrigin: false },
    },
  },
})
