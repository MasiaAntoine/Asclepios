<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { pdfExists, useSseStream } from '@/composables/usePdfApi'
import { FileText, Loader, RefreshCw, X } from '@lucide/vue'

const props = defineProps<{
  /** Chemin /data/… vers le PDF (pour vérifier l'existence et l'ouvrir). */
  pdfUrl?: string
  /** Endpoint POST /api/… pour lancer la génération. */
  generateEndpoint?: string
  /** Libellé du bouton (ex. "Rapport PDF"). */
  label?: string
  /**
   * Si true, déclenche automatiquement la génération en arrière-plan
   * quand le PDF est absent (utile pour les pages de détail).
   */
  autoGenerate?: boolean
}>()

const exists = ref<boolean | null>(null)
const showTerminal = ref(false)
const { lines, running, done, error, run } = useSseStream()

onMounted(async () => {
  if (props.pdfUrl) {
    exists.value = await pdfExists(props.pdfUrl)
    if (!exists.value && props.autoGenerate && props.generateEndpoint) {
      await generate()
    }
  }
})

async function generate() {
  if (!props.generateEndpoint) return
  showTerminal.value = true
  await run(props.generateEndpoint)
  if (!error.value && props.pdfUrl) {
    exists.value = await pdfExists(props.pdfUrl)
  }
}

function openPdf() {
  if (props.pdfUrl) window.open(props.pdfUrl, '_blank')
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <!-- Action buttons -->
    <div class="flex flex-wrap items-center gap-2">
      <!-- View PDF -->
      <button
        v-if="exists && pdfUrl"
        type="button"
        class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--primary)]/30 bg-[var(--primary)]/10 px-3 py-1.5 text-xs font-medium text-[var(--primary)] transition hover:bg-[var(--primary)]/20"
        @click="openPdf"
      >
        <FileText :size="14" />
        {{ label ?? 'Voir le PDF' }}
      </button>

      <!-- Generate / Regenerate -->
      <button
        v-if="generateEndpoint && !running"
        type="button"
        class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-1.5 text-xs font-medium text-[var(--muted-foreground)] transition hover:border-[var(--primary)]/30 hover:text-[var(--primary)]"
        @click="generate"
      >
        <RefreshCw :size="13" />
        {{ exists ? 'Régénérer' : 'Générer le PDF' }}
      </button>

      <!-- Running indicator -->
      <span
        v-if="running"
        class="inline-flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]"
      >
        <Loader :size="13" class="animate-spin" />
        Génération…
      </span>
    </div>

    <!-- Mini terminal (visible dès qu'actif, même si vide ou en erreur) -->
    <div
      v-if="showTerminal"
      class="relative max-h-48 overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--foreground)]/[0.03] p-3 font-mono text-[11px] leading-5"
    >
      <button
        type="button"
        class="absolute right-2 top-2 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
        @click="showTerminal = false"
      >
        <X :size="12" />
      </button>

      <!-- Spinner pendant l'initialisation (avant la 1re ligne) -->
      <p v-if="running && !lines.length" class="flex items-center gap-1.5 text-[var(--muted-foreground)]">
        <Loader :size="11" class="animate-spin" />
        Connexion à l'API…
      </p>

      <p v-for="(line, i) in lines" :key="i" :class="[
        line.startsWith('✗') ? 'text-red-600' :
        line.startsWith('✓') ? 'text-emerald-700' :
        line.startsWith('▶') ? 'text-[var(--primary)] font-semibold' :
        'text-[var(--muted-foreground)]'
      ]">{{ line }}</p>
      <p v-if="done && !error" class="mt-1 font-semibold text-emerald-700">✓ Terminé</p>
      <p v-if="error" class="mt-1 font-semibold text-red-600">✗ {{ error }}</p>
    </div>
  </div>
</template>
