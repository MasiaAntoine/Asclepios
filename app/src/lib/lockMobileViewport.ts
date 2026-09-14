/** Comportement « app native » : pas de pinch zoom. */

export function lockMobileViewport() {
  const prevent = (event: Event) => {
    event.preventDefault()
  }

  // Safari iOS : gestes de zoom
  document.addEventListener('gesturestart', prevent, { passive: false })
  document.addEventListener('gesturechange', prevent, { passive: false })
  document.addEventListener('gestureend', prevent, { passive: false })

  // Pinch multi-touch
  document.addEventListener(
    'touchmove',
    (event) => {
      if (event.touches.length > 1) event.preventDefault()
    },
    { passive: false },
  )
}
