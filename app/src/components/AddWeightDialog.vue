<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useSseStream } from '@/composables/usePdfApi'
import { Plus, X, Loader } from '@lucide/vue'

const emit = defineEmits<{ (e: 'added'): void }>()

const open = ref(false)
const success = ref(false)
const terminalEl = ref<HTMLElement | null>(null)
const { lines, running, done: streamDone, error: streamError, run, cancel, reset } = useSseStream()

function todayIso() {
  return new Date().toISOString().split('T')[0]
}

function isoToFr(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

const dateIso = ref(todayIso())
const poidsKg = ref('')

const canSubmit = computed(
  () => !running.value && !!dateIso.value && !!poidsKg.value && parseFloat(poidsKg.value) > 0,
)

watch(streamDone, (v) => {
  if (v && !streamError.value) {
    success.value = true
    emit('added')
  }
})

function openDialog() {
  reset()
  success.value = false
  dateIso.value = todayIso()
  poidsKg.value = ''
  open.value = true
}

function closeDialog() {
  if (!running.value) {
    cancel()
    open.value = false
  }
}

async function submit() {
  success.value = false
  await run('/poids/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      date: isoToFr(dateIso.value),
      poids_kg: parseFloat(poidsKg.value),
    }),
  })
}

function scrollBottom() {
  if (terminalEl.value) terminalEl.value.scrollTop = terminalEl.value.scrollHeight
}
</script>

<template>
  <button
    type="button"
    class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--primary)]/30 bg-[var(--primary)]/8 px-3 py-2 text-sm font-medium text-[var(--primary)] transition hover:bg-[var(--primary)]/15"
    @click="openDialog"
  >
    <Plus :size="15" />
    Ajouter une mesure
  </button>

  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm"
      @click.self="closeDialog"
    >
      <div class="relative w-full max-w-md rounded-2xl bg-[var(--card)] shadow-2xl ring-1 ring-[var(--border)]">
        <div class="flex items-center justify-between border-b border-[var(--border)] px-6 py-4">
          <div>
            <h2 class="text-base font-semibold text-[var(--foreground)]">Nouvelle mesure de poids</h2>
            <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">Enregistré dans poids.csv puis sync OVH</p>
          </div>
          <button
            type="button"
            class="rounded-lg p-1.5 text-[var(--muted-foreground)] transition hover:bg-[var(--muted)]"
            @click="closeDialog"
          >
            <X :size="16" />
          </button>
        </div>

        <div class="space-y-4 px-6 py-5">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Date *</label>
              <input
                v-model="dateIso"
                type="date"
                class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
              />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Poids (kg) *</label>
              <input
                v-model="poidsKg"
                type="number"
                step="0.1"
                min="1"
                max="400"
                placeholder="72.5"
                class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
              />
            </div>
          </div>

          <div
            v-if="lines.length || running || streamError"
            ref="terminalEl"
            class="max-h-36 overflow-y-auto rounded-xl border border-[var(--border)] bg-[oklch(0.12_0.02_165)] p-3 font-mono text-[11px] leading-5 text-slate-200"
            @vue:updated="scrollBottom"
          >
            <p v-for="(line, i) in lines" :key="i" class="text-slate-300">{{ line }}</p>
            <p v-if="running" class="mt-1 flex items-center gap-1.5 text-slate-400">
              <Loader :size="12" class="animate-spin" /> En cours…
            </p>
            <p v-if="streamError" class="mt-1 text-red-400">{{ streamError }}</p>
            <p v-if="success" class="mt-1 font-semibold text-emerald-400">✓ Mesure enregistrée</p>
          </div>
        </div>

        <div class="flex justify-end gap-2 border-t border-[var(--border)] px-6 py-4">
          <button
            type="button"
            class="rounded-lg px-3 py-2 text-sm text-[var(--muted-foreground)] hover:bg-[var(--muted)]"
            :disabled="running"
            @click="closeDialog"
          >
            {{ success ? 'Fermer' : 'Annuler' }}
          </button>
          <button
            v-if="!success"
            type="button"
            class="inline-flex items-center gap-2 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] disabled:opacity-50"
            :disabled="!canSubmit"
            @click="submit"
          >
            <Loader v-if="running" :size="14" class="animate-spin" />
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
