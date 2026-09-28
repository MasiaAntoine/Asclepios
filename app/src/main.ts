import { createApp } from 'vue'
import { registerSW } from 'virtual:pwa-register'
import App from './App.vue'
import router from './router'
import { lockMobileViewport } from './lib/lockMobileViewport'
import './style.css'

lockMobileViewport()
registerSW({ immediate: true })

const app = createApp(App)
app.use(router)

if (typeof navigator !== 'undefined' && 'serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('message', (event) => {
    const data = event.data
    if (!data || data.type !== 'navigate') return
    const url = String(data.url || '')
    if (!url.startsWith('/')) return
    void router.push(url)
  })
}

// Attendre la garde auth (fetch /me + éventuelle redirect) avant le premier rendu
router.isReady().then(() => {
  app.mount('#app')
})
