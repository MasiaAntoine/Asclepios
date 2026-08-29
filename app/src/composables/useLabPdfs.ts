import { ref } from 'vue'

const API_BASE = '/api'

export interface LabPdfListItem {
  id: string
  filename: string
  date: string | null
  lab: string
  title: string
  size: number
}

export interface LabAnalyteAlt {
  value: number | null
  value_display: string | null
  unit: string | null
  ref_low: number | null
  ref_high: number | null
  ref_label: string | null
}

export interface LabAnalyte {
  name: string
  value: number | null
  value_display: string | null
  unit: string | null
  ref_low: number | null
  ref_high: number | null
  ref_label: string | null
  out_of_range: boolean
  has_range: boolean
  pct?: number | null
  pct_display?: string | null
  alt?: LabAnalyteAlt
}

export interface LabSection {
  title: string
  items: LabAnalyte[]
}

export interface LabPdfMeta {
  lab: string | null
  date: string | null
  dossier: string | null
  patient: string | null
  prescriber: string | null
  validated_at: string | null
  validated_by: string | null
  sampled_at: string | null
  filename: string
  note?: string
}

export interface LabPdfDetail {
  id: string
  meta: LabPdfMeta
  sections: LabSection[]
  out_of_range_summary: string[]
  parsable: boolean
  parser: string
  navigation: {
    prev_id: string | null
    next_id: string | null
    index: number
    total: number
  }
}

export async function fetchLabPdfList(): Promise<LabPdfListItem[]> {
  const res = await fetch(`${API_BASE}/labs/pdfs`)
  if (!res.ok) throw new Error(`Liste indisponible (${res.status})`)
  const data = (await res.json()) as { items: LabPdfListItem[] }
  return data.items ?? []
}

export async function fetchLabPdfDetail(id: string, force = false): Promise<LabPdfDetail> {
  const q = force ? '?force=true' : ''
  const res = await fetch(`${API_BASE}/labs/pdfs/${encodeURIComponent(id)}${q}`)
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
  return (await res.json()) as LabPdfDetail
}

export function labPdfFileUrl(id: string): string {
  return `${API_BASE}/labs/pdfs/${encodeURIComponent(id)}/file`
}

export function formatLabDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (m) return `${m[3]}/${m[2]}/${m[1]}`
  return iso
}

export function useLabPdfs() {
  const items = ref<LabPdfListItem[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      items.value = await fetchLabPdfList()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Erreur de chargement'
    } finally {
      loading.value = false
    }
  }

  return { items, loading, error, load }
}
