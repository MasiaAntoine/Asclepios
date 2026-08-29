<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { BrainCircuit, ExternalLink, Loader2, RotateCcw, Sparkles } from '@lucide/vue'
import Dialog from '@/components/ui/Dialog.vue'

const emit = defineEmits<{
  generated: [reportId: string]
}>()

const open = ref(false)
const text = ref('')
const logs = ref<string[]>([])
const running = ref(false)
const generatedId = ref<string | null>(null)
const hasError = ref(false)
const terminalEl = ref<HTMLDivElement | null>(null)

const router = useRouter()

function reset() {
  text.value = ''
  logs.value = []
  running.value = false
  generatedId.value = null
  hasError.value = false
}

watch(open, (val) => {
  if (!val) reset()
})

async function scrollTerminal() {
  await nextTick()
  if (terminalEl.value) {
    terminalEl.value.scrollTop = terminalEl.value.scrollHeight
  }
}

async function generate() {
  if (!text.value.trim() || running.value) return

  running.value = true
  generatedId.value = null
  hasError.value = false
  logs.value = []

  try {
    const resp = await fetch('/api/reports/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text.value }),
    })

    if (!resp.ok || !resp.body) {
      logs.value.push(`Erreur HTTP ${resp.status}`)
      hasError.value = true
      running.value = false
      return
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() ?? ''

      for (const part of parts) {
        const line = part.replace(/^data:\s?/, '').trim()
        if (!line) continue

        if (line.startsWith('GENERATED:')) {
          generatedId.value = line.slice('GENERATED:'.length).trim()
          emit('generated', generatedId.value)
        } else if (line === '[DONE]') {
          running.value = false
        } else if (line === '[ERROR]') {
          hasError.value = true
          running.value = false
        } else {
          logs.value.push(line)
          await scrollTerminal()
        }
      }
    }
  } catch (err) {
    logs.value.push(`Erreur réseau : ${err}`)
    hasError.value = true
    running.value = false
  }
}

function openReport() {
  if (generatedId.value) {
    open.value = false
    router.push(`/rapports/${generatedId.value}`)
  }
}
</script>

<template>
  <!-- Trigger -->
  <Dialog
    v-model:open="open"
    title="Générer un rapport avec l'IA"
    description="Collez du texte brut (notes, résumé, journal) — l'IA (gemini-3.7-flash) le transforme en rapport médical structuré, génère le PDF et synchronise sur OVH."
  >
    <template #trigger>
      <button
        class="flex items-center gap-2 rounded-lg bg-[var(--primary)] px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-[var(--primary)]/90 active:scale-95"
      >
        <Sparkles :size="16" />
        Générer avec l'IA
      </button>
    </template>

    <!-- Body -->
    <div class="flex flex-col gap-4 px-6 py-5">
      <!-- Textarea -->
      <div class="flex flex-col gap-1.5">
        <label class="text-xs font-medium uppercase tracking-wide text-[var(--muted-foreground)]">
          Texte source
        </label>
        <textarea
          v-model="text"
          :disabled="running"
          rows="8"
          placeholder="Collez ici vos notes, journal intime, résumé de consultation, brouillon…"
          class="w-full resize-none rounded-xl border border-[var(--border)] bg-[var(--background)] p-3.5 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20 disabled:opacity-50 transition"
        />
        <p class="text-right text-[11px] text-[var(--muted-foreground)]">
          {{ text.trim().split(/\s+/).filter(Boolean).length }} mots
        </p>
      </div>

      <!-- Terminal (visible dès qu'il y a des logs) -->
      <div
        v-if="logs.length || running"
        ref="terminalEl"
        class="max-h-48 overflow-y-auto rounded-xl border border-[var(--border)] bg-[#0d1117] p-4 font-mono text-[11px] leading-relaxed text-emerald-400"
      >
        <p v-for="(line, i) in logs" :key="i" class="whitespace-pre-wrap break-words">
          {{ line }}
        </p>
        <span v-if="running" class="inline-flex items-center gap-1.5 text-emerald-300/70">
          <Loader2 :size="11" class="animate-spin" />
          En cours...
        </span>
      </div>

      <!-- Success -->
      <div
        v-if="generatedId && !hasError"
        class="flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3"
      >
        <div class="flex items-center gap-2 text-sm text-emerald-400">
          <BrainCircuit :size="16" />
          <span>Rapport généré avec succès</span>
        </div>
        <button
          @click="openReport"
          class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-emerald-400 transition hover:bg-emerald-500/10"
        >
          <ExternalLink :size="13" />
          Ouvrir
        </button>
      </div>

      <!-- Error -->
      <div
        v-if="hasError"
        class="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400"
      >
        Une erreur est survenue. Vérifiez que CURSOR_API_KEY est défini dans .env.
      </div>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-between border-t border-[var(--border)] px-6 py-4">
      <button
        v-if="!running && (logs.length || generatedId)"
        @click="reset"
        class="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] transition hover:text-[var(--foreground)]"
      >
        <RotateCcw :size="14" />
        Recommencer
      </button>
      <div v-else />

      <button
        @click="generate"
        :disabled="!text.trim() || running"
        class="flex items-center gap-2 rounded-lg bg-[var(--primary)] px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-[var(--primary)]/90 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Loader2 v-if="running" :size="15" class="animate-spin" />
        <BrainCircuit v-else :size="15" />
        {{ running ? 'Génération…' : 'Générer' }}
      </button>
    </div>
  </Dialog>
</template>
