import { ref } from 'vue'

const API_BASE = '/api'

export type PdfCategory = 'rapport' | 'trauma' | 'compte-rendu' | 'traitement'

export interface PdfList {
  rapport: string[]
  trauma: string[]
  'compte-rendu': string[]
  traitement: string[]
}

/** Charge la liste des PDFs existants depuis l'API. */
export async function fetchPdfList(): Promise<PdfList> {
  const res = await fetch(`${API_BASE}/pdf/list`)
  if (!res.ok) throw new Error(`PDF list unavailable (${res.status})`)
  return res.json() as Promise<PdfList>
}

/** Vérifie si un PDF spécifique est accessible (HEAD request sur /data/…). */
export async function pdfExists(dataPath: string): Promise<boolean> {
  try {
    const res = await fetch(dataPath, { method: 'HEAD' })
    return res.ok
  } catch {
    return false
  }
}

/** Composable générique pour déclencher un endpoint SSE et afficher les logs. */
export function useSseStream() {
  const lines = ref<string[]>([])
  const running = ref(false)
  const done = ref(false)
  const error = ref<string | null>(null)
  let abortController: AbortController | null = null

  async function run(endpoint: string, init?: RequestInit): Promise<void> {
    lines.value = []
    done.value = false
    error.value = null
    running.value = true
    abortController = new AbortController()

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        ...init,
        signal: abortController.signal,
      })
      if (!res.ok) {
        error.value = `Erreur HTTP ${res.status}`
        return
      }
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done: streamDone, value } = await reader.read()
        if (streamDone) break
        buffer += decoder.decode(value, { stream: true })
        const blocks = buffer.split('\n\n')
        buffer = blocks.pop() ?? ''
        for (const block of blocks) {
          const line = block.replace(/^data: /, '').trim()
          if (line === '[DONE]') {
            done.value = true
          } else if (line) {
            lines.value.push(line)
          }
        }
      }
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        error.value = e instanceof Error ? e.message : 'Erreur inconnue'
      }
    } finally {
      running.value = false
      abortController = null
    }
  }

  function cancel() {
    abortController?.abort()
  }

  function reset() {
    lines.value = []
    done.value = false
    error.value = null
    running.value = false
  }

  return { lines, running, done, error, run, cancel, reset }
}
