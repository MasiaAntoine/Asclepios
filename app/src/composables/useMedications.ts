import { computed, ref } from 'vue'
import { fetchJson, fetchText } from '@/lib/dataClient'
import type { HistoriqueDose, Traitement } from '@/composables/useProfile'

export interface MedicationCard extends Traitement {
  actuel: HistoriqueDose | null
  actif: boolean
}

function currentDose(t: Traitement): HistoriqueDose | null {
  if (!t.historique.length) return null
  return t.historique[t.historique.length - 1]
}

function isActive(t: Traitement): boolean {
  const last = currentDose(t)
  if (!last) return false
  if (last.evenement === 'arret') return false
  const doseNum = parseFloat(last.dose.replace(',', '.'))
  return !Number.isNaN(doseNum) ? doseNum > 0 : last.evenement !== 'arret'
}

const list = ref<MedicationCard[]>([])
const misAJour = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const docCache = new Map<string, string>()
let loaded = false

async function load() {
  if (loaded || loading.value) return
  loading.value = true
  error.value = null
  try {
    const data = await fetchJson<{ traitements: Traitement[]; mis_a_jour?: string }>(
      'traitements.json',
    )
    misAJour.value = data.mis_a_jour ?? ''
    list.value = data.traitements.map((t) => ({
      ...t,
      actuel: currentDose(t),
      actif: isActive(t),
    }))
    loaded = true
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erreur de chargement'
  } finally {
    loading.value = false
  }
}

export function useMedications() {
  if (!loaded && !loading.value) void load()

  const actifs = computed(() => list.value.filter((t) => t.actif))
  const arretes = computed(() => list.value.filter((t) => !t.actif))

  function getById(id: string): MedicationCard | undefined {
    return list.value.find((t) => t.id === id)
  }

  async function getDoc(t: MedicationCard): Promise<string | null> {
    if (!t.doc) return null
    const cached = docCache.get(t.id)
    if (cached != null) return cached
    const content = await fetchText(t.doc)
    docCache.set(t.id, content)
    return content
  }

  return {
    list,
    actifs,
    arretes,
    misAJour,
    loading,
    error,
    load,
    getById,
    getDoc,
  }
}
