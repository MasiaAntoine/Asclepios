<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  AlertTriangle,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Clock,
  ExternalLink,
  MapPin,
  RefreshCw,
  Repeat,
  Settings,
} from '@lucide/vue'
import PageShell from '@/components/PageShell.vue'
import {
  useAgenda,
  dayKey,
  formatEventRange,
  formatEventDay,
  formatTime,
  relativeDayLabel,
  type AgendaEvent,
} from '@/composables/useAgenda'

const { eventsByDay, upcoming, nextEvent, status, loading, error, stale, lastSync, reload } =
  useAgenda()

const WEEKDAYS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']

const today = new Date()
const todayKey = dayKey(today)

/** Premier jour du mois affiché. */
const cursor = ref(new Date(today.getFullYear(), today.getMonth(), 1))
const selectedDay = ref<string | null>(todayKey)

const monthLabel = computed(() =>
  cursor.value.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' }),
)

interface DayCell {
  key: string
  day: number
  inMonth: boolean
  isToday: boolean
  events: AgendaEvent[]
}

/** Grille de 6 semaines commençant le lundi, incluant le débord des mois voisins. */
const weeks = computed<DayCell[][]>(() => {
  const year = cursor.value.getFullYear()
  const month = cursor.value.getMonth()

  const firstOfMonth = new Date(year, month, 1)
  // getDay() : 0 = dimanche → on décale pour une semaine démarrant lundi.
  const offset = (firstOfMonth.getDay() + 6) % 7
  const gridStart = new Date(year, month, 1 - offset)

  const result: DayCell[][] = []
  const walker = new Date(gridStart)

  for (let w = 0; w < 6; w += 1) {
    const week: DayCell[] = []
    for (let d = 0; d < 7; d += 1) {
      const key = dayKey(walker)
      week.push({
        key,
        day: walker.getDate(),
        inMonth: walker.getMonth() === month,
        isToday: key === todayKey,
        events: eventsByDay.value.get(key) ?? [],
      })
      walker.setDate(walker.getDate() + 1)
    }
    result.push(week)
  }
  return result
})

const selectedEvents = computed(() =>
  selectedDay.value ? (eventsByDay.value.get(selectedDay.value) ?? []) : [],
)

const selectedDayLabel = computed(() => {
  if (!selectedDay.value) return ''
  const [y, m, d] = selectedDay.value.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })
})

const lastSyncLabel = computed(() => {
  const raw = lastSync.value ?? status.value?.last_sync
  if (!raw) return null
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
})

const notConfigured = computed(() => status.value?.configured === false)

function shiftMonth(delta: number) {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + delta, 1)
}

function goToday() {
  cursor.value = new Date(today.getFullYear(), today.getMonth(), 1)
  selectedDay.value = todayKey
}

/** Sélectionne un jour (`YYYY-MM-DD`) et cadre le mois correspondant. */
function focusDay(key: string) {
  selectedDay.value = key
  const [y, m] = key.split('-').map(Number)
  if (y !== cursor.value.getFullYear() || m - 1 !== cursor.value.getMonth()) {
    cursor.value = new Date(y, m - 1, 1)
  }
}
</script>

<template>
  <PageShell title="Agenda médical" max-width="xl">
    <template #description>
      <p class="mt-0.5 text-sm text-[var(--muted-foreground)]">
        Rendez-vous synchronisés depuis Google Agenda · lecture seule
        <span v-if="lastSyncLabel"> · maj {{ lastSyncLabel }}</span>
      </p>
    </template>

    <template #actions>
      <a
        href="https://calendar.google.com/"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-2 text-sm font-medium text-[var(--foreground)] transition-colors hover:bg-[var(--accent)]"
      >
        <ExternalLink :size="15" />
        Google Agenda
      </a>
      <button
        type="button"
        :disabled="loading"
        class="inline-flex items-center gap-1.5 rounded-lg bg-[var(--primary)] px-3 py-2 text-sm font-medium text-[var(--primary-foreground)] transition-opacity hover:opacity-90 disabled:opacity-50"
        @click="reload(true)"
      >
        <RefreshCw :size="15" :class="loading ? 'animate-spin' : ''" />
        Actualiser
      </button>
    </template>

    <!-- Agenda non configuré : guide de mise en route -->
    <div
      v-if="notConfigured"
      class="rounded-2xl border border-amber-200 bg-amber-50 p-6"
    >
      <div class="flex items-start gap-3">
        <Settings :size="20" class="mt-0.5 shrink-0 text-amber-600" />
        <div class="min-w-0 space-y-3 text-sm text-amber-900">
          <p class="font-semibold">Agenda pas encore connecté</p>
          <p>
            Récupère l'<strong>adresse secrète au format iCal</strong> de ton agenda
            « Médical » dans Google Agenda&nbsp;:
            <em>Paramètres du calendrier → Intégrer l'agenda → Adresse secrète au format iCal</em>.
          </p>
          <p>
            Ajoute-la ensuite dans le fichier <code class="rounded bg-amber-100 px-1 py-0.5">.env</code> :
          </p>
          <pre class="overflow-x-auto rounded-lg bg-amber-100 px-3 py-2 text-xs">{{ status?.env_var }}=https://calendar.google.com/calendar/ical/.../private-.../basic.ics</pre>
          <p class="text-xs">
            L'adresse secrète garde ton agenda <strong>privé</strong> — contrairement à une URL
            publique. Elle reste côté serveur et n'est jamais envoyée au navigateur.
          </p>
        </div>
      </div>
    </div>

    <!-- Erreur de chargement -->
    <div
      v-else-if="error && !stale"
      class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
    >
      {{ error }}
    </div>

    <div v-if="!notConfigured" class="space-y-6" :class="error && !stale ? 'mt-6' : ''">
      <!-- Bandeau snapshot périmé -->
      <div
        v-if="stale"
        class="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
      >
        <AlertTriangle :size="16" class="mt-0.5 shrink-0" />
        <p>
          Google Agenda est injoignable — affichage de la dernière synchronisation connue.
          <span v-if="error" class="text-amber-700">({{ error }})</span>
        </p>
      </div>

      <!-- Prochain rendez-vous en évidence -->
      <div
        v-if="nextEvent"
        class="overflow-hidden rounded-2xl border border-[var(--primary)]/30 bg-[var(--card)] shadow-sm"
      >
        <div class="h-0.5 bg-[var(--primary)]" />
        <div class="flex flex-wrap items-center justify-between gap-4 p-5">
          <div class="min-w-0">
            <p class="text-[11px] font-semibold uppercase tracking-wider text-[var(--primary)]">
              Prochain rendez-vous · {{ relativeDayLabel(nextEvent) }}
            </p>
            <p class="mt-1 truncate text-lg font-bold text-[var(--foreground)]">
              {{ nextEvent.title }}
            </p>
            <div class="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-[var(--muted-foreground)]">
              <span class="inline-flex items-center gap-1.5">
                <CalendarDays :size="14" />
                {{ formatEventDay(nextEvent) }}
              </span>
              <span class="inline-flex items-center gap-1.5">
                <Clock :size="14" />
                {{ formatEventRange(nextEvent) }}
              </span>
              <span v-if="nextEvent.location" class="inline-flex items-center gap-1.5">
                <MapPin :size="14" />
                {{ nextEvent.location }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <!-- Grille du mois -->
        <div class="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-sm">
          <div class="flex items-center justify-between border-b border-[var(--border)] px-4 py-3">
            <p class="text-sm font-semibold capitalize text-[var(--foreground)]">
              {{ monthLabel }}
            </p>
            <div class="flex items-center gap-1">
              <button
                type="button"
                aria-label="Mois précédent"
                class="rounded-lg p-1.5 text-[var(--muted-foreground)] transition-colors hover:bg-[var(--accent)] hover:text-[var(--foreground)]"
                @click="shiftMonth(-1)"
              >
                <ChevronLeft :size="17" />
              </button>
              <button
                type="button"
                class="rounded-lg px-2.5 py-1 text-xs font-medium text-[var(--muted-foreground)] transition-colors hover:bg-[var(--accent)] hover:text-[var(--foreground)]"
                @click="goToday"
              >
                Aujourd'hui
              </button>
              <button
                type="button"
                aria-label="Mois suivant"
                class="rounded-lg p-1.5 text-[var(--muted-foreground)] transition-colors hover:bg-[var(--accent)] hover:text-[var(--foreground)]"
                @click="shiftMonth(1)"
              >
                <ChevronRight :size="17" />
              </button>
            </div>
          </div>

          <!-- En-têtes de jours -->
          <div class="grid grid-cols-7 border-b border-[var(--border)] bg-[var(--muted)]/30">
            <div
              v-for="wd in WEEKDAYS"
              :key="wd"
              class="py-2 text-center text-[10px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)]"
            >
              {{ wd }}
            </div>
          </div>

          <!-- Cases -->
          <div>
            <div
              v-for="(week, wIdx) in weeks"
              :key="wIdx"
              class="grid grid-cols-7 border-b border-[var(--border)] last:border-b-0"
            >
              <button
                v-for="cell in week"
                :key="cell.key"
                type="button"
                :class="[
                  'relative flex min-h-[76px] flex-col gap-1 border-r border-[var(--border)] p-1.5 text-left transition-colors last:border-r-0',
                  cell.inMonth ? '' : 'bg-[var(--muted)]/20',
                  selectedDay === cell.key
                    ? 'bg-[var(--primary)]/8 ring-1 ring-inset ring-[var(--primary)]/40'
                    : 'hover:bg-[var(--accent)]',
                ]"
                @click="focusDay(cell.key)"
              >
                <span
                  :class="[
                    'inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-medium',
                    cell.isToday
                      ? 'bg-[var(--primary)] font-bold text-[var(--primary-foreground)]'
                      : cell.inMonth
                        ? 'text-[var(--foreground)]'
                        : 'text-[var(--muted-foreground)]/50',
                  ]"
                >
                  {{ cell.day }}
                </span>

                <span
                  v-for="event in cell.events.slice(0, 2)"
                  :key="event.uid + cell.key"
                  class="truncate rounded px-1 py-0.5 text-[10px] font-medium leading-tight"
                  :class="
                    event.all_day
                      ? 'bg-[var(--primary)]/15 text-[var(--primary)]'
                      : 'bg-[var(--accent)] text-[var(--accent-foreground)]'
                  "
                  :title="event.title"
                >
                  <template v-if="!event.all_day">{{ formatTime(event) }} </template>{{ event.title }}
                </span>
                <span
                  v-if="cell.events.length > 2"
                  class="px-1 text-[10px] font-medium text-[var(--muted-foreground)]"
                >
                  +{{ cell.events.length - 2 }}
                </span>
              </button>
            </div>
          </div>
        </div>

        <!-- Colonne latérale -->
        <div class="space-y-6">
          <!-- Détail du jour sélectionné -->
          <div class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 shadow-sm">
            <p class="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
              Jour sélectionné
            </p>
            <p class="mt-1 text-sm font-semibold capitalize text-[var(--foreground)]">
              {{ selectedDayLabel || '—' }}
            </p>

            <p
              v-if="!selectedEvents.length"
              class="mt-3 text-sm text-[var(--muted-foreground)]"
            >
              Aucun rendez-vous ce jour.
            </p>

            <ul v-else class="mt-3 space-y-3">
              <li
                v-for="event in selectedEvents"
                :key="event.uid"
                class="border-l-2 border-[var(--primary)] pl-3"
              >
                <p class="text-sm font-medium text-[var(--foreground)]">{{ event.title }}</p>
                <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">
                  {{ formatEventRange(event) }}
                </p>
                <p
                  v-if="event.location"
                  class="mt-0.5 inline-flex items-center gap-1 text-xs text-[var(--muted-foreground)]"
                >
                  <MapPin :size="11" />
                  {{ event.location }}
                </p>
                <p
                  v-if="event.description"
                  class="mt-1 whitespace-pre-line text-xs text-[var(--muted-foreground)]"
                >
                  {{ event.description }}
                </p>
              </li>
            </ul>
          </div>

          <!-- Prochains rendez-vous -->
          <div class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 shadow-sm">
            <div class="flex items-center justify-between">
              <p class="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                À venir
              </p>
              <span class="text-xs text-[var(--muted-foreground)]">{{ upcoming.length }}</span>
            </div>

            <p
              v-if="loading && !upcoming.length"
              class="mt-3 text-sm text-[var(--muted-foreground)]"
            >
              Chargement…
            </p>
            <p
              v-else-if="!upcoming.length"
              class="mt-3 text-sm text-[var(--muted-foreground)]"
            >
              Aucun rendez-vous à venir.
            </p>

            <ul v-else class="mt-3 space-y-1">
              <li v-for="event in upcoming.slice(0, 8)" :key="event.uid">
                <button
                  type="button"
                  class="w-full rounded-lg px-2 py-2 text-left transition-colors hover:bg-[var(--accent)]"
                  @click="focusDay(event.start.slice(0, 10))"
                >
                  <div class="flex items-baseline justify-between gap-2">
                    <p class="truncate text-sm font-medium text-[var(--foreground)]">
                      {{ event.title }}
                    </p>
                    <span
                      v-if="event.recurring"
                      class="shrink-0 text-[var(--muted-foreground)]"
                      title="Rendez-vous récurrent"
                    >
                      <Repeat :size="11" />
                    </span>
                  </div>
                  <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">
                    {{ formatEventDay(event) }} · {{ formatTime(event) }}
                  </p>
                </button>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </PageShell>
</template>
