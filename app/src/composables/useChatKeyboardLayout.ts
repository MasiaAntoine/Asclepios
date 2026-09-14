import { onMounted, onUnmounted, ref, type CSSProperties, type Ref } from 'vue'

/**
 * Remonte la zone chat au-dessus du clavier mobile via padding-bottom
 * (sans transform / hauteur viewport qui déborde sous l’écran).
 */
export function useChatKeyboardLayout(scrollEl: Ref<HTMLElement | null>) {
  const shellStyle = ref<CSSProperties>({ height: '100%' })
  const keyboardOpen = ref(false)
  let raf = 0

  function sync() {
    cancelAnimationFrame(raf)
    raf = requestAnimationFrame(() => {
      const vv = window.visualViewport
      const isCompact = window.matchMedia('(max-width: 767px)').matches

      if (!vv || !isCompact) {
        shellStyle.value = { height: '100%', paddingBottom: '0px' }
        keyboardOpen.value = false
        return
      }

      // Espace couvert par le clavier (bas de l’écran layout vs visualViewport)
      const inset = Math.max(0, window.innerHeight - vv.height - vv.offsetTop)
      const open = inset > 60
      keyboardOpen.value = open

      shellStyle.value = {
        height: '100%',
        // Remonte le composer au-dessus du clavier ; le parent (main) garde déjà le header app
        paddingBottom: open ? `${Math.round(inset)}px` : '0px',
        boxSizing: 'border-box',
        transition: 'none',
      }

      if (open && scrollEl.value) {
        scrollEl.value.scrollTop = scrollEl.value.scrollHeight
      }
    })
  }

  function onFocusIn(event: FocusEvent) {
    const target = event.target
    if (!(target instanceof HTMLTextAreaElement) && !(target instanceof HTMLInputElement)) {
      return
    }
    window.setTimeout(() => {
      sync()
      if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
    }, 50)
    window.setTimeout(() => {
      sync()
      if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
    }, 350)
  }

  onMounted(() => {
    sync()
    const vv = window.visualViewport
    vv?.addEventListener('resize', sync)
    vv?.addEventListener('scroll', sync)
    window.addEventListener('resize', sync)
    window.addEventListener('orientationchange', sync)
    document.addEventListener('focusin', onFocusIn)
  })

  onUnmounted(() => {
    cancelAnimationFrame(raf)
    const vv = window.visualViewport
    vv?.removeEventListener('resize', sync)
    vv?.removeEventListener('scroll', sync)
    window.removeEventListener('resize', sync)
    window.removeEventListener('orientationchange', sync)
    document.removeEventListener('focusin', onFocusIn)
  })

  return { shellStyle, keyboardOpen, syncViewport: sync }
}
