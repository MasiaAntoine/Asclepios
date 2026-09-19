<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import {
  AlertTriangle,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Clock,
  MapPin,
  Repeat,
  Settings,
} from '@lucide/vue'
import PageShell from '@/components/PageShell.vue'
import BottomSheet from '@/components/ui/BottomSheet.vue'
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

const WEEKDAYS = ['L', 'M', 'M', 'J', 'V', 'S', 'D']
const WEEKDAYS_DESKTOP = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']

const today = new Date()
const todayKey = dayKey(today)

const cursor = ref(new Date(today.getFullYear(), today.getMonth(), 1))
const selectedDay = ref<string | null>(todayKey)
const isMobile = useMediaQuery('(max-width: 767px)')
const daySheetOpen = ref(false)

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

const weeks = computed<DayCell[][]>(() => {
  const year = cursor.value.getFullYear()
  const month = cursor.value.getMonth()
  const firstOfMonth = new Date(year, month, 1)
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

const EVENT_CHIP_COLORS = [
  'bg-rose-600 text-white',
  'bg-sky-600 text-white',
  'bg-emerald-700 text-white',
  'bg-violet-600 text-white',
  'bg-amber-600 text-white',
  'bg-teal-700 text-white',
  'bg-[var(--primary)] text-[var(--primary-foreground)]',
]

function eventChipClass(title: string) {
  let hash = 0
  for (let i = 0; i < title.length; i += 1) {
    hash = (hash + title.charCodeAt(i) * (i + 1)) % EVENT_CHIP_COLORS.length
  }
  return EVENT_CHIP_COLORS[hash]
}

const notConfigured = computed(() => status.value?.configured === false)

function shiftMonth(delta: number) {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + delta, 1)
}

function goToday() {
  cursor.value = new Date(today.getFullYear(), today.getMonth(), 1)
  selectedDay.value = todayKey
}

function focusDay(key: string) {
  selectedDay.value = key
  const [y, m] = key.split('-').map(Number)
  if (y !== cursor.value.getFullYear() || m - 1 !== cursor.value.getMonth()) {
    cursor.value = new Date(y, m - 1, 1)
  }
  if (isMobile.value) daySheetOpen.value = true
}

onMounted(() => {
  void reload(true)
})
</script>

<template>
  <PageShell flush no-scroll max-width="full">
    <div class="flex h-full min-h-0 flex-col bg-[var(--background)]">
      <div
        v-if="notConfigured"
        class="m-4 rounded-2xl border border-amber-200 bg-amber-50 p-6"
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
          </div>
        </div>
      </div>

      <div
        v-else-if="error && !stale"
        class="m-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
      >
        {{ error }}
      </div>

      <div
        v-else
        class="flex min-h-0 flex-1 flex-col md:overflow-y-auto md:px-8 md:py-6"
      >
        <div
          v-if="stale"
          class="mx-3 mb-3 flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 md:mx-0"
        >
          <AlertTriangle :size="16" class="mt-0.5 shrink-0" />
          <p>
            Google Agenda est injoignable — affichage de la dernière synchronisation connue.
            <span v-if="error" class="text-amber-700">({{ error }})</span>
          </p>
        </div>

        <div
          v-if="nextEvent"
          class="mb-4 hidden overflow-hidden rounded-2xl border border-[var(--primary)]/30 bg-[var(--card)] shadow-sm md:block"
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

        <div class="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] lg:gap-6">
          <div
            class="flex min-h-0 flex-1 flex-col bg-[var(--card)] md:overflow-hidden md:rounded-2xl md:border md:border-[var(--border)] md:shadow-sm"
          >
            <div class="flex shrink-0 items-center justify-between px-3 py-2 md:border-b md:border-[var(--border)] md:px-4 md:py-3">
              <div class="flex items-center gap-1">
                <button
                  type="button"
                  aria-label="Mois précédent"
                  class="rounded-lg p-2 text-[var(--muted-foreground)] hover:bg-[var(--accent)]"
                  @click="shiftMonth(-1)"
                >
                  <ChevronLeft :size="18" />
                </button>
                <p class="min-w-[8rem] text-center text-sm font-semibold capitalize text-[var(--foreground)]">
                  {{ monthLabel }}
                </p>
                <button
                  type="button"
                  aria-label="Mois suivant"
                  class="rounded-lg p-2 text-[var(--muted-foreground)] hover:bg-[var(--accent)]"
                  @click="shiftMonth(1)"
                >
                  <ChevronRight :size="18" />
                </button>
              </div>
              <div class="flex items-center gap-1">
                <button
                  type="button"
                  class="rounded-lg px-2.5 py-1 text-xs font-medium text-[var(--muted-foreground)] hover:bg-[var(--accent)]"
                  @click="goToday"
                >
                  Aujourd'hui
                </button>
              </div>
            </div>

            <div class="grid shrink-0 grid-cols-7 border-b border-[var(--border)]">
              <div
                v-for="(wd, i) in WEEKDAYS"
                :key="wd + i"
                class="py-1.5 text-center text-[11px] font-semibold uppercase tracking-wide md:hidden"
                :class="i === 6 ? 'text-rose-500' : 'text-[var(--muted-foreground)]'"
              >
                {{ wd }}
              </div>
              <div
                v-for="wd in WEEKDAYS_DESKTOP"
                :key="wd"
                class="hidden py-2 text-center text-[10px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)] md:block"
              >
                {{ wd }}
              </div>
            </div>

            <div class="grid min-h-0 flex-1 grid-rows-6">
              <div
                v-for="(week, wIdx) in weeks"
                :key="wIdx"
                class="grid min-h-0 grid-cols-7 border-b border-[var(--border)] last:border-b-0"
              >
                <button
                  v-for="(cell, dIdx) in week"
                  :key="cell.key"
                  type="button"
                  :class="[
                    'flex min-h-0 flex-col overflow-hidden border-r border-[var(--border)] p-0.5 text-left last:border-r-0 md:p-1.5',
                    cell.inMonth ? '' : 'bg-[var(--muted)]/15',
                    selectedDay === cell.key ? 'bg-[var(--primary)]/8' : '',
                  ]"
                  @click="focusDay(cell.key)"
                >
                  <span
                    :class="[
                      'mb-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center self-center rounded-full text-xs font-medium md:self-start',
                      cell.isToday
                        ? 'bg-[var(--primary)] font-bold text-[var(--primary-foreground)]'
                        : !cell.inMonth
                          ? 'text-[var(--muted-foreground)]/40'
                          : dIdx === 6
                            ? 'text-rose-500'
                            : 'text-[var(--foreground)]',
                    ]"
                  >
                    {{ cell.day }}
                  </span>

                  <span
                    v-for="event in cell.events.slice(0, 3)"
                    :key="event.uid + cell.key"
                    class="mb-px truncate rounded-[3px] px-0.5 py-px text-[9px] font-medium leading-tight md:px-1 md:text-[10px]"
                    :class="eventChipClass(event.title)"
                    :title="event.title"
                  >
                    {{ event.title }}
                  </span>
                  <span
                    v-if="cell.events.length > 3"
                    class="px-0.5 text-[9px] font-medium text-[var(--muted-foreground)]"
                  >
                    +{{ cell.events.length - 3 }}
                  </span>
                </button>
              </div>
            </div>
          </div>

          <div class="hidden space-y-6 lg:block">
            <p v-if="lastSyncLabel" class="text-xs text-[var(--muted-foreground)]">
              Lecture seule · maj {{ lastSyncLabel }}
            </p>
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
                </li>
              </ul>
            </div>

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
                    class="w-full rounded-lg px-2 py-2 text-left hover:bg-[var(--accent)]"
                    @click="focusDay(event.start.slice(0, 10))"
                  >
                    <div class="flex items-baseline justify-between gap-2">
                      <p class="truncate text-sm font-medium">{{ event.title }}</p>
                      <Repeat v-if="event.recurring" :size="11" class="shrink-0 text-[var(--muted-foreground)]" />
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
    </div>
  </PageShell>

  <BottomSheet v-model:open="daySheetOpen" :title="selectedDayLabel">
    <p
      v-if="!selectedEvents.length"
      class="text-sm text-[var(--muted-foreground)]"
    >
      Aucun rendez-vous ce jour.
    </p>
    <ul v-else class="space-y-3">
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
      </li>
    </ul>
  </BottomSheet>
</template>
