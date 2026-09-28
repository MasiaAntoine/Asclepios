import { computed, ref } from 'vue'
import { apiFetch } from '@/lib/apiFetch'
import { fetchJson, fetchText } from '@/lib/dataClient'
import { parseFrDate } from '@/lib/chartTheme'
import { VAULT } from '@/lib/vault'
import { reloadProfile, useProfile } from '@/composables/useProfile'
import { formatPoidsNotify } from '@/lib/poids'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api'

export interface PoidsEntry {
  date: string
  dateObj: Date
  poids_kg: number
  imc: number | null
}

function calcImc(poidsKg: number, tailleCm: number): number {
  const m = tailleCm / 100
  return poidsKg / (m * m)
}

function parsePoidsCsv(raw: string, tailleCm: number): PoidsEntry[] {
  return raw
    .trim()
    .split('\n')
    .slice(1)
    .map((line) => {
      const [date, poids] = line.split(',')
      const dateObj = parseFrDate(date?.trim() ?? '')
      const poids_kg = parseFloat(poids)
      if (!dateObj || Number.isNaN(poids_kg)) return null
      return {
        date: date.trim(),
        dateObj,
        poids_kg,
        imc: tailleCm ? calcImc(poids_kg, tailleCm) : null,
      }
    })
    .filter((e): e is PoidsEntry => e !== null)
    .sort((a, b) => a.dateObj.getTime() - b.dateObj.getTime())
}

const entries = ref<PoidsEntry[]>([])
const tailleCm = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)
let loaded = false

async function load() {
  if (loaded || loading.value) return
  loading.value = true
  error.value = null
  try {
    const [profil, poidsRaw] = await Promise.all([
      fetchJson<{ taille_cm: number }>(VAULT.profil),
      fetchText(VAULT.poids),
    ])
    tailleCm.value = profil.taille_cm
    entries.value = parsePoidsCsv(poidsRaw, profil.taille_cm)
    loaded = true
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erreur de chargement'
  } finally {
    loading.value = false
  }
}

export async function reloadPoids() {
  loaded = false
  return load()
}

export function usePoids() {
  const { profil } = useProfile()
  if (!loaded && !loading.value) void load()

  const premier = computed(() => entries.value[0] ?? null)
  const dernier = computed(() =>
    entries.value.length ? entries.value[entries.value.length - 1] : null,
  )
  const min = computed(() =>
    entries.value.length
      ? entries.value.reduce((a, b) => (a.poids_kg < b.poids_kg ? a : b))
      : null,
  )
  const max = computed(() =>
    entries.value.length
      ? entries.value.reduce((a, b) => (a.poids_kg > b.poids_kg ? a : b))
      : null,
  )
  const delta = computed(() =>
    premier.value && dernier.value
      ? Number((dernier.value.poids_kg - premier.value.poids_kg).toFixed(2))
      : null,
  )
  const deltaRecent = computed(() => {
    const e = entries.value
    if (e.length < 2) return null
    return Number((e[e.length - 1].poids_kg - e[e.length - 2].poids_kg).toFixed(2))
  })

  const notifyWeekday = computed(() => {
    const raw = profil.value?.poids_notify_weekday
    return typeof raw === 'number' && raw >= 0 && raw <= 6 ? raw : 0
  })
  const notifyAt = computed(() => (profil.value?.poids_notify_at || '').trim())
  const notifyLabel = computed(() => formatPoidsNotify(notifyWeekday.value, notifyAt.value))

  async function saveNotify(weekday: number | null, value: string) {
    const at = value.trim()
    const res = await apiFetch(`${API_BASE}/poids/notify`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        weekday: at ? weekday : null,
        notify_at: at || null,
      }),
    })
    if (!res.ok) throw new Error(`Enregistrement impossible (${res.status})`)
    const json = (await res.json()) as {
      poids_notify_weekday?: number | null
      poids_notify_at?: string | null
    }
    if (profil.value) {
      if (json.poids_notify_at) {
        profil.value.poids_notify_at = json.poids_notify_at
        profil.value.poids_notify_weekday = json.poids_notify_weekday ?? 0
      } else {
        delete profil.value.poids_notify_at
        delete profil.value.poids_notify_weekday
      }
    }
    await reloadProfile()
  }

  return {
    entries,
    tailleCm,
    premier,
    dernier,
    min,
    max,
    delta,
    deltaRecent,
    notifyWeekday,
    notifyAt,
    notifyLabel,
    loading,
    error,
    load,
    reload: reloadPoids,
    saveNotify,
  }
}
