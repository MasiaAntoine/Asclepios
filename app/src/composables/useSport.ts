import { computed, onMounted, onUnmounted, ref } from 'vue'
import { apiFetch } from '@/lib/apiFetch'
import { dataUrl } from '@/lib/dataClient'
import { todayIso } from '@/lib/mood'
import { formatNotifyAt, type SportExercise } from '@/lib/sport'
import { VAULT } from '@/lib/vault'
import { reloadProfile, useProfile } from '@/composables/useProfile'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api'

export interface SportLogItem {
  exercise_id: string
  done: boolean
  name?: string
  sets?: number
  reps?: number | null
  seconds?: number | null
  note?: string
}

export interface SportSession {
  date: string
  at: string
  items: SportLogItem[]
}

const exercises = ref<SportExercise[]>([])
const sessions = ref<SportSession[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const clock = ref(Date.now())
let loaded = false
let loadPromise: Promise<void> | null = null
let clockTimer: ReturnType<typeof setInterval> | null = null
let clockUsers = 0

function asExercise(raw: unknown): SportExercise | null {
  if (!raw || typeof raw !== 'object') return null
  const row = raw as Record<string, unknown>
  const name = String(row.name || '').trim()
  const id = String(row.id || '').trim()
  if (!name || !id) return null
  const sets = Number(row.sets) || 1
  const reps = row.reps == null || row.reps === '' ? null : Number(row.reps)
  const seconds = row.seconds == null || row.seconds === '' ? null : Number(row.seconds)
  return {
    id,
    name,
    sets: Math.max(1, sets),
    reps: Number.isFinite(reps) && (reps as number) > 0 ? (reps as number) : null,
    seconds: Number.isFinite(seconds) && (seconds as number) > 0 ? (seconds as number) : null,
    note: String(row.note || '').trim(),
  }
}

function asSession(raw: unknown): SportSession | null {
  if (!raw || typeof raw !== 'object') return null
  const row = raw as Record<string, unknown>
  const date = String(row.date || '')
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return null
  const itemsRaw = Array.isArray(row.items) ? row.items : []
  const items: SportLogItem[] = []
  const seen = new Set<string>()
  for (const item of itemsRaw) {
    if (!item || typeof item !== 'object' || !('done' in item)) continue
    const rec = item as Record<string, unknown>
    const exerciseId = String(rec.exercise_id || '').trim()
    if (!exerciseId || seen.has(exerciseId)) continue
    seen.add(exerciseId)
    items.push({
      exercise_id: exerciseId,
      done: Boolean(rec.done),
      name: String(rec.name || '').trim() || undefined,
      sets: Number.isFinite(Number(rec.sets)) && Number(rec.sets) > 0 ? Number(rec.sets) : undefined,
      reps:
        rec.reps == null || rec.reps === ''
          ? null
          : Number.isFinite(Number(rec.reps)) && Number(rec.reps) > 0
            ? Number(rec.reps)
            : null,
      seconds:
        rec.seconds == null || rec.seconds === ''
          ? null
          : Number.isFinite(Number(rec.seconds)) && Number(rec.seconds) > 0
            ? Number(rec.seconds)
            : null,
      note: String(rec.note || '').trim() || undefined,
    })
  }
  return { date, at: String(row.at || ''), items }
}

async function loadSport(force = false) {
  if (!force && loaded) return
  if (!force && loadPromise) return loadPromise

  loading.value = true
  error.value = null
  const run = (async () => {
    const [programRes, logRes] = await Promise.all([
      apiFetch(dataUrl(VAULT.sport)),
      apiFetch(dataUrl(VAULT.sportLog)),
    ])

    if (programRes.status === 404) {
      exercises.value = []
    } else if (!programRes.ok) {
      throw new Error(`Impossible de charger le programme (${programRes.status})`)
    } else {
      const data = (await programRes.json()) as { exercises?: unknown }
      const list = Array.isArray(data.exercises) ? data.exercises : []
      exercises.value = list.map(asExercise).filter((e): e is SportExercise => e !== null)
    }

    if (logRes.status === 404) {
      sessions.value = []
    } else if (!logRes.ok) {
      throw new Error(`Impossible de charger le journal sport (${logRes.status})`)
    } else {
      const data = (await logRes.json()) as { sessions?: unknown }
      const list = Array.isArray(data.sessions) ? data.sessions : []
      sessions.value = list
        .map(asSession)
        .filter((s): s is SportSession => s !== null)
        .sort((a, b) => a.date.localeCompare(b.date))
    }

    loaded = true
  })()

  loadPromise = run
  try {
    await run
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erreur de chargement'
    if (!loaded) {
      exercises.value = []
      sessions.value = []
    }
  } finally {
    if (loadPromise === run) loadPromise = null
    loading.value = false
  }
}

function startClock() {
  clockUsers += 1
  clock.value = Date.now()
  if (clockTimer == null) {
    clockTimer = setInterval(() => {
      clock.value = Date.now()
    }, 60_000)
  }
}

function stopClock() {
  clockUsers -= 1
  if (clockUsers <= 0 && clockTimer != null) {
    clearInterval(clockTimer)
    clockTimer = null
    clockUsers = 0
  }
}

export function useSport() {
  const { profil } = useProfile()
  if (!loaded && !loading.value) void loadSport()
  onMounted(startClock)
  onUnmounted(stopClock)

  const notifyAt = computed(() => (profil.value?.sport_notify_at || '').trim())
  const notifyLabel = computed(() => formatNotifyAt(notifyAt.value))

  const todayKey = computed(() => {
    clock.value
    return todayIso(new Date(clock.value))
  })

  const todaySession = computed(
    () => sessions.value.find((s) => s.date === todayKey.value) ?? null,
  )

  const todayAnswers = computed(() => {
    const map: Record<string, boolean> = {}
    for (const item of todaySession.value?.items ?? []) {
      map[item.exercise_id] = item.done
    }
    return map
  })

  const todayPending = computed(() =>
    exercises.value.filter((exo) => todayAnswers.value[exo.id] === undefined),
  )

  const todayDoneCount = computed(
    () => exercises.value.filter((exo) => todayAnswers.value[exo.id] === true).length,
  )

  const todayComplete = computed(
    () => exercises.value.length > 0 && todayPending.value.length === 0,
  )

  const sportDue = computed(() => {
    clock.value
    if (!notifyAt.value || !exercises.value.length || todayComplete.value) return false
    const [h, m] = notifyAt.value.split(':').map(Number)
    if (!Number.isFinite(h) || !Number.isFinite(m)) return false
    const now = new Date(clock.value)
    const minutesNow = now.getHours() * 60 + now.getMinutes()
    return minutesNow >= h * 60 + m
  })

  const recentSessions = computed(() => [...sessions.value].reverse().slice(0, 14))

  const weekRate = computed(() => {
    const cutoff = new Date(clock.value)
    cutoff.setDate(cutoff.getDate() - 6)
    cutoff.setHours(0, 0, 0, 0)
    const cutoffIso = todayIso(cutoff)
    const recent = sessions.value.filter((s) => s.date >= cutoffIso)
    if (!recent.length) return null
    let done = 0
    let total = 0
    for (const session of recent) {
      total += session.items.length
      done += session.items.filter((i) => i.done).length
    }
    if (!total) return null
    return Math.round((done / total) * 100)
  })

  async function saveProgram(next: SportExercise[]) {
    const res = await apiFetch(`${API_BASE}/sport/program`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        exercises: next.map((e) => ({
          id: e.id,
          name: e.name,
          sets: e.sets,
          reps: e.reps,
          seconds: e.seconds,
          note: e.note,
        })),
      }),
    })
    if (!res.ok) throw new Error(`Enregistrement impossible (${res.status})`)
    const json = (await res.json()) as { exercises?: unknown }
    const list = Array.isArray(json.exercises) ? json.exercises : []
    exercises.value = list.map(asExercise).filter((e): e is SportExercise => e !== null)
  }

  async function saveTodayItems(items: SportLogItem[], day = todayKey.value) {
    const res = await apiFetch(`${API_BASE}/sport/log`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date: day, items }),
    })
    if (!res.ok) throw new Error(`Enregistrement impossible (${res.status})`)
    const session = asSession(await res.json())
    if (!session) {
      await loadSport(true)
      return
    }
    const next = sessions.value.filter((s) => s.date !== session.date)
    next.push(session)
    next.sort((a, b) => a.date.localeCompare(b.date))
    sessions.value = next
  }

  async function answerExercise(exerciseId: string, done: boolean) {
    const map = { ...todayAnswers.value, [exerciseId]: done }
    const byId = new Map(exercises.value.map((e) => [e.id, e]))
    const prevById = new Map(
      (todaySession.value?.items ?? []).map((item) => [item.exercise_id, item]),
    )
    const items: SportLogItem[] = Object.entries(map).map(([id, value]) => {
      const exo = byId.get(id)
      const prev = prevById.get(id)
      return {
        exercise_id: id,
        done: value,
        name: prev?.name || exo?.name || id,
        sets: prev?.sets ?? exo?.sets ?? 1,
        reps: prev?.reps ?? exo?.reps ?? null,
        seconds: prev?.seconds ?? exo?.seconds ?? null,
        note: prev?.note || exo?.note || '',
      }
    })
    await saveTodayItems(items)
  }

  async function saveNotifyAt(value: string) {
    const res = await apiFetch(`${API_BASE}/sport/notify-at`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notify_at: value.trim() }),
    })
    if (!res.ok) throw new Error(`Enregistrement impossible (${res.status})`)
    const json = (await res.json()) as { sport_notify_at?: string | null }
    if (profil.value) {
      if (json.sport_notify_at) profil.value.sport_notify_at = json.sport_notify_at
      else delete profil.value.sport_notify_at
    }
    await reloadProfile()
  }

  return {
    exercises,
    sessions,
    loading,
    error,
    notifyAt,
    notifyLabel,
    todayKey,
    todaySession,
    todayAnswers,
    todayPending,
    todayDoneCount,
    todayComplete,
    sportDue,
    recentSessions,
    weekRate,
    saveProgram,
    answerExercise,
    saveNotifyAt,
    reload: () => loadSport(true),
  }
}
