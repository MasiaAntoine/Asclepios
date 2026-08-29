import { computed, ref } from 'vue'
import { fetchJson, fetchText } from '@/lib/dataClient'
import { parseFrDate } from '@/lib/chartTheme'
import type { HistoriqueDose, Traitement } from '@/composables/useProfile'

export interface LabsConfig {
  title: string
  subtitle: string
  csv: string
  primaryAnalyte: string
  treatmentNameIncludes: string
  markerUnit: string
  doseUnit: string
  refLow: number
  refHigh: number
  fichier?: string
}

export interface LabPoint {
  date: string
  dateObj: Date
  analyte: string
  value: number
  unit: string
  ref_low: number | null
  ref_high: number | null
  out_of_range: boolean
  lab: string
  source: string
}

export interface DosePoint {
  date: string
  dateObj: Date
  dose_ug: number
  doseLabel: string
  evenement: string
  note: string
}

const DEFAULT_CONFIG: LabsConfig = {
  title: 'Analyses',
  subtitle: 'Marqueur biologique et traitement associé',
  csv: 'labs.csv',
  primaryAnalyte: '',
  treatmentNameIncludes: '',
  markerUnit: '',
  doseUnit: '',
  refLow: 0,
  refHigh: 0,
}

function parseNum(raw: string | undefined): number | null {
  if (!raw?.trim()) return null
  const n = parseFloat(raw.trim().replace(',', '.'))
  return Number.isNaN(n) ? null : n
}

function parseDoseValue(dose: string): number {
  const m = dose.replace(',', '.').match(/([\d.]+)/)
  return m ? parseFloat(m[1]) : 0
}

function parseLabsCsv(raw: string): LabPoint[] {
  const lines = raw.trim().split('\n')
  if (lines.length < 2) return []
  const headers = lines[0].split(',').map((h) => h.trim())

  return lines
    .slice(1)
    .map((line) => {
      const cols = line.split(',')
      if (cols.length < headers.length) return null
      const row: Record<string, string> = {}
      headers.forEach((h, i) => {
        row[h] = cols[i]?.trim() ?? ''
      })
      if (cols.length > headers.length) {
        row.source = cols.slice(headers.indexOf('source')).join(',').trim()
      }

      const dateObj = parseFrDate(row.date)
      const value = parseNum(row.value)
      if (!dateObj || value === null) return null

      return {
        date: row.date,
        dateObj,
        analyte: row.analyte.toUpperCase(),
        value,
        unit: row.unit,
        ref_low: parseNum(row.ref_low),
        ref_high: parseNum(row.ref_high),
        out_of_range: row.out_of_range?.toLowerCase() === 'true',
        lab: row.lab,
        source: row.source,
      }
    })
    .filter((e): e is LabPoint => e !== null)
    .sort((a, b) => a.dateObj.getTime() - b.dateObj.getTime())
}

function buildDoseSeries(historique: HistoriqueDose[]): DosePoint[] {
  return historique
    .map((h) => {
      const dateObj = parseFrDate(h.date)
      if (!dateObj) return null
      return {
        date: h.date,
        dateObj,
        dose_ug: parseDoseValue(h.dose),
        doseLabel: h.dose,
        evenement: h.evenement,
        note: h.note,
      }
    })
    .filter((e): e is DosePoint => e !== null)
    .sort((a, b) => a.dateObj.getTime() - b.dateObj.getTime())
}

const config = ref<LabsConfig>({ ...DEFAULT_CONFIG })
const all = ref<LabPoint[]>([])
const doses = ref<DosePoint[]>([])
const linkedTreatment = ref<Traitement | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
let loaded = false

export async function reloadLabs() {
  loaded = false
  await load()
}

async function load() {
  if (loaded || loading.value) return
  loading.value = true
  error.value = null
  try {
    const cfg = await fetchJson<LabsConfig>('labs-config.json')
    config.value = { ...DEFAULT_CONFIG, ...cfg }

    const [csv, traitementsFile] = await Promise.all([
      fetchText(cfg.csv || 'labs.csv'),
      fetchJson<{ traitements: Traitement[] }>('traitements.json'),
    ])

    all.value = parseLabsCsv(csv)
    const needle = (cfg.treatmentNameIncludes || '').toLowerCase()
    const linked = needle
      ? traitementsFile.traitements.find((t) => t.nom.toLowerCase().includes(needle)) ?? null
      : null
    linkedTreatment.value = linked
    doses.value = linked ? buildDoseSeries(linked.historique) : []
    loaded = true
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erreur de chargement'
  } finally {
    loading.value = false
  }
}

export function useLabs() {
  if (!loaded && !loading.value) void load()

  const primary = computed(() => {
    const key = config.value.primaryAnalyte.toUpperCase()
    if (!key) return all.value
    return all.value.filter((p) => p.analyte === key)
  })

  const secondary = computed(() => {
    const key = config.value.primaryAnalyte.toUpperCase()
    if (!key) return []
    return all.value.filter((p) => p.analyte !== key)
  })

  const latestPrimary = computed(() =>
    primary.value.length ? primary.value[primary.value.length - 1] : null,
  )

  const currentDose = computed(() =>
    doses.value.length ? doses.value[doses.value.length - 1] : null,
  )

  return {
    config,
    all,
    primary,
    secondary,
    doses,
    linkedTreatment,
    latestPrimary,
    currentDose,
    loading,
    error,
    load,
    reload: reloadLabs,
  }
}
