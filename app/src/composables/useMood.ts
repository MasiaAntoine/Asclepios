import { computed, ref } from 'vue'
import { apiFetch } from '@/lib/apiFetch'
import { dataUrl } from '@/lib/dataClient'
import { parseIsoDate, todayIso } from '@/lib/mood'
import { VAULT } from '@/lib/vault'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api'

export interface MoodEntry {
  date: string
  dateObj: Date
  score: number
}

const entries = ref<MoodEntry[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
let loaded = false
let loadPromise: Promise<void> | null = null

function parseCsv(raw: string): MoodEntry[] {
  return raw
    .trim()
    .split('\n')
    .slice(1)
    .map((line) => {
      const [date, scoreRaw] = line.split(',')
      const iso = date?.trim() ?? ''
      const dateObj = parseIsoDate(iso)
      const score = Number.parseInt(scoreRaw?.trim() ?? '', 10)
      if (!dateObj || Number.isNaN(score) || score < 0 || score > 10) return null
      return { date: iso, dateObj, score }
    })
    .filter((e): e is MoodEntry => e !== null)
    .sort((a, b) => a.dateObj.getTime() - b.dateObj.getTime())
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

export function useMood() {
  if (!loaded && !loading.value) void loadMoods()

  const byDate = computed(() => {
    const map: Record<string, MoodEntry> = {}
    for (const entry of entries.value) map[entry.date] = entry
    return map
  })

  const today = computed(() => byDate.value[todayIso()] ?? null)

  const dernier = computed(() =>
    entries.value.length ? entries.value[entries.value.length - 1] : null,
  )

  const moyenne7j = computed(() => {
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - 6)
    cutoff.setHours(0, 0, 0, 0)
    const recent = entries.value.filter((e) => e.dateObj >= cutoff)
    if (!recent.length) return null
    return Number(
      (recent.reduce((sum, e) => sum + e.score, 0) / recent.length).toFixed(1),
    )
  })

  const missingDays = computed(() => {
    const missing: string[] = []
    for (let i = 0; i < 14; i += 1) {
      const d = new Date()
      d.setDate(d.getDate() - i)
      const iso = todayIso(d)
      if (!byDate.value[iso]) missing.push(iso)
    }
    return missing
  })

  async function saveMood(date: string, score: number) {
    const res = await apiFetch(`${API_BASE}/mood`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date, score }),
    })
    if (!res.ok) {
      throw new Error(`Enregistrement impossible (${res.status})`)
    }
    const dateObj = parseIsoDate(date)
    if (!dateObj) return
    const next = entries.value.filter((e) => e.date !== date)
    next.push({ date, dateObj, score })
    next.sort((a, b) => a.dateObj.getTime() - b.dateObj.getTime())
    entries.value = next
  }

  return {
    entries,
    byDate,
    today,
    dernier,
    moyenne7j,
    missingDays,
    loading,
    error,
    saveMood,
    reload: () => loadMoods(true),
  }
}
