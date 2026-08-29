import { computed, ref } from 'vue'
import { fetchJson, fetchText } from '@/lib/dataClient'
import { parseFrDate } from '@/lib/chartTheme'

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
      fetchJson<{ taille_cm: number }>('profil.json'),
      fetchText('poids.csv'),
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

  return {
    entries,
    tailleCm,
    premier,
    dernier,
    min,
    max,
    delta,
    deltaRecent,
    loading,
    error,
    load,
    reload: reloadPoids,
  }
}
