import { ref } from 'vue'
import { apiFetch } from '@/lib/apiFetch'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api'

export type PushKind =
  | 'idle'
  | 'unsupported'
  | 'needs-home'
  | 'prompt'
  | 'denied'
  | 'subscribed'
  | 'error'

const kind = ref<PushKind>('idle')
const error = ref<string | null>(null)
const loading = ref(false)
const configured = ref(false)
const dialogOpen = ref(false)
const dismissedThisVisit = ref(false)

function isIosDevice() {
  const ua = navigator.userAgent || ''
  if (/iPad|iPhone|iPod/.test(ua)) return true
  return navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1
}

function isStandalonePwa() {
  const nav = navigator as Navigator & { standalone?: boolean }
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    nav.standalone === true
  )
}

function urlBase64ToUint8Array(base64String: string) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  const output = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i += 1) {
    output[i] = raw.charCodeAt(i)
  }
  return output
}

async function fetchVapidPublicKey(): Promise<string | null> {
  const res = await apiFetch(`${API_BASE}/push/vapid-public-key`)
  if (res.status === 503) {
    configured.value = false
    return null
  }
  if (!res.ok) throw new Error(`Clé VAPID indisponible (${res.status})`)
  const body = (await res.json()) as { publicKey?: string }
  const key = body.publicKey?.trim() || ''
  configured.value = Boolean(key)
  return key || null
}

async function postSubscription(sub: PushSubscription) {
  const json = sub.toJSON()
  const endpoint = json.endpoint
  const p256dh = json.keys?.p256dh
  const auth = json.keys?.auth
  if (!endpoint || !p256dh || !auth) {
    throw new Error('Abonnement push incomplet')
  }
  const res = await apiFetch(`${API_BASE}/push/subscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      endpoint,
      keys: { p256dh, auth },
    }),
  })
  if (!res.ok) throw new Error(`Enregistrement impossible (${res.status})`)
}

export async function syncPushSubscription(): Promise<PushKind> {
  error.value = null

  if (typeof window === 'undefined' || !('serviceWorker' in navigator) || !('PushManager' in window)) {
    kind.value = 'unsupported'
    return kind.value
  }

  if (isIosDevice() && !isStandalonePwa()) {
    kind.value = 'needs-home'
    return kind.value
  }

  if (typeof Notification === 'undefined') {
    kind.value = 'unsupported'
    return kind.value
  }

  const permission = Notification.permission
  if (permission === 'denied') {
    kind.value = 'denied'
    return kind.value
  }

  try {
    const publicKey = await fetchVapidPublicKey()
    if (!publicKey) {
      kind.value = 'error'
      error.value = 'Notifications non configurées sur le serveur.'
      return kind.value
    }
  } catch (e) {
    kind.value = 'error'
    error.value = e instanceof Error ? e.message : 'Serveur injoignable'
    return kind.value
  }

  if (permission !== 'granted') {
    kind.value = 'prompt'
    return kind.value
  }

  try {
    const ready = await navigator.serviceWorker.ready
    let sub = await ready.pushManager.getSubscription()
    if (!sub) {
      const publicKey = await fetchVapidPublicKey()
      if (!publicKey) {
        kind.value = 'error'
        return kind.value
      }
      sub = await ready.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      })
    }
    await postSubscription(sub)
    kind.value = 'subscribed'
    dialogOpen.value = false
    return kind.value
  } catch (e) {
    kind.value = 'error'
    error.value = e instanceof Error ? e.message : 'Abonnement impossible'
    return kind.value
  }
}

export async function enablePush(): Promise<boolean> {
  loading.value = true
  error.value = null
  try {
    if (isIosDevice() && !isStandalonePwa()) {
      kind.value = 'needs-home'
      return false
    }
    if (!('Notification' in window)) {
      kind.value = 'unsupported'
      return false
    }
    const permission = await Notification.requestPermission()
    if (permission !== 'granted') {
      kind.value = permission === 'denied' ? 'denied' : 'prompt'
      return false
    }
    const next = await syncPushSubscription()
    return next === 'subscribed'
  } catch (e) {
    kind.value = 'error'
    error.value = e instanceof Error ? e.message : 'Permission refusée'
    return false
  } finally {
    loading.value = false
  }
}

export function dismissPushDialog() {
  dismissedThisVisit.value = true
  dialogOpen.value = false
}

export function maybeOpenPushDialog() {
  if (dismissedThisVisit.value) return
  if (kind.value === 'subscribed' || kind.value === 'unsupported' || kind.value === 'idle') return
  dialogOpen.value = true
}

export async function sendTestPush() {
  const res = await apiFetch(`${API_BASE}/push/test`, { method: 'POST' })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error((body && body.detail) || `Test impossible (${res.status})`)
  }
}

export function usePushSubscription() {
  return {
    kind,
    error,
    loading,
    configured,
    dialogOpen,
    dismissedThisVisit,
    isIosDevice,
    isStandalonePwa,
    syncPushSubscription,
    enablePush,
    dismissPushDialog,
    maybeOpenPushDialog,
    sendTestPush,
  }
}
