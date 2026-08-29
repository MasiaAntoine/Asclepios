import { computed, ref } from 'vue'
import { fetchJson } from '@/lib/dataClient'
import { parseFrDate } from '@/lib/chartTheme'
import type { HistoriqueDose, Traitement } from '@/composables/useProfile'

export interface MedicationConfig {
  title: string
  subtitle: string
  treatmentNameIncludes: string
  doseUnit: string
  fichier?: string
}

export interface DosePoint {
  date: string
  dateObj: Date
  doseValue: number
  doseLabel: string
  posologie: string
  evenement: string
  note: string
}

const DEFAULT_CONFIG: MedicationConfig = {
  title: 'Posologie',
  subtitle: 'Historique des doses',
  treatmentNameIncludes: '',
  doseUnit: '',
}

function parseDoseValue(dose: string): number {
  const m = dose.replace(',', '.').match(/([\d.]+)/)
  return m ? parseFloat(m[1]) : 0
}

function buildDoseSeries(historique: HistoriqueDose[]): DosePoint[] {
  return historique
    .map((h) => {
      const dateObj = parseFrDate(h.date)
      if (!dateObj) return null
      return {
        date: h.date,
        dateObj,
        doseValue: parseDoseValue(h.dose),
        doseLabel: h.dose,
        posologie: h.posologie,
        evenement: h.evenement,
        note: h.note,
      }
    })
    .filter((e): e is DosePoint => e !== null)
    .sort((a, b) => a.dateObj.getTime() - b.dateObj.getTime())
}

const config = ref<MedicationConfig>({ ...DEFAULT_CONFIG })
const treatment = ref<Traitement | null>(null)
const doses = ref<DosePoint[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
let loaded = false

export async function reloadMedicationSeries() {
  loaded = false
  await load()
}

async function load() {
  if (loaded || loading.value) return
  loading.value = true
  error.value = null
  try {
    const [cfg, traitementsFile] = await Promise.all([
      fetchJson<MedicationConfig>('medication-config.json'),
      fetchJson<{ traitements: Traitement[]; mis_a_jour?: string }>('traitements.json'),
    ])
    config.value = { ...DEFAULT_CONFIG, ...cfg }

    const needle = (cfg.treatmentNameIncludes || '').toLowerCase()
    const found = needle
      ? traitementsFile.traitements.find((t) => t.nom.toLowerCase().includes(needle)) ?? null
      : null

    treatment.value = found
    doses.value = found ? buildDoseSeries(found.historique) : []
    loaded = true
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erreur de chargement'
  } finally {
    loading.value = false
  }
}

export function useMedicationSeries() {
  if (!loaded && !loading.value) void load()

  const currentDose = computed(() =>
    doses.value.length ? doses.value[doses.value.length - 1] : null,
  )

  const isActive = computed(() => {
    const last = currentDose.value
    if (!last) return false
    if (last.evenement === 'arret') return false
    return last.doseValue > 0
  })

  return {
    config,
    treatment,
    doses,
    currentDose,
    isActive,
    loading,
    error,
    load,
    reload: reloadMedicationSeries,
  }
}
