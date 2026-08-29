<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSseStream } from '@/composables/usePdfApi'
import { Plus, X, Loader } from '@lucide/vue'

const props = defineProps<{
  type: 'labs' | 'rx'
  // Labs props
  csv?: string
  primaryAnalyte?: string
  markerUnit?: string
  refLow?: number
  refHigh?: number
  // RX props
  treatmentNameIncludes?: string
  doseUnit?: string
  // Shared
  titre?: string
}>()

const emit = defineEmits<{ (e: 'added'): void }>()

const open = ref(false)
const done = ref(false)
const terminalEl = ref<HTMLElement | null>(null)

const { lines, running, done: streamDone, error: streamError, run, cancel, reset } = useSseStream()

// ── Date (défaut = aujourd'hui) ────────────────────────────────────────────
function todayIso() {
  return new Date().toISOString().split('T')[0]
}

function isoToFr(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

// ── Labs form ──────────────────────────────────────────────────────────────
const labDate = ref(todayIso())
const labAnalyte = ref(props.primaryAnalyte ?? 'TSH')
const labValue = ref('')
const labUnit = ref(props.markerUnit ?? '')
const labRefLow = ref(props.refLow !== undefined ? String(props.refLow) : '')
const labRefHigh = ref(props.refHigh !== undefined ? String(props.refHigh) : '')
const labLab = ref('')
const labSource = ref('')

const labOutOfRange = computed(() => {
  const v = parseFloat(labValue.value)
  const lo = parseFloat(labRefLow.value)
  const hi = parseFloat(labRefHigh.value)
  if (isNaN(v) || isNaN(lo) || isNaN(hi)) return null
  return !(v >= lo && v <= hi)
})

// ── RX form ────────────────────────────────────────────────────────────────
const rxDate = ref(todayIso())
const rxDose = ref('')
const rxPosologie = ref('')
const rxEvenement = ref('maintien')
const rxNote = ref('')

const eventOptions = [
  { value: 'debut', label: 'Début' },
  { value: 'maintien', label: 'Maintien' },
  { value: 'augmentation', label: 'Augmentation' },
  { value: 'diminution', label: 'Diminution' },
  { value: 'arret', label: 'Arrêt' },
  { value: 'reprise', label: 'Reprise' },
]

// ── Validation ─────────────────────────────────────────────────────────────
const canSubmit = computed(() => {
  if (running.value) return false
  if (props.type === 'labs') {
    return labDate.value && labAnalyte.value && labValue.value && labLab.value
  }
  return rxDate.value && rxDose.value && rxPosologie.value && rxEvenement.value
})

// ── Submit ─────────────────────────────────────────────────────────────────
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api'

async function submit() {
  done.value = false
  let endpoint: string
  let body: Record<string, unknown>

  if (props.type === 'labs') {
    endpoint = `${API_BASE}/labs/add`
    body = {
      csv: props.csv ?? 'labs.csv',
      date: isoToFr(labDate.value),
      analyte: labAnalyte.value.toUpperCase(),
      value: parseFloat(labValue.value),
      unit: labUnit.value,
      ref_low: labRefLow.value ? parseFloat(labRefLow.value) : null,
      ref_high: labRefHigh.value ? parseFloat(labRefHigh.value) : null,
      out_of_range: labOutOfRange.value,
      lab: labLab.value,
      source: labSource.value,
    }
  } else {
    endpoint = `${API_BASE}/treatment/add-entry`
    body = {
      treatment_name_includes: props.treatmentNameIncludes ?? '',
      date: isoToFr(rxDate.value),
      dose: rxDose.value,
      posologie: rxPosologie.value,
      evenement: rxEvenement.value,
      note: rxNote.value,
    }
  }

  await run(endpoint.replace(API_BASE, ''), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

// ── Watch for completion ───────────────────────────────────────────────────
import { watch } from 'vue'

watch(streamDone, (v) => {
  if (v && !streamError.value) {
    done.value = true
    emit('added')
  }
})

function openDialog() {
  reset()
  done.value = false
  // Reset forms
  labDate.value = todayIso()
  labAnalyte.value = props.primaryAnalyte ?? 'TSH'
  labValue.value = ''
  labUnit.value = props.markerUnit ?? ''
  labRefLow.value = props.refLow !== undefined ? String(props.refLow) : ''
  labRefHigh.value = props.refHigh !== undefined ? String(props.refHigh) : ''
  labLab.value = ''
  labSource.value = ''
  rxDate.value = todayIso()
  rxDose.value = ''
  rxPosologie.value = ''
  rxEvenement.value = 'maintien'
  rxNote.value = ''
  open.value = true
}

function closeDialog() {
  if (!running.value) {
    cancel()
    open.value = false
  }
}

function scrollBottom() {
  if (terminalEl.value) terminalEl.value.scrollTop = terminalEl.value.scrollHeight
}
</script>

<template>
  <!-- Trigger -->
  <button
    type="button"
    class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--primary)]/30 bg-[var(--primary)]/8 px-3 py-2 text-sm font-medium text-[var(--primary)] transition hover:bg-[var(--primary)]/15"
    @click="openDialog"
  >
    <Plus :size="15" />
    Ajouter une entrée
  </button>

  <!-- Modal backdrop -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-150"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm"
        @click.self="closeDialog"
      >
        <Transition
          enter-active-class="transition duration-150"
          enter-from-class="opacity-0 scale-95"
          leave-active-class="transition duration-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div
            v-if="open"
            class="relative w-full max-w-lg rounded-2xl bg-[var(--card)] shadow-2xl ring-1 ring-[var(--border)]"
          >
            <!-- Header -->
            <div class="flex items-center justify-between border-b border-[var(--border)] px-6 py-4">
              <div>
                <h2 class="text-base font-semibold text-[var(--foreground)]">
                  {{ type === 'labs' ? 'Ajouter une analyse' : 'Ajouter une entrée de traitement' }}
                </h2>
                <p v-if="titre" class="mt-0.5 text-xs text-[var(--muted-foreground)]">{{ titre }}</p>
              </div>
              <button
                type="button"
                class="rounded-lg p-1.5 text-[var(--muted-foreground)] transition hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
                @click="closeDialog"
              >
                <X :size="16" />
              </button>
            </div>

            <!-- Body -->
            <div class="space-y-4 px-6 py-5">

              <!-- ── LABS form ── -->
              <template v-if="type === 'labs'">
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Date *</label>
                    <input
                      v-model="labDate"
                      type="date"
                      class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
                    />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Analyte *</label>
                    <input
                      v-model="labAnalyte"
                      type="text"
                      placeholder="TSH"
                      class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
                    />
                  </div>
                </div>

                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Valeur *</label>
                    <input
                      v-model="labValue"
                      type="number"
                      step="0.01"
                      placeholder="2.35"
                      class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
                    />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Unité</label>
                    <input
                      v-model="labUnit"
                      type="text"
                      placeholder="mUI/L"
                      class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
                    />
                  </div>
                </div>

                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Réf. basse</label>
                    <input
                      v-model="labRefLow"
                      type="number"
                      step="0.01"
                      placeholder="0.27"
                      class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
                    />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Réf. haute</label>
                    <input
                      v-model="labRefHigh"
                      type="number"
                      step="0.01"
                      placeholder="4.2"
                      class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
                    />
                  </div>
                </div>

                <!-- Out of range preview -->
                <div
                  v-if="labValue && labOutOfRange !== null"
                  class="flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium"
                  :class="labOutOfRange ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-800'"
                >
                  <span>{{ labOutOfRange ? '⚠ Hors normes' : '✓ Dans les normes' }}</span>
                  <span class="opacity-70">
                    (réf. {{ labRefLow }}–{{ labRefHigh }} {{ labUnit }})
                  </span>
                </div>

                <div>
                  <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Laboratoire *</label>
                  <input
                    v-model="labLab"
                    type="text"
                    placeholder="Unilabs, BIOD'OC…"
                    class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
                  />
                </div>

                <div>
                  <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Source (PDF de référence, optionnel)</label>
                  <input
                    v-model="labSource"
                    type="text"
                    placeholder="2026-08-29_Unilabs.pdf"
                    class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
                  />
                </div>
              </template>

              <!-- ── RX form ── -->
              <template v-else>
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Date *</label>
                    <input
                      v-model="rxDate"
                      type="date"
                      class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
                    />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">
                      Dose * {{ doseUnit ? `(${doseUnit})` : '' }}
                    </label>
                    <input
                      v-model="rxDose"
                      type="text"
                      :placeholder="`5 ${doseUnit || 'mg'}`"
                      class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
                    />
                  </div>
                </div>

                <div>
                  <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Posologie *</label>
                  <input
                    v-model="rxPosologie"
                    type="text"
                    placeholder="1 comprimé le matin"
                    class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
                  />
                </div>

                <div>
                  <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Événement *</label>
                  <select
                    v-model="rxEvenement"
                    class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
                  >
                    <option v-for="opt in eventOptions" :key="opt.value" :value="opt.value">
                      {{ opt.label }}
                    </option>
                  </select>
                </div>

                <div>
                  <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Note (optionnel)</label>
                  <textarea
                    v-model="rxNote"
                    rows="2"
                    placeholder="Observations, contexte…"
                    class="w-full resize-none rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
                  />
                </div>
              </template>

              <!-- ── Terminal SSE ── -->
              <div
                v-if="running || lines.length"
                ref="terminalEl"
                class="max-h-36 overflow-y-auto rounded-xl border border-[var(--border)] bg-[oklch(0.12_0.02_165)] px-4 py-3 font-mono text-[11px] leading-5 text-slate-200"
                @vue:updated="scrollBottom"
              >
                <p
                  v-for="(line, i) in lines"
                  :key="i"
                  :class="[
                    line.startsWith('✗') ? 'text-red-400' :
                    line.startsWith('✓') ? 'text-emerald-400' :
                    line.startsWith('▶') ? 'text-[var(--primary)] font-semibold' :
                    'text-slate-300'
                  ]"
                >{{ line }}</p>
                <p v-if="running" class="mt-1 flex items-center gap-1.5 text-slate-400">
                  <Loader :size="11" class="animate-spin" />
                  En cours…
                </p>
              </div>

              <!-- Success -->
              <div v-if="done && !streamError" class="rounded-lg bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
                ✓ Entrée ajoutée et synchronisée avec OVH.
              </div>

              <!-- Error -->
              <div v-if="streamError" class="rounded-lg bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
                ✗ {{ streamError }}
              </div>
            </div>

            <!-- Footer -->
            <div class="flex items-center justify-end gap-2 border-t border-[var(--border)] px-6 py-4">
              <button
                type="button"
                class="rounded-lg px-4 py-2 text-sm text-[var(--muted-foreground)] transition hover:bg-[var(--muted)]"
                @click="closeDialog"
              >
                {{ done ? 'Fermer' : 'Annuler' }}
              </button>
              <button
                v-if="!done"
                type="button"
                :disabled="!canSubmit"
                class="inline-flex items-center gap-2 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] shadow-sm transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
                @click="submit"
              >
                <Loader v-if="running" :size="14" class="animate-spin" />
                <Plus v-else :size="14" />
                {{ running ? 'Enregistrement…' : 'Enregistrer' }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
