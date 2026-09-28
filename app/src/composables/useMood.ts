import { computed, onMounted, onUnmounted, ref } from 'vue'
import { apiFetch } from '@/lib/apiFetch'
import { dataUrl } from '@/lib/dataClient'
import {
  MIN_MOOD_GAP_MINUTES,
  parseMoodAt,
  slotAt,
  slotMeta,
  todayIso,
  toIsoWithOffset,
  type MoodSlotId,
} from '@/lib/mood'
import { VAULT } from '@/lib/vault'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api'

export interface MoodEntry {
  at: string
  atObj: Date
  date: string
  score: number
  slot: MoodSlotId | null
}

const entries = ref<MoodEntry[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const clock = ref(Date.now())
let loaded = false
let loadPromise: Promise<void> | null = null
let clockTimer: ReturnType<typeof setInterval> | null = null
let clockUsers = 0

function makeEntry(at: string, score: number, atObj?: Date): MoodEntry | null {
  const when = atObj ?? parseMoodAt(at)
  if (!when) return null
  return {
    at,
    atObj: when,
    date: todayIso(when),
    score,
    slot: slotAt(when),
  }
}

function parseCsv(raw: string): MoodEntry[] {
  const lines = raw.trim().split('\n')
  const out: MoodEntry[] = []
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i]?.trim() ?? ''
    if (!line) continue
    const lower = line.toLowerCase()
    if (i === 0 && (lower.startsWith('date') || lower.startsWith('at'))) continue
    const [atRaw, scoreRaw] = line.split(',')
    const score = Number.parseInt(scoreRaw?.trim() ?? '', 10)
    if (Number.isNaN(score) || score < 0 || score > 10) continue
    const entry = makeEntry(atRaw?.trim() ?? '', score)
    if (entry) out.push(entry)
  }
  out.sort((a, b) => a.atObj.getTime() - b.atObj.getTime())
  return out
}

async function loadMoods(force = false) {
  if (!force && loaded) return
  if (!force && loadPromise) return loadPromise

  loading.value = true
  error.value = null
  const run = (async () => {
    const res = await apiFetch(dataUrl(VAULT.humeur))
    if (res.status === 404) {
      entries.value = []
      loaded = true
      return
    }
    if (!res.ok) throw new Error(`Impossible de charger l’humeur (${res.status})`)
    entries.value = parseCsv(await res.text())
    loaded = true
  })()

  loadPromise = run
  try {
    await run
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erreur de chargement'
    if (!loaded) entries.value = []
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

export function useMood() {
  if (!loaded && !loading.value) void loadMoods()
  onMounted(startClock)
  onUnmounted(stopClock)

  const byDate = computed(() => {
    const map: Record<string, MoodEntry[]> = {}
    for (const entry of entries.value) {
      ;(map[entry.date] ??= []).push(entry)
    }
    return map
  })

  const todayEntries = computed(() => byDate.value[todayIso(new Date(clock.value))] ?? [])

  const today = computed(() => {
    const list = todayEntries.value
    return list.length ? list[list.length - 1] : null
  })

  const dernier = computed(() =>
    entries.value.length ? entries.value[entries.value.length - 1] : null,
  )

  const now = computed(() => new Date(clock.value))

  const currentSlot = computed(() => slotAt(now.value))

  const currentSlotMeta = computed(() => slotMeta(currentSlot.value))

  const currentSlotFilled = computed(() => {
    const slot = currentSlot.value
    if (!slot) return true
    return todayEntries.value.some((e) => e.slot === slot)
  })

  const slotDue = computed(() => {
    clock.value
    const slot = currentSlot.value
    if (!slot || currentSlotFilled.value) return false
    const last = dernier.value
    if (last) {
      const gap = (clock.value - last.atObj.getTime()) / 60_000
      if (gap < MIN_MOOD_GAP_MINUTES) return false
    }
    return true
  })

  const moyenne7j = computed(() => {
    const cutoff = new Date(clock.value)
    cutoff.setDate(cutoff.getDate() - 6)
    cutoff.setHours(0, 0, 0, 0)
    const recent = entries.value.filter((e) => e.atObj >= cutoff)
    if (!recent.length) return null
    return Number(
      (recent.reduce((sum, e) => sum + e.score, 0) / recent.length).toFixed(1),
    )
  })

  const missingDays = computed(() => {
    const missing: string[] = []
    for (let i = 0; i < 14; i += 1) {
      const d = new Date(clock.value)
      d.setDate(d.getDate() - i)
      const iso = todayIso(d)
      if (!byDate.value[iso]?.length) missing.push(iso)
    }
    return missing
  })

  async function saveMood(
    score: number,
    opts: { at?: Date; replaceAt?: string } = {},
  ) {
    const at = opts.at ?? new Date()
    const body: { score: number; at: string; replace_at?: string } = {
      score,
      at: toIsoWithOffset(at),
    }
    if (opts.replaceAt) body.replace_at = opts.replaceAt

    const res = await apiFetch(`${API_BASE}/mood`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      throw new Error(`Enregistrement impossible (${res.status})`)
    }
    const json = (await res.json()) as { at?: string; score?: number }
    const savedAt = json.at ?? body.at
    const savedScore = json.score ?? score
    const entry = makeEntry(savedAt, savedScore)
    if (!entry) {
      await loadMoods(true)
      return
    }
    let next = entries.value.slice()
    if (opts.replaceAt) {
      next = next.filter((e) => e.at !== opts.replaceAt)
    }
    next = next.filter((e) => e.at !== entry.at && e.atObj.getTime() !== entry.atObj.getTime())
    next.push(entry)
    next.sort((a, b) => a.atObj.getTime() - b.atObj.getTime())
    entries.value = next
  }

  return {
    entries,
    byDate,
    todayEntries,
    today,
    dernier,
    now,
    currentSlot,
    currentSlotMeta,
    currentSlotFilled,
    slotDue,
    moyenne7j,
    missingDays,
    loading,
    error,
    saveMood,
    reload: () => loadMoods(true),
  }
}
