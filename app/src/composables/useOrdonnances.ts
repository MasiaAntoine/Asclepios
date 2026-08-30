import { ref } from 'vue'

const API_BASE = '/api'

export interface OrdonnanceListItem {
  id: string
  filename: string
  date: string | null
  prescriber: string
  kind?: 'medicaments' | 'biologie' | string
  title: string
  medications_count: number | null
  exams_count?: number | null
  size: number
}

export interface OrdonnanceMedication {
  name: string
  posology: string | null
  brand: string | null
  dose: string | null
  form: string | null
}

export interface OrdonnanceMeta {
  date: string | null
  kind?: 'medicaments' | 'biologie' | string
  prescriber: string | null
  specialty: string | null
  address: string | null
  phone: string | null
  rpps: string | null
  patient: string | null
  patient_birth: string | null
  duration: string | null
  signed_via: string | null
  signed_at: string | null
  e_prescription: string | null
  filename: string
}

export interface OrdonnanceDetail {
  id: string
  meta: OrdonnanceMeta
  medications: OrdonnanceMedication[]
  exams?: string[]
  parsable: boolean
  parser: string
  note?: string | null
  navigation: {
    prev_id: string | null
    next_id: string | null
    index: number
    total: number
  }
}

export async function fetchOrdonnanceList(): Promise<OrdonnanceListItem[]> {
  const res = await fetch(`${API_BASE}/ordonnances/pdfs`)
  if (!res.ok) throw new Error(`Liste indisponible (${res.status})`)
  const data = (await res.json()) as { items: OrdonnanceListItem[] }
  return data.items ?? []
}

export async function fetchOrdonnanceDetail(
  id: string,
  force = false,
): Promise<OrdonnanceDetail> {
  const q = force ? '?force=true' : ''
  const res = await fetch(`${API_BASE}/ordonnances/pdfs/${encodeURIComponent(id)}${q}`)
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = String(body.detail)
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return (await res.json()) as OrdonnanceDetail
}

export function ordonnancePdfFileUrl(id: string): string {
  return `${API_BASE}/ordonnances/pdfs/${encodeURIComponent(id)}/file`
}

export function formatOrdonnanceDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (m) return `${m[3]}/${m[2]}/${m[1]}`
  return iso
}

export function useOrdonnances() {
  const items = ref<OrdonnanceListItem[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      items.value = await fetchOrdonnanceList()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Erreur de chargement'
    } finally {
      loading.value = false
    }
  }

  return { items, loading, error, load }
}
