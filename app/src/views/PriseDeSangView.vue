<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { formatLabDate, useLabPdfs } from '@/composables/useLabPdfs'
import PageShell from '@/components/PageShell.vue'
import { ChevronRight, Droplets, FileText, Loader, Upload, X } from '@lucide/vue'

const router = useRouter()
const { items, loading, error, load } = useLabPdfs()

const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const showTerminal = ref(false)
const syncLines = ref<string[]>([])
const syncDone = ref(false)
const syncError = ref<string | null>(null)
const uploadedId = ref<string | null>(null)

onMounted(() => {
  void load()
})

function open(id: string) {
  void router.push(`/prise-de-sang/${encodeURIComponent(id)}`)
}

function formatSize(n: number): string {
  if (n < 1024) return `${n} o`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} Ko`
  return `${(n / (1024 * 1024)).toFixed(1)} Mo`
}

function pickFile() {
  if (uploading.value) return
  fileInput.value?.click()
}

async function onFileSelected(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    syncError.value = 'Seuls les fichiers PDF sont acceptés'
    showTerminal.value = true
    return
  }

  uploading.value = true
  showTerminal.value = true
  syncLines.value = []
  syncDone.value = false
  syncError.value = null
  uploadedId.value = null

  try {
    const form = new FormData()
    form.append('file', file, file.name)
    const res = await fetch('/api/labs/pdfs/upload', { method: 'POST', body: form })
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

    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() ?? ''
      for (const block of blocks) {
        const line = block.replace(/^data: /, '').trim()
        if (!line) continue
        if (line === '[DONE]') {
          syncDone.value = true
          continue
        }
        if (line === '[ERROR]') {
          syncError.value = syncError.value || 'Échec'
          continue
        }
        if (line.startsWith('ID:')) {
          uploadedId.value = line.slice(3)
          continue
        }
        syncLines.value.push(line)
      }
    }
    await load()
  } catch (e) {
    syncError.value = e instanceof Error ? e.message : 'Upload impossible'
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <PageShell title="Prise de sang" max-width="md">
    <template #description>
      <p class="mt-0.5 text-sm text-[var(--muted-foreground)]">
        {{ items.length }} compte{{ items.length > 1 ? 's' : '' }}-rendu{{ items.length > 1 ? 's' : '' }} PDF
      </p>
    </template>
    <template #actions>
      <input
        ref="fileInput"
        type="file"
        accept="application/pdf,.pdf"
        class="hidden"
        @change="onFileSelected"
      />
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-lg bg-[var(--primary)] px-3 py-2 text-sm font-medium text-[var(--primary-foreground)] transition hover:opacity-90 disabled:opacity-50"
        :disabled="uploading"
        @click="pickFile"
      >
        <Loader v-if="uploading" :size="15" class="animate-spin" />
        <Upload v-else :size="15" />
        {{ uploading ? 'Envoi…' : 'Ajouter un PDF' }}
      </button>
      <button
        v-if="uploadedId && syncDone && !syncError"
        type="button"
        class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-2 text-sm text-[var(--foreground)] transition hover:bg-[var(--accent)]"
        @click="open(uploadedId)"
      >
        Ouvrir
        <ChevronRight :size="14" />
      </button>
    </template>

    <div
      v-if="showTerminal"
      class="relative mb-6 overflow-hidden rounded-xl border border-[var(--border)] bg-[oklch(0.12_0.02_165)] p-4 font-mono text-[11.5px] leading-5 text-slate-200"
    >
      <button
        type="button"
        class="absolute right-2 top-2 text-slate-400 hover:text-white"
        :disabled="uploading"
        @click="showTerminal = false"
      >
        <X :size="14" />
      </button>
      <p class="mb-2 text-xs font-semibold text-slate-300">Ajout + synchronisation OVH</p>
      <div class="max-h-40 overflow-y-auto">
        <p v-if="!syncLines.length && uploading" class="text-slate-500">Envoi du PDF…</p>
        <p
          v-for="(line, i) in syncLines"
          :key="i"
          :class="[
            line.startsWith('✗') ? 'text-red-400' :
            line.startsWith('✓') ? 'text-emerald-400' :
            line.startsWith('▶') ? 'text-[var(--primary)] font-semibold' :
            'text-slate-300',
          ]"
        >{{ line }}</p>
        <p v-if="syncDone && !syncError" class="mt-1 font-semibold text-emerald-400">✓ Terminé</p>
        <p v-if="syncError" class="mt-1 font-semibold text-red-400">✗ {{ syncError }}</p>
      </div>
    </div>

    <div v-if="error" class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {{ error }}
    </div>
    <div v-else-if="loading && !items.length" class="py-24 text-center text-sm text-[var(--muted-foreground)]">
      Chargement…
    </div>
    <div v-else-if="!items.length" class="mx-auto max-w-md py-24 text-center">
      <div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--accent)]">
        <Droplets :size="28" class="text-[var(--primary)]" />
      </div>
      <p class="font-medium text-[var(--foreground)]">Aucun PDF</p>
      <p class="mt-1 text-sm text-[var(--muted-foreground)]">
        Ajoutez un compte-rendu via le bouton ci-dessus.
      </p>
    </div>
    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <button
        v-for="item in items"
        :key="item.id"
        type="button"
        class="group flex flex-col rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 text-left shadow-sm transition hover:border-[var(--primary)]/40 hover:shadow-md"
        @click="open(item.id)"
      >
        <div class="mb-3 flex items-start justify-between gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent)]">
            <FileText :size="18" class="text-[var(--primary)]" />
          </div>
          <ChevronRight
            :size="18"
            class="mt-1 text-[var(--muted-foreground)] transition group-hover:text-[var(--primary)]"
          />
        </div>
        <p class="text-lg font-semibold text-[var(--foreground)]">
          {{ item.date ? `Résultats du ${formatLabDate(item.date)}` : item.title }}
        </p>
        <p class="mt-1 text-sm text-[var(--muted-foreground)]">
          {{ item.lab }}
          <span class="mx-1.5 text-[var(--border)]">·</span>
          {{ formatSize(item.size) }}
        </p>
        <p class="mt-3 truncate font-mono text-[11px] text-[var(--muted-foreground)]">
          {{ item.filename }}
        </p>
      </button>
    </div>
  </PageShell>
</template>
