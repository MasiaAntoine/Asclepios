import { ref } from 'vue'

const promptOpen = ref(false)
const promptReportId = ref<string | null>(null)
const promptedThisSession = new Set<string>()

export function promptReportEmotions(reportId: string, opts?: { force?: boolean }) {
  const id = reportId.replace(/\.md$/i, '')
  if (!id) return
  const force = opts?.force !== false
  if (!force && promptedThisSession.has(id)) return
  promptedThisSession.add(id)
  promptReportId.value = id
  promptOpen.value = true
}

export function useEmotionPrompt() {
  return {
    promptOpen,
    promptReportId,
    promptReportEmotions,
  }
}
