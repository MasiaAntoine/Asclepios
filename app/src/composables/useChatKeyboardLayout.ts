import { onMounted, onUnmounted, ref, type CSSProperties, type Ref } from 'vue'

/**
 * Ancre le layout chat dans le visualViewport (clavier mobile iOS/Android)
 * pour éviter le décalage / le contenu caché derrière le clavier.
 */
export function useChatKeyboardLayout(scrollEl: Ref<HTMLElement | null>) {
  const shellStyle = ref<CSSProperties>({})
  const keyboardOpen = ref(false)
  let raf = 0

  function sync() {
    cancelAnimationFrame(raf)
    raf = requestAnimationFrame(() => {
      const vv = window.visualViewport
      if (!vv) {
        shellStyle.value = { height: '100%' }
        keyboardOpen.value = false
        return
      }

      // Mobile / tablette étroite uniquement
      const isCompact = window.matchMedia('(max-width: 767px)').matches
      if (!isCompact) {
        shellStyle.value = { height: '100%', transform: 'none' }
        keyboardOpen.value = false
        return
      }

      const inset = Math.max(0, window.innerHeight - vv.height - vv.offsetTop)
      keyboardOpen.value = inset > 80

      shellStyle.value = {
        height: `${Math.round(vv.height)}px`,
        transform: `translateY(${Math.round(vv.offsetTop)}px)`,
        transition: 'none',
      }

      if (keyboardOpen.value && scrollEl.value) {
        scrollEl.value.scrollTop = scrollEl.value.scrollHeight
      }
    })
  }

  function onFocusIn(event: FocusEvent) {
    const target = event.target
    if (!(target instanceof HTMLTextAreaElement) && !(target instanceof HTMLInputElement)) {
      return
    }
    // Laisser le clavier s’ouvrir puis resync + scroll
    window.setTimeout(() => {
      sync()
      if (scrollEl.value) {
        scrollEl.value.scrollTop = scrollEl.value.scrollHeight
      }
    }, 50)
    window.setTimeout(sync, 300)
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
