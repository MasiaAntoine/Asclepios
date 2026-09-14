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

// Attendre la garde auth (fetch /me + éventuelle redirect) avant le premier rendu
router.isReady().then(() => {
  app.mount('#app')
})
