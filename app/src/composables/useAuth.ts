import { ref } from 'vue'
import { apiFetch } from '@/lib/apiFetch'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api'

const authenticated = ref(false)
const checked = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
/** Mot de passe OK, en attente du code TOTP (cookie preauth). */
const pendingTotp = ref(false)

export async function fetchMe(): Promise<boolean> {
  loading.value = true
  error.value = null
  try {
    const res = await apiFetch(`${API_BASE}/auth/me`)
    authenticated.value = res.ok
    checked.value = true
    if (res.ok) pendingTotp.value = false
    return res.ok
  } catch {
    authenticated.value = false
    checked.value = true
    error.value = 'Impossible de joindre l’API'
    return false
  } finally {
    loading.value = false
  }
}

async function readDetail(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json()
    if (body?.detail) return String(body.detail)
  } catch {
    /* ignore */
  }
  return fallback
}

/** Étape 1 : mot de passe → preauth (pas encore authentifié). */
export async function login(password: string): Promise<boolean> {
  loading.value = true
  error.value = null
  try {
    const res = await apiFetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    })
    if (!res.ok) {
      error.value = await readDetail(res, 'Mot de passe incorrect')
      authenticated.value = false
      pendingTotp.value = false
      return false
    }
    authenticated.value = false
    pendingTotp.value = true
    return true
  } catch {
    error.value = 'Impossible de joindre l’API'
    authenticated.value = false
    pendingTotp.value = false
    return false
  } finally {
    loading.value = false
  }
}

/** Étape 2 : code Google Authenticator → session. */
export async function verifyTotp(code: string): Promise<boolean> {
  loading.value = true
  error.value = null
  try {
    const res = await apiFetch(`${API_BASE}/auth/totp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    })
    if (!res.ok) {
      error.value = await readDetail(res, 'Code incorrect')
      authenticated.value = false
      return false
    }
    authenticated.value = true
    pendingTotp.value = false
    checked.value = true
    return true
  } catch {
    error.value = 'Impossible de joindre l’API'
    authenticated.value = false
    return false
  } finally {
    loading.value = false
  }
}

export async function logout(): Promise<void> {
  try {
    await apiFetch(`${API_BASE}/auth/logout`, { method: 'POST' })
  } finally {
    authenticated.value = false
    pendingTotp.value = false
  }
}

export function useAuth() {
  return {
    authenticated,
    checked,
    loading,
    error,
    pendingTotp,
    fetchMe,
    login,
    verifyTotp,
    logout,
  }
}
