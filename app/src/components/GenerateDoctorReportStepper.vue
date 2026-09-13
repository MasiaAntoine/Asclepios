<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  CalendarRange,
  Check,
  FileText,
  Loader2,
  Maximize2,
  Minimize2,
} from '@lucide/vue'
import StepperDrawer, { type StepperStep } from '@/components/StepperDrawer.vue'
import { useDoctors, doctorFullName, doctorPhotoUrl, type Doctor } from '@/composables/useDoctors'
import { parseEventDate, formatTime, type AgendaEvent } from '@/composables/useAgenda'
import { apiFetch } from '@/lib/apiFetch'

const props = defineProps<{
  initialDoctorId?: string | null
}>()

const emit = defineEmits<{
  generated: [reportId: string]
}>()

const open = defineModel<boolean>('open', { default: false })

const steps: StepperStep[] = [
  { id: 'doctor', label: 'Médecin' },
  { id: 'size', label: 'Format' },
  { id: 'period', label: 'Période' },
  { id: 'content', label: 'Contenu' },
]

const router = useRouter()
const { doctors } = useDoctors()

const step = ref(0)
const doctorId = ref('')
const size = ref<'petit' | 'grand'>('petit')
const dateFrom = ref('')
const dateTo = ref('')
const datesTouched = ref(false)
const include = ref<Record<string, boolean>>({})
const contextLoading = ref(false)
const contextError = ref<string | null>(null)
const events = ref<AgendaEvent[]>([])
const suggestionReason = ref('')
const lastVisit = ref<AgendaEvent | null>(null)
const nextVisit = ref<AgendaEvent | null>(null)
const includeOptions = ref<{ id: string; label: string; hint: string; default: boolean }[]>([])

const running = ref(false)
const logs = ref<string[]>([])
const generatedId = ref<string | null>(null)
const hasError = ref(false)

const selectedDoctor = computed(
  () => doctors.value.find((d) => d.id === doctorId.value) ?? null,
)

const canNext = computed(() => {
  if (step.value === 0) return Boolean(doctorId.value)
  if (step.value === 1) return size.value === 'petit' || size.value === 'grand'
  if (step.value === 2) return Boolean(dateFrom.value && dateTo.value)
  if (step.value === 3) return Object.values(include.value).some(Boolean) && !running.value
  return true
})

const submitLabel = computed(() => (running.value ? 'Génération…' : 'Générer le rapport'))

function formatDay(event: AgendaEvent | null) {
  if (!event) return '—'
  return parseEventDate(event.start).toLocaleDateString('fr-FR', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function reset() {
  step.value = 0
  doctorId.value = props.initialDoctorId || ''
  size.value = 'petit'
  dateFrom.value = ''
  dateTo.value = ''
  datesTouched.value = false
  include.value = {}
  events.value = []
  suggestionReason.value = ''
  lastVisit.value = null
  nextVisit.value = null
  includeOptions.value = []
  contextError.value = null
  running.value = false
  logs.value = []
  generatedId.value = null
  hasError.value = false
}

watch(open, (value) => {
  if (value) {
    const previous = doctorId.value
    reset()
    if (doctorId.value && doctorId.value === previous) void loadContext()
  }
})

watch(doctorId, () => {
  if (!open.value) return
  datesTouched.value = false
  void loadContext()
})

let contextSeq = 0
async function loadContext() {
  if (!doctorId.value) return
  const seq = ++contextSeq
  contextLoading.value = true
  contextError.value = null
  try {
    const params = new URLSearchParams({ doctor_id: doctorId.value })
    if (datesTouched.value && dateFrom.value && dateTo.value) {
      params.set('date_from', dateFrom.value)
      params.set('date_to', dateTo.value)
    }
    const res = await apiFetch(`/api/reports/doctor-context?${params}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (seq !== contextSeq) return
    events.value = data.events ?? []
    suggestionReason.value = data.suggestion?.reason ?? ''
    lastVisit.value = data.suggestion?.last_visit ?? null
    nextVisit.value = data.suggestion?.next_visit ?? null
    if (!datesTouched.value) {
      dateFrom.value = data.suggestion?.date_from ?? data.date_from
      dateTo.value = data.suggestion?.date_to ?? data.date_to
    }
    includeOptions.value = data.include_options ?? []
    const nextInclude: Record<string, boolean> = { ...include.value }
    for (const opt of includeOptions.value) {
      if (!(opt.id in nextInclude)) nextInclude[opt.id] = opt.default
    }
    include.value = nextInclude
  } catch (e) {
    if (seq !== contextSeq) return
    contextError.value = e instanceof Error ? e.message : 'Impossible de charger le contexte'
  } finally {
    if (seq === contextSeq) contextLoading.value = false
  }
}

async function onDatesBlur() {
  datesTouched.value = true
  await loadContext()
}

function applySuggestion() {
  datesTouched.value = false
  void loadContext()
}

async function generate() {
  if (running.value || !doctorId.value) return
  running.value = true
  hasError.value = false
  generatedId.value = null
  logs.value = []
  try {
    const res = await apiFetch('/api/reports/generate-for-doctor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        doctor_id: doctorId.value,
        size: size.value,
        date_from: dateFrom.value,
        date_to: dateTo.value,
        include: Object.entries(include.value)
          .filter(([, v]) => v)
          .map(([k]) => k),
      }),
    })
    if (!res.ok || !res.body) {
      logs.value.push(`Erreur HTTP ${res.status}`)
      hasError.value = true
      running.value = false
      return
    }
    const reader = res.body.getReader()
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
        }
      }
    }
  } catch (err) {
    logs.value.push(`Erreur réseau : ${err}`)
    hasError.value = true
  } finally {
    running.value = false
  }
}

function openReport() {
  if (!generatedId.value) return
  open.value = false
  router.push(`/rapports/${generatedId.value}`)
}

function initials(doctor: Doctor) {
  return `${doctor.prenom[0] ?? ''}${doctor.nom[0] ?? ''}`.toUpperCase()
}

const periodEvents = computed(() => {
  if (!dateFrom.value || !dateTo.value) return events.value
  return events.value.filter((e) => {
    const d = e.start.slice(0, 10)
    return d >= dateFrom.value && d <= dateTo.value
  })
})
</script>

<template>
  <StepperDrawer
    v-model:open="open"
    v-model:index="step"
    title="Rapport pour un médecin"
    description="Dossier de synthèse à déposer dans Rapports"
    :steps="steps"
    wide
    :can-next="canNext"
    :submitting="running"
    :submit-label="submitLabel"
    @submit="generate"
  >
    <!-- Étape 1 : médecin -->
    <div v-if="step === 0" class="space-y-3">
      <p class="text-sm text-[var(--muted-foreground)]">
        Quel praticien doit recevoir ce dossier ?
      </p>
      <button
        v-for="doctor in doctors"
        :key="doctor.id"
        type="button"
        class="flex w-full items-center gap-3 rounded-xl border p-3 text-left transition"
        :class="
          doctorId === doctor.id
            ? 'border-[var(--primary)] bg-[var(--accent)]/40 ring-2 ring-[var(--primary)]/20'
            : 'border-[var(--border)] hover:border-[var(--primary)]/40'
        "
        @click="doctorId = doctor.id"
      >
        <img
          v-if="doctorPhotoUrl(doctor)"
          :src="doctorPhotoUrl(doctor)!"
          :alt="doctorFullName(doctor)"
          class="h-11 w-11 rounded-full object-cover"
        />
        <div
          v-else
          class="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--primary)] text-sm font-bold text-white"
        >
          {{ initials(doctor) }}
        </div>
        <div class="min-w-0 flex-1">
          <p class="font-medium text-[var(--foreground)]">{{ doctorFullName(doctor) }}</p>
          <p class="text-xs text-[var(--primary)]">{{ doctor.specialite }}</p>
        </div>
        <span
          v-if="doctorId === doctor.id"
          class="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--primary)] text-white"
        >
          <Check :size="13" />
        </span>
      </button>
    </div>

    <!-- Étape 2 : taille -->
    <div v-else-if="step === 1" class="grid gap-3">
      <button
        type="button"
        class="rounded-2xl border p-4 text-left transition"
        :class="
          size === 'petit'
            ? 'border-[var(--primary)] bg-[var(--accent)]/40 ring-2 ring-[var(--primary)]/20'
            : 'border-[var(--border)] hover:border-[var(--primary)]/40'
        "
        @click="size = 'petit'"
      >
        <div class="flex items-center gap-2 font-semibold text-[var(--foreground)]">
          <Minimize2 :size="16" class="text-[var(--primary)]" />
          Petit
        </div>
        <p class="mt-1 text-sm text-[var(--muted-foreground)]">
          Synthèse courte : points clés, tableaux condensés, 1–2 courbes.
        </p>
      </button>
      <button
        type="button"
        class="rounded-2xl border p-4 text-left transition"
        :class="
          size === 'grand'
            ? 'border-[var(--primary)] bg-[var(--accent)]/40 ring-2 ring-[var(--primary)]/20'
            : 'border-[var(--border)] hover:border-[var(--primary)]/40'
        "
        @click="size = 'grand'"
      >
        <div class="flex items-center gap-2 font-semibold text-[var(--foreground)]">
          <Maximize2 :size="16" class="text-[var(--primary)]" />
          Grand
        </div>
        <p class="mt-1 text-sm text-[var(--muted-foreground)]">
          Dossier complet : chronologie, extraits de rapports, courbes et historique détaillé.
        </p>
      </button>
    </div>

    <!-- Étape 3 : période -->
    <div v-else-if="step === 2" class="space-y-4">
      <p v-if="contextLoading" class="text-sm text-[var(--muted-foreground)]">
        Lecture de l’agenda…
      </p>
      <p v-else-if="contextError" class="text-sm text-red-600">{{ contextError }}</p>
      <div
        v-else
        class="rounded-xl border border-[var(--border)] bg-[var(--accent)]/30 p-3 text-sm text-[var(--foreground)]"
      >
        <p class="flex items-center gap-1.5 font-medium">
          <CalendarRange :size="15" class="text-[var(--primary)]" />
          Proposition
        </p>
        <p class="mt-1 text-[var(--muted-foreground)]">{{ suggestionReason }}</p>
        <p v-if="lastVisit || nextVisit" class="mt-2 text-xs text-[var(--muted-foreground)]">
          Dernier RDV : {{ formatDay(lastVisit) }}
          <span class="mx-1">·</span>
          Prochain : {{ formatDay(nextVisit) }}
        </p>
        <button
          v-if="datesTouched"
          type="button"
          class="mt-2 text-xs font-medium text-[var(--primary)] hover:underline"
          @click="applySuggestion"
        >
          Reprendre la proposition
        </button>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <label class="text-xs font-medium text-[var(--muted-foreground)]">
          Du
          <input
            v-model="dateFrom"
            type="date"
            class="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)]"
            @change="onDatesBlur"
          />
        </label>
        <label class="text-xs font-medium text-[var(--muted-foreground)]">
          Au
          <input
            v-model="dateTo"
            type="date"
            class="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)]"
            @change="onDatesBlur"
          />
        </label>
      </div>

      <div>
        <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
          RDV retenus ({{ periodEvents.length }})
        </p>
        <ul v-if="periodEvents.length" class="space-y-1.5">
          <li
            v-for="ev in periodEvents"
            :key="ev.uid + ev.start"
            class="rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
          >
            <span class="font-medium text-[var(--foreground)]">{{ ev.title }}</span>
            <span class="mt-0.5 block text-xs text-[var(--muted-foreground)]">
              {{ formatDay(ev) }}
              <template v-if="!ev.all_day"> · {{ formatTime(ev) }}</template>
            </span>
          </li>
        </ul>
        <p v-else class="text-sm text-[var(--muted-foreground)]">
          Aucun rendez-vous identifié pour ce praticien sur la période.
        </p>
      </div>
    </div>

    <!-- Étape 4 : contenu -->
    <div v-else class="space-y-4">
      <p class="text-sm text-[var(--muted-foreground)]">
        Coche ce qui doit figurer dans le dossier
        <template v-if="selectedDoctor">
          pour {{ doctorFullName(selectedDoctor) }}.
        </template>
        Les courbes sont ajoutées quand un suivi chiffré est coché.
      </p>
      <label
        v-for="opt in includeOptions"
        :key="opt.id"
        class="flex cursor-pointer items-start gap-3 rounded-xl border border-[var(--border)] p-3 transition hover:bg-[var(--accent)]/30"
      >
        <input
          v-model="include[opt.id]"
          type="checkbox"
          class="mt-1 h-4 w-4 rounded border-[var(--border)] text-[var(--primary)]"
        />
        <span>
          <span class="block text-sm font-medium text-[var(--foreground)]">{{ opt.label }}</span>
          <span class="text-xs text-[var(--muted-foreground)]">{{ opt.hint }}</span>
        </span>
      </label>

      <div
        v-if="logs.length || running"
        class="max-h-40 overflow-y-auto rounded-xl border border-[var(--border)] bg-[#0d1117] p-3 font-mono text-[11px] leading-relaxed text-emerald-400"
      >
        <p v-for="(line, i) in logs" :key="i">{{ line }}</p>
        <p v-if="running" class="mt-1 flex items-center gap-1.5 text-emerald-300/70">
          <Loader2 :size="11" class="animate-spin" /> En cours…
        </p>
      </div>

      <div
        v-if="generatedId && !hasError"
        class="flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-700"
      >
        <span class="flex items-center gap-2">
          <FileText :size="16" />
          Rapport enregistré
        </span>
        <button type="button" class="font-medium underline" @click="openReport">
          Ouvrir
        </button>
      </div>
      <p v-if="hasError" class="text-sm text-red-600">La génération a échoué.</p>
    </div>
  </StepperDrawer>
</template>
