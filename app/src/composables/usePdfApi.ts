import { ref } from 'vue'

const API_BASE = '/api'

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
