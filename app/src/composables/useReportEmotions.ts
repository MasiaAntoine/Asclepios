import { ref } from 'vue'
import { apiFetch } from '@/lib/apiFetch'
import { dataUrl } from '@/lib/dataClient'
import {
  normalizeEmotionIds,
  type EmotionId,
} from '@/lib/emotions'
import { VAULT } from '@/lib/vault'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api'

const byId = ref<Record<string, EmotionId[]>>({})
const loading = ref(false)
const loaded = ref(false)
let loadPromise: Promise<void> | null = null

async function loadEmotions(force = false) {
  if (!force && loaded.value) return
  if (!force && loadPromise) return loadPromise

  loading.value = true
  const run = (async () => {
    const res = await apiFetch(dataUrl(VAULT.rapportsEmotions))
    if (res.status === 404) {
      byId.value = {}
      loaded.value = true
      return
    }
    if (!res.ok) {
      throw new Error(`Impossible de charger les émotions (${res.status})`)
    }
    const data = (await res.json()) as Record<string, unknown>
    const next: Record<string, EmotionId[]> = {}
    if (data && typeof data === 'object' && !Array.isArray(data)) {
      for (const [id, value] of Object.entries(data)) {
        const raw = Array.isArray(value)
          ? value
          : value && typeof value === 'object' && 'emotions' in value
            ? (value as { emotions?: unknown }).emotions
            : value && typeof value === 'object' && 'ids' in value
              ? (value as { ids?: unknown }).ids
              : []
        const ids = normalizeEmotionIds(Array.isArray(raw) ? raw.map(String) : [])
        if (ids.length) next[id] = ids
      }
    }
    byId.value = next
    loaded.value = true
  })()

  loadPromise = run
  try {
    await run
  } catch {
    if (!loaded.value) byId.value = {}
  } finally {
    if (loadPromise === run) loadPromise = null
    loading.value = false
  }
}

export function useReportEmotions() {
  if (!loaded.value && !loading.value) {
    void loadEmotions()
  }

  function emotionsOf(reportId: string): EmotionId[] {
    return byId.value[reportId] ?? []
  }

  function isEvaluated(reportId: string): boolean {
    return (byId.value[reportId]?.length ?? 0) > 0
  }

  async function saveEmotions(reportId: string, ids: EmotionId[]) {
    const normalized = normalizeEmotionIds(ids)
    const res = await apiFetch(
      `${API_BASE}/reports/${encodeURIComponent(reportId)}/emotions`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emotions: normalized }),
      },
    )
    if (!res.ok) {
      throw new Error(`Enregistrement impossible (${res.status})`)
    }
    const next = { ...byId.value }
    if (normalized.length) next[reportId] = normalized
    else delete next[reportId]
    byId.value = next
  }

  return {
    byId,
    loading,
    loaded,
    loadEmotions,
    emotionsOf,
    isEvaluated,
    saveEmotions,
    reload: () => loadEmotions(true),
  }
}
