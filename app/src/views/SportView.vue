<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  Bell,
  Check,
  ChevronDown,
  ChevronUp,
  Loader,
  Plus,
  Trash2,
  X,
} from '@lucide/vue'
import PageShell from '@/components/PageShell.vue'
import { useSport, type SportLogItem } from '@/composables/useSport'
import {
  EXERCISE_CATALOG,
  formatNotifyAt,
  formatPrescription,
  type SportCatalogItem,
  type SportExercise,
} from '@/lib/sport'

const {
  exercises,
  loading,
  error,
  notifyAt,
  notifyLabel,
  todayAnswers,
  todayDoneCount,
  todayComplete,
  todayPending,
  recentSessions,
  saveProgram,
  answerExercise,
  saveNotifyAt,
} = useSport()

const savingId = ref<string | null>(null)
const programSaving = ref(false)
const notifyDraft = ref('')
const notifySaving = ref(false)
const notifyError = ref<string | null>(null)
const editorOpen = ref(false)
const editorIndex = ref<number | null>(null)
const editorName = ref('')
const editorSets = ref('3')
const editorReps = ref('10')
const editorSeconds = ref('')
const editorNote = ref('')
const editorError = ref<string | null>(null)
const editorExisting = computed(() => editorIndex.value != null)

const inputClass =
  'w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20'

watch(
  notifyAt,
  (value) => {
    notifyDraft.value = value
  },
  { immediate: true },
)

async function persistNotify(value: string) {
  if (notifySaving.value) return
  const next = value.trim()
  if (next === notifyAt.value) return
  notifySaving.value = true
  notifyError.value = null
  try {
    await saveNotifyAt(next)
  } catch (e) {
    notifyError.value = e instanceof Error ? e.message : 'Enregistrement impossible'
    notifyDraft.value = notifyAt.value
  } finally {
    notifySaving.value = false
  }
}

function onNotifyChange() {
  void persistNotify(notifyDraft.value)
}

function clearNotify() {
  notifyDraft.value = ''
  void persistNotify('')
}

function openNew() {
  editorIndex.value = null
  editorName.value = ''
  editorSets.value = '3'
  editorReps.value = '10'
  editorSeconds.value = ''
  editorNote.value = ''
  editorError.value = null
  editorOpen.value = true
}

function openEdit(index: number) {
  const exo = exercises.value[index]
  if (!exo) return
  editorIndex.value = index
  editorName.value = exo.name
  editorSets.value = String(exo.sets)
  editorReps.value = exo.reps != null ? String(exo.reps) : ''
  editorSeconds.value = exo.seconds != null ? String(exo.seconds) : ''
  editorNote.value = exo.note
  editorError.value = null
  editorOpen.value = true
}

function applyCatalog(item: SportCatalogItem) {
  editorName.value = item.name
  editorSets.value = String(item.sets)
  editorReps.value = item.reps != null ? String(item.reps) : ''
  editorSeconds.value = item.seconds != null ? String(item.seconds) : ''
}

function closeEditor() {
  if (!programSaving.value) editorOpen.value = false
}

function draftExercise(): SportExercise | null {
  const name = editorName.value.trim()
  const sets = Number.parseInt(editorSets.value, 10)
  if (!name || !Number.isFinite(sets) || sets < 1) return null
  const repsRaw = editorReps.value.trim()
  const secRaw = editorSeconds.value.trim()
  const reps = repsRaw ? Number.parseInt(repsRaw, 10) : null
  const seconds = secRaw ? Number.parseInt(secRaw, 10) : null
  const existing =
    editorIndex.value != null ? exercises.value[editorIndex.value] : null
  return {
    id: existing?.id ?? '',
    name,
    sets,
    reps: reps && reps > 0 ? reps : null,
    seconds: seconds && seconds > 0 ? seconds : null,
    note: editorNote.value.trim(),
  }
}

async function submitEditor() {
  const draft = draftExercise()
  if (!draft) {
    editorError.value = 'Nom et séries sont requis'
    return
  }
  programSaving.value = true
  editorError.value = null
  try {
    const next = exercises.value.slice()
    if (editorIndex.value != null) next[editorIndex.value] = draft
    else next.push(draft)
    await saveProgram(next)
    editorOpen.value = false
  } catch (e) {
    editorError.value = e instanceof Error ? e.message : 'Enregistrement impossible'
  } finally {
    programSaving.value = false
  }
}

async function removeExercise(index: number) {
  const exo = exercises.value[index]
  if (!exo) return
  programSaving.value = true
  try {
    const next = exercises.value.filter((_, i) => i !== index)
    await saveProgram(next)
  } finally {
    programSaving.value = false
  }
}

async function moveExercise(index: number, delta: number) {
  const target = index + delta
  if (target < 0 || target >= exercises.value.length) return
  const next = exercises.value.slice()
  const [row] = next.splice(index, 1)
  next.splice(target, 0, row)
  programSaving.value = true
  try {
    await saveProgram(next)
  } finally {
    programSaving.value = false
  }
}

async function onAnswer(id: string, done: boolean) {
  if (savingId.value) return
  savingId.value = id
  try {
    await answerExercise(id, done)
  } finally {
    savingId.value = null
  }
}

function sessionLabel(date: string) {
  const [y, m, d] = date.split('-').map(Number)
  const dt = new Date(y, (m ?? 1) - 1, d ?? 1)
  return dt.toLocaleDateString('fr-FR', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
}

function sessionStats(items: { done: boolean }[]) {
  const done = items.filter((i) => i.done).length
  return `${done}/${items.length}`
}

function sessionTime(at: string) {
  if (!at) return ''
  const date = new Date(at)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}

function historyItem(item: SportLogItem) {
  const exo = exercises.value.find((e) => e.id === item.exercise_id)
  return {
    id: item.exercise_id,
    name: item.name || exo?.name || item.exercise_id,
    prescription: formatPrescription({
      sets: item.sets ?? exo?.sets ?? 1,
      reps: item.reps ?? exo?.reps ?? null,
      seconds: item.seconds ?? exo?.seconds ?? null,
    }),
    note: item.note || exo?.note || '',
    done: item.done,
  }
}

const detailedSessions = computed(() =>
  recentSessions.value.map((session) => ({
    date: session.date,
    at: session.at,
    items: session.items,
    rows: session.items.map(historyItem),
  })),
)
</script>

<template>
  <PageShell title="Sport" max-width="lg">
    <template #description>
      <p class="mt-0.5 text-sm text-[var(--muted-foreground)]">
        {{ exercises.length }} exercice{{ exercises.length > 1 ? 's' : '' }}
        <template v-if="notifyLabel"> · rappel à {{ notifyLabel }}</template>
        <template v-else> · pas de rappel</template>
      </p>
    </template>

    <div class="space-y-6">
      <div v-if="error" class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {{ error }}
      </div>
      <div v-else-if="loading && !exercises.length" class="py-16 text-center text-sm text-[var(--muted-foreground)]">
        Chargement…
      </div>

      <template v-else>
        <section class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 sm:p-5">
          <div class="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p class="text-sm font-semibold text-[var(--foreground)]">Séance du jour</p>
              <p class="text-xs text-[var(--muted-foreground)]">
                <template v-if="!exercises.length">Compose d’abord ton programme.</template>
                <template v-else-if="todayComplete">
                  {{ todayDoneCount }}/{{ exercises.length }} fait{{ todayDoneCount > 1 ? 's' : '' }}
                </template>
                <template v-else>
                  {{ todayPending.length }} à noter
                  <template v-if="notifyAt"> · notif à {{ formatNotifyAt(notifyAt) }}</template>
                </template>
              </p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <label class="inline-flex min-h-11 items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-1.5">
                <Bell :size="15" class="text-[var(--primary)]" />
                <span class="text-xs font-medium text-[var(--muted-foreground)]">Rappel</span>
                <input
                  v-model="notifyDraft"
                  type="time"
                  class="bg-transparent text-sm text-[var(--foreground)] focus:outline-none"
                  :disabled="notifySaving"
                  @change="onNotifyChange"
                />
              </label>
              <button
                v-if="notifyDraft"
                type="button"
                class="rounded-lg px-2 py-2 text-xs text-[var(--muted-foreground)] hover:bg-[var(--muted)]"
                :disabled="notifySaving"
                @click="clearNotify"
              >
                Aucun
              </button>
              <Loader v-if="notifySaving" :size="14" class="animate-spin text-[var(--muted-foreground)]" />
            </div>
          </div>
          <p v-if="notifyError" class="mb-3 text-xs text-red-600">{{ notifyError }}</p>

          <p
            v-if="!exercises.length"
            class="rounded-xl border border-dashed border-[var(--border)] px-4 py-8 text-center text-sm text-[var(--muted-foreground)]"
          >
            Ajoute tes exercices ci-dessous (pompes, squats, gainage…).
          </p>

          <ul v-else class="space-y-2">
            <li
              v-for="exo in exercises"
              :key="exo.id"
              class="rounded-xl border border-[var(--border)] px-3 py-3"
            >
              <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div class="min-w-0">
                  <p class="text-sm font-medium text-[var(--foreground)]">{{ exo.name }}</p>
                  <p class="text-xs text-[var(--muted-foreground)]">
                    {{ formatPrescription(exo) }}
                    <template v-if="exo.note"> · {{ exo.note }}</template>
                  </p>
                </div>
                <div class="flex gap-2">
                  <button
                    type="button"
                    class="inline-flex min-h-11 flex-1 items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium transition sm:flex-none"
                    :class="
                      todayAnswers[exo.id] === true
                        ? 'border-emerald-300 bg-emerald-50 text-emerald-800'
                        : 'border-[var(--border)] text-[var(--foreground)] hover:bg-[var(--accent)]/50'
                    "
                    :disabled="savingId === exo.id"
                    @click="onAnswer(exo.id, true)"
                  >
                    <Check :size="15" />
                    Fait
                  </button>
                  <button
                    type="button"
                    class="inline-flex min-h-11 flex-1 items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium transition sm:flex-none"
                    :class="
                      todayAnswers[exo.id] === false
                        ? 'border-red-200 bg-red-50 text-red-800'
                        : 'border-[var(--border)] text-[var(--foreground)] hover:bg-[var(--accent)]/50'
                    "
                    :disabled="savingId === exo.id"
                    @click="onAnswer(exo.id, false)"
                  >
                    <X :size="15" />
                    Pas fait
                  </button>
                </div>
              </div>
            </li>
          </ul>
        </section>

        <section class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 sm:p-5">
          <div class="mb-3 flex items-center justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-[var(--foreground)]">Programme</p>
              <p class="text-xs text-[var(--muted-foreground)]">
                Ordre, séries et répétitions (ou secondes).
              </p>
            </div>
            <button
              type="button"
              class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--primary)]/30 bg-[var(--primary)]/8 px-3 py-2 text-sm font-medium text-[var(--primary)] hover:bg-[var(--primary)]/15"
              @click="openNew"
            >
              <Plus :size="15" />
              Ajouter
            </button>
          </div>

          <ul v-if="exercises.length" class="divide-y divide-[var(--border)] overflow-hidden rounded-xl border border-[var(--border)]">
            <li
              v-for="(exo, index) in exercises"
              :key="exo.id"
              class="flex items-center gap-2 px-3 py-2.5"
            >
              <div class="flex flex-col">
                <button
                  type="button"
                  class="rounded p-1 text-[var(--muted-foreground)] hover:bg-[var(--muted)] disabled:opacity-30"
                  :disabled="index === 0 || programSaving"
                  @click="moveExercise(index, -1)"
                >
                  <ChevronUp :size="14" />
                </button>
                <button
                  type="button"
                  class="rounded p-1 text-[var(--muted-foreground)] hover:bg-[var(--muted)] disabled:opacity-30"
                  :disabled="index === exercises.length - 1 || programSaving"
                  @click="moveExercise(index, 1)"
                >
                  <ChevronDown :size="14" />
                </button>
              </div>
              <button
                type="button"
                class="min-w-0 flex-1 text-left"
                @click="openEdit(index)"
              >
                <p class="text-sm font-medium text-[var(--foreground)]">{{ exo.name }}</p>
                <p class="text-xs text-[var(--muted-foreground)]">{{ formatPrescription(exo) }}</p>
              </button>
              <button
                type="button"
                class="rounded-lg p-2 text-[var(--muted-foreground)] hover:bg-red-50 hover:text-red-700"
                :disabled="programSaving"
                @click="removeExercise(index)"
              >
                <Trash2 :size="15" />
              </button>
            </li>
          </ul>
          <p
            v-else
            class="rounded-xl border border-dashed border-[var(--border)] px-4 py-6 text-center text-sm text-[var(--muted-foreground)]"
          >
            Pas encore d’exercice. Choisis-en dans le catalogue, ou crée le tien.
          </p>
        </section>

        <section
          v-if="detailedSessions.length"
          class="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)]"
        >
          <div class="border-b border-[var(--border)] px-5 py-3">
            <h2 class="text-sm font-semibold">Historique</h2>
          </div>
          <ul class="divide-y divide-[var(--border)]">
            <li
              v-for="session in detailedSessions"
              :key="session.date"
              class="px-4 py-3"
            >
              <div class="mb-2 flex items-baseline justify-between gap-3">
                <p class="text-sm capitalize text-[var(--foreground)]">
                  {{ sessionLabel(session.date) }}
                  <span v-if="sessionTime(session.at)" class="font-normal text-[var(--muted-foreground)]">
                    · {{ sessionTime(session.at) }}
                  </span>
                </p>
                <p class="text-xs font-medium tabular-nums text-[var(--muted-foreground)]">
                  {{ sessionStats(session.items) }} faits
                </p>
              </div>
              <ul class="space-y-1.5">
                <li
                  v-for="row in session.rows"
                  :key="row.id"
                  class="flex items-start justify-between gap-3 text-xs"
                >
                  <div class="min-w-0">
                    <p class="font-medium text-[var(--foreground)]">{{ row.name }}</p>
                    <p class="text-[var(--muted-foreground)]">
                      {{ row.prescription }}
                      <template v-if="row.note"> · {{ row.note }}</template>
                    </p>
                  </div>
                  <span
                    class="shrink-0 font-medium"
                    :class="row.done ? 'text-emerald-700' : 'text-red-700'"
                  >
                    {{ row.done ? 'fait' : 'pas fait' }}
                  </span>
                </li>
              </ul>
            </li>
          </ul>
        </section>
      </template>
    </div>
  </PageShell>

  <Teleport to="body">
    <div
      v-if="editorOpen"
      class="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center sm:p-4 backdrop-blur-sm"
      @click.self="closeEditor"
    >
      <div class="relative max-h-[100dvh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-[var(--card)] pb-[env(safe-area-inset-bottom)] shadow-2xl ring-1 ring-[var(--border)] sm:max-h-[90vh] sm:rounded-2xl sm:pb-0">
        <div class="flex items-center justify-between border-b border-[var(--border)] px-5 py-4">
          <div>
            <h2 class="text-base font-semibold text-[var(--foreground)]">
              {{ editorExisting ? 'Modifier l’exercice' : 'Ajouter un exercice' }}
            </h2>
            <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">
              Catalogue ou exercice perso · séries et répétitions
            </p>
          </div>
          <button
            type="button"
            class="rounded-lg p-1.5 text-[var(--muted-foreground)] hover:bg-[var(--muted)]"
            @click="closeEditor"
          >
            <X :size="16" />
          </button>
        </div>
        <div class="space-y-4 px-5 py-5">
          <div>
            <p class="mb-2 text-xs font-medium text-[var(--muted-foreground)]">Catalogue</p>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="item in EXERCISE_CATALOG"
                :key="item.name"
                type="button"
                class="rounded-lg border border-[var(--border)] px-2.5 py-1.5 text-xs font-medium text-[var(--foreground)] hover:bg-[var(--accent)]/50"
                @click="applyCatalog(item)"
              >
                {{ item.name }}
              </button>
            </div>
          </div>
          <div>
            <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Nom *</label>
            <input v-model="editorName" type="text" :class="inputClass" />
          </div>
          <div class="grid grid-cols-3 gap-3">
            <div>
              <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Séries *</label>
              <input v-model="editorSets" type="number" min="1" max="20" :class="inputClass" />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Répétitions</label>
              <input v-model="editorReps" type="number" min="1" max="200" :class="inputClass" />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Secondes</label>
              <input v-model="editorSeconds" type="number" min="5" max="600" :class="inputClass" />
            </div>
          </div>
          <p class="text-[11px] text-[var(--muted-foreground)]">
            Pour un gainage, laisse les répétitions vides et renseigne les secondes.
          </p>
          <div>
            <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Note</label>
            <input v-model="editorNote" type="text" placeholder="tempo, variante…" :class="inputClass" />
          </div>
          <p v-if="editorError" class="text-xs text-red-600">{{ editorError }}</p>
        </div>
        <div class="flex justify-end gap-2 border-t border-[var(--border)] px-5 py-4">
          <button
            type="button"
            class="rounded-lg px-3 py-2 text-sm text-[var(--muted-foreground)] hover:bg-[var(--muted)]"
            :disabled="programSaving"
            @click="closeEditor"
          >
            Annuler
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-2 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] disabled:opacity-50"
            :disabled="programSaving"
            @click="submitEditor"
          >
            <Loader v-if="programSaving" :size="14" class="animate-spin" />
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
