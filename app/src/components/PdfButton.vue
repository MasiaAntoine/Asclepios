<script setup lang="ts">
import { ref } from 'vue'
import { Download, Loader } from '@lucide/vue'

const props = defineProps<{
  /** Endpoint GET /api/… qui génère et renvoie le PDF (ou ZIP). */
  downloadEndpoint: string
  /** Libellé du bouton. */
  label?: string
}>()

const running = ref(false)
const error = ref<string | null>(null)

function filenameFromDisposition(header: string | null): string | null {
  if (!header) return null
  const star = /filename\*=UTF-8''([^;]+)/i.exec(header)
  if (star?.[1]) {
    try {
      return decodeURIComponent(star[1].trim())
    } catch {
      /* ignore */
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header)
  return plain?.[1]?.trim() || null
}

async function download() {
  if (running.value) return
  running.value = true
  error.value = null
  try {
    const res = await fetch(`/api${props.downloadEndpoint}`)
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
    const blob = await res.blob()
    const name =
      filenameFromDisposition(res.headers.get('Content-Disposition')) ||
      'document.pdf'
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = name
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Téléchargement impossible'
  } finally {
    running.value = false
  }
}
</script>

<template>
  <div class="flex flex-col gap-1">
    <button
      type="button"
      class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--primary)]/30 bg-[var(--primary)]/10 px-3 py-1.5 text-xs font-medium text-[var(--primary)] transition hover:bg-[var(--primary)]/20 disabled:opacity-50"
      :disabled="running"
      @click="download"
    >
      <Loader v-if="running" :size="14" class="animate-spin" />
      <Download v-else :size="14" />
      {{ running ? 'Génération…' : (label ?? 'Télécharger le PDF') }}
    </button>
    <p v-if="error" class="max-w-xs text-[11px] text-red-600">{{ error }}</p>
  </div>
</template>
