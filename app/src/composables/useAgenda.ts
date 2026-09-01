import { computed, ref } from 'vue'

/**
 * Agenda médical en lecture seule.
 *
 * Les événements viennent du Google Agenda « Médical » via le backend
 * (`/api/agenda/events`). L'adresse secrète iCal reste côté serveur : on ne
 * crée, modifie ni stocke aucun événement ici.
 */

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api'

export interface AgendaEvent {
  uid: string
  title: string
  /** ISO : `YYYY-MM-DD` si journée entière, sinon datetime complet. */
  start: string
  end: string
  all_day: boolean
  location: string
  description: string
  status: string
  recurring: boolean
}

export interface AgendaStatus {
  configured: boolean
  env_var: string
  cache_ttl_seconds: number
  last_sync: string | null
  cached_events: number
}

interface AgendaPayload {
  events: AgendaEvent[]
  count: number
  window: { start: string; end: string }
  fetched_at: string
  stale: boolean
  error: string | null
}

// ── Utilitaires de date (sans dépendance : évite les pièges de timezone) ────

/** Clé de jour locale `YYYY-MM-DD`, stable quelle que soit la timezone. */
export function dayKey(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/** Parse une valeur iCal normalisée en Date locale. */
export function parseEventDate(value: string): Date {
  // Une date seule (`2026-09-10`) serait interprétée en UTC par `new Date()`,
  // ce qui décale le jour affiché : on la construit explicitement en local.
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [y, m, d] = value.split('-').map(Number)
    return new Date(y, m - 1, d)
  }
  return new Date(value)
}

export function eventDayKeys(event: AgendaEvent): string[] {
  const start = parseEventDate(event.start)
  const end = parseEventDate(event.end)
  const keys: string[] = []
  const cursor = new Date(start.getFullYear(), start.getMonth(), start.getDate())
  const last = new Date(end.getFullYear(), end.getMonth(), end.getDate())
  // Garde-fou : un flux malformé ne doit pas boucler indéfiniment.
  let guard = 0
  while (cursor <= last && guard < 400) {
    keys.push(dayKey(cursor))
    cursor.setDate(cursor.getDate() + 1)
    guard += 1
  }
  return keys.length ? keys : [dayKey(start)]
}

export function formatTime(event: AgendaEvent): string {
  if (event.all_day) return 'Journée'
  return parseEventDate(event.start).toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatEventRange(event: AgendaEvent): string {
  if (event.all_day) return 'Toute la journée'
  const opts: Intl.DateTimeFormatOptions = { hour: '2-digit', minute: '2-digit' }
  const start = parseEventDate(event.start).toLocaleTimeString('fr-FR', opts)
  const end = parseEventDate(event.end).toLocaleTimeString('fr-FR', opts)
  return `${start} – ${end}`
}

export function formatEventDay(event: AgendaEvent): string {
  return parseEventDate(event.start).toLocaleDateString('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })
}

/** Libellé relatif court (« Aujourd'hui », « Dans 3 jours », « Il y a 2 j »). */
export function relativeDayLabel(event: AgendaEvent): string {
  const today = new Date()
  const todayMid = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  const start = parseEventDate(event.start)
  const startMid = new Date(start.getFullYear(), start.getMonth(), start.getDate())
  const days = Math.round((startMid.getTime() - todayMid.getTime()) / 86_400_000)

  if (days === 0) return "Aujourd'hui"
  if (days === 1) return 'Demain'
  if (days === -1) return 'Hier'
  if (days > 1) return `Dans ${days} jours`
  return `Il y a ${Math.abs(days)} jours`
}

// ── État partagé ────────────────────────────────────────────────────────────

const events = ref<AgendaEvent[]>([])
const status = ref<AgendaStatus | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
/** Vrai quand on affiche un snapshot faute d'avoir pu joindre Google. */
const stale = ref(false)
const lastSync = ref<string | null>(null)
let loaded = false

async function fetchStatus() {
  try {
    const res = await fetch(`${API_BASE}/agenda/status`)
    if (res.ok) status.value = (await res.json()) as AgendaStatus
  } catch {
    // Statut non bloquant : l'erreur utile viendra de /events.
  }
}

async function load(refresh = false) {
  if (loading.value) return
  loading.value = true
  error.value = null
  try {
    const url = new URL(`${API_BASE}/agenda/events`, window.location.origin)
    if (refresh) url.searchParams.set('refresh', 'true')

    const res = await fetch(url.toString().replace(window.location.origin, ''))
    if (!res.ok) {
      let detail = `Erreur ${res.status}`
      try {
        const body = await res.json()
        if (body?.detail) detail = String(body.detail)
      } catch {
        // réponse non JSON : on garde le code HTTP
      }
      throw new Error(detail)
    }

    const payload = (await res.json()) as AgendaPayload
    events.value = payload.events ?? []
    stale.value = Boolean(payload.stale)
    lastSync.value = payload.fetched_at ?? null
    if (payload.stale && payload.error) error.value = payload.error
    loaded = true
  } catch (e) {
    events.value = []
    error.value = e instanceof Error ? e.message : "Impossible de charger l'agenda"
  } finally {
    loading.value = false
  }
}

export function useAgenda() {
  if (!loaded && !loading.value) {
    void fetchStatus()
    void load()
  }

  /** Index jour → événements, pour la grille du mois. */
  const eventsByDay = computed(() => {
    const map = new Map<string, AgendaEvent[]>()
    for (const event of events.value) {
      for (const key of eventDayKeys(event)) {
        const bucket = map.get(key)
        if (bucket) bucket.push(event)
        else map.set(key, [event])
      }
    }
    for (const bucket of map.values()) {
      bucket.sort((a, b) => {
        if (a.all_day !== b.all_day) return a.all_day ? -1 : 1
        return a.start.localeCompare(b.start)
      })
    }
    return map
  })

  const upcoming = computed(() => {
    const today = dayKey(new Date())
    return events.value
      .filter((e) => e.start.slice(0, 10) >= today)
      .sort((a, b) => a.start.localeCompare(b.start))
  })

  const past = computed(() => {
    const today = dayKey(new Date())
    return events.value
      .filter((e) => e.start.slice(0, 10) < today)
      .sort((a, b) => b.start.localeCompare(a.start))
  })

  const nextEvent = computed(() => upcoming.value[0] ?? null)

  return {
    events,
    eventsByDay,
    upcoming,
    past,
    nextEvent,
    status,
    loading,
    error,
    stale,
    lastSync,
    reload: (refresh = true) => load(refresh),
  }
}
