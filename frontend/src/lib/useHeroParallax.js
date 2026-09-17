import { ref, onMounted, onUnmounted } from "vue";

/**
 * Parallax de recorrido largo: el hero es `sticky` dentro de un contenedor
 * alto, y el progreso se mide sobre TODO ese recorrido (no sobre una
 * pantalla) para que la animación se sienta gradual.
 */
export function useHeroParallax() {
  const contenedor = ref(null);
  const fondo = ref(null);
  const contenido = ref(null);
  const flechaOculta = ref(false);
  const fueraDelHero = ref(false);

  const sinMovimiento =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let pendiente = false;

  function actualizar() {
    if (!contenedor.value) return;
    const y = window.scrollY;
    const recorrido = Math.max(contenedor.value.offsetHeight - window.innerHeight, 1);
    const p = Math.min(Math.max(y / recorrido, 0), 1);

    fueraDelHero.value = p > 0.9;

    if (!sinMovimiento) {
      if (fondo.value) {
        fondo.value.style.transform = `translateY(${p * 18}vh) scale(${1 + p * 0.12})`;
      }
      if (contenido.value) {
        // El contenido se desvanece en el primer 65% del recorrido; el resto
        // es imagen limpia antes de dar paso al menú.
        const pc = Math.min(p / 0.65, 1);
        contenido.value.style.opacity = String(1 - pc);
        contenido.value.style.transform = `translateY(${-pc * 90}px) scale(${1 - pc * 0.12})`;
      }
      if (!flechaOculta.value && y > 40) flechaOculta.value = true;
    }
    pendiente = false;
  }

  function alHacerScroll() {
    if (!pendiente) {
      requestAnimationFrame(actualizar);
      pendiente = true;
    }
  }

  onMounted(() => {
    window.addEventListener("scroll", alHacerScroll, { passive: true });
    window.addEventListener("resize", actualizar, { passive: true });
    actualizar();
  });

  onUnmounted(() => {
    window.removeEventListener("scroll", alHacerScroll);
    window.removeEventListener("resize", actualizar);
  });

  return { contenedor, fondo, contenido, flechaOculta, fueraDelHero };
}
