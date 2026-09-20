<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  TimeScale,
} from 'chart.js'
import { Line } from 'vue-chartjs'
import type { ChartOptions, TooltipItem } from 'chart.js'
import 'chartjs-adapter-date-fns'
import { fr } from 'date-fns/locale'
import { Plus, X, Loader } from '@lucide/vue'
import PageShell from '@/components/PageShell.vue'
import MoodScale from '@/components/MoodScale.vue'
import OwlEmotionIcon from '@/components/OwlEmotionIcon.vue'
import DateRangeFilter from '@/components/DateRangeFilter.vue'
import { useMood } from '@/composables/useMood'
import { useDateRange } from '@/composables/useDateRange'
import { baseChartOptions, chartColors, formatFrDate } from '@/lib/chartTheme'
import {
  formatMoodDate,
  moodColor,
  moodLabel,
  moodOwl,
  parseIsoDate,
  todayIso,
} from '@/lib/mood'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  TimeScale,
)

const route = useRoute()
const router = useRouter()
const { entries, byDate, today, moyenne7j, missingDays, loading, error, saveMood } = useMood()

const lastDate = computed(() =>
  entries.value.length ? entries.value[entries.value.length - 1].dateObj : null,
)
const { preset, customFrom, customTo, inRange, setPreset } = useDateRange(lastDate)

const filtered = computed(() => entries.value.filter((e) => inRange(e.dateObj)))
const tableRows = computed(() => [...filtered.value].reverse())

const editorOpen = ref(false)
const editorDate = ref(todayIso())
const editorScore = ref<number | null>(null)
const editorSaving = ref(false)
const editorError = ref<string | null>(null)
const editorExisting = computed(() => Boolean(byDate.value[editorDate.value]))

watch(editorDate, (date) => {
  editorScore.value = byDate.value[date]?.score ?? null
})

function openEditor(date = todayIso(), score: number | null = byDate.value[date]?.score ?? null) {
  editorDate.value = date
  editorScore.value = score
  editorError.value = null
  editorOpen.value = true
}

function closeEditor() {
  if (!editorSaving.value) editorOpen.value = false
}

async function onTodayScore(n: number | null) {
  if (n == null) return
  try {
    await saveMood(todayIso(), n)
  } catch {
    /* keep previous value via today computed */
  }
}

watch(
  () => route.query.date,
  (raw) => {
    const date = typeof raw === 'string' ? raw : ''
    if (parseIsoDate(date) && date <= todayIso()) {
      openEditor(date, byDate.value[date]?.score ?? null)
      void router.replace({ path: '/humeur', query: {} })
    }
  },
  { immediate: true },
)

async function submitEditor() {
  if (editorScore.value == null || editorSaving.value) return
  editorSaving.value = true
  editorError.value = null
  try {
    await saveMood(editorDate.value, editorScore.value)
    editorOpen.value = false
  } catch (e) {
    editorError.value = e instanceof Error ? e.message : 'Enregistrement impossible'
  } finally {
    editorSaving.value = false
  }
}

const chartData = computed(() => ({
  datasets: [
    {
      label: 'Humeur',
      data: filtered.value.map((e) => ({ x: e.dateObj.getTime(), y: e.score })),
      borderColor: chartColors.primary,
      backgroundColor: chartColors.primaryFill,
      pointBackgroundColor: filtered.value.map((e) => moodColor(e.score)),
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
      pointRadius: 4,
      pointHoverRadius: 6,
      borderWidth: 2.5,
      tension: 0.25,
      fill: true,
    },
  ],
}))

const chartOptions = computed((): ChartOptions<'line'> => {
  const base = baseChartOptions()
  return {
    ...base,
    plugins: {
      ...base.plugins,
      tooltip: {
        ...base.plugins.tooltip,
        callbacks: {
          title: (items: TooltipItem<'line'>[]) =>
            formatFrDate(new Date(items[0]?.parsed.x ?? 0)),
          label: (ctx: TooltipItem<'line'>) => {
            const y = ctx.parsed.y
            if (y == null) return ''
            return `${y} / 10  ·  ${moodLabel(y)}`
          },
        },
      },
    },
    scales: {
      ...base.scales,
      x: {
        ...base.scales.x,
        adapters: { date: { locale: fr } },
        time: {
          tooltipFormat: 'dd MMM yyyy',
          displayFormats: {
            month: 'MMM yy',
            year: 'yyyy',
          },
        },
      },
      y: {
        ...base.scales.y,
        min: 0,
        max: 10,
        ticks: {
          ...base.scales.y.ticks,
          stepSize: 1,
        },
        title: {
          display: true,
          text: '0–10',
          color: chartColors.muted,
          font: { size: 11 },
        },
      },
    },
  }
})
</script>

<template>
  <PageShell title="Humeur" max-width="lg">
    <template #description>
      <p class="mt-0.5 text-sm text-[var(--muted-foreground)]">
        {{ filtered.length }} jour{{ filtered.length > 1 ? 's' : '' }} noté{{ filtered.length > 1 ? 's' : '' }}
        <template v-if="moyenne7j != null"> · moyenne 7 j {{ moyenne7j }}/10</template>
      </p>
    </template>

    <div class="space-y-6">
      <div v-if="error" class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {{ error }}
      </div>
      <div v-else-if="loading && !entries.length" class="py-16 text-center text-sm text-[var(--muted-foreground)]">
        Chargement…
      </div>

      <template v-else>
        <section class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 sm:p-5">
          <div class="mb-3 flex items-center justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-[var(--foreground)]">Aujourd’hui</p>
              <p class="text-xs capitalize text-[var(--muted-foreground)]">{{ formatMoodDate(todayIso()) }}</p>
            </div>
            <OwlEmotionIcon
              :emotion="moodOwl(today?.score ?? 5)"
              :active="today != null"
              :size="44"
            />
          </div>
          <MoodScale
            :score="today?.score ?? null"
            @update:score="onTodayScore"
          />
        </section>

        <section
          v-if="missingDays.length > 1"
          class="rounded-2xl border border-[var(--primary)]/20 bg-[var(--card)] p-4"
        >
          <p class="text-sm font-semibold text-[var(--foreground)]">
            {{ missingDays.length }} jour{{ missingDays.length > 1 ? 's' : '' }} sans note
          </p>
          <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">
            Tu peux rattraper un oubli ou corriger une note.
          </p>
          <div class="mt-3 flex flex-wrap gap-1.5">
            <button
              v-for="day in missingDays.slice(0, 8)"
              :key="day"
              type="button"
              class="rounded-lg border border-[var(--border)] px-2.5 py-1.5 text-xs font-medium text-[var(--foreground)] hover:bg-[var(--accent)]/50"
              @click="openEditor(day)"
            >
              {{ day === todayIso() ? 'Aujourd’hui' : day.slice(8) }}/{{ day.slice(5, 7) }}
            </button>
          </div>
        </section>

        <div
          class="-mx-4 overflow-hidden border-y border-[var(--border)] bg-[var(--card)] sm:-mx-6 md:mx-0 md:rounded-2xl md:border"
        >
          <div class="flex flex-col gap-3 border-b border-[var(--border)] px-4 py-3 sm:px-5">
            <DateRangeFilter
              :preset="preset"
              :custom-from="customFrom"
              :custom-to="customTo"
              @update:preset="preset = $event"
              @update:custom-from="customFrom = $event"
              @update:custom-to="customTo = $event"
              @select="setPreset"
            />
            <button
              type="button"
              class="inline-flex items-center gap-1.5 self-start rounded-lg border border-[var(--primary)]/30 bg-[var(--primary)]/8 px-3 py-2 text-sm font-medium text-[var(--primary)] transition hover:bg-[var(--primary)]/15"
              @click="openEditor()"
            >
              <Plus :size="15" />
              Ajouter / modifier
            </button>
          </div>
          <div class="px-1 py-3 sm:px-5 sm:py-5">
            <h2 class="mb-3 px-3 text-sm font-semibold text-[var(--foreground)] sm:px-0">Courbe d’humeur</h2>
            <div v-if="filtered.length" class="h-56 w-full sm:h-80">
              <Line :data="chartData" :options="chartOptions" />
            </div>
            <p v-else class="py-16 text-center text-sm text-[var(--muted-foreground)]">
              Aucune note sur cette période
            </p>
          </div>
        </div>

        <div class="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)]">
          <div class="border-b border-[var(--border)] px-5 py-3">
            <h2 class="text-sm font-semibold">Historique</h2>
          </div>
          <div class="divide-y divide-[var(--border)]">
            <button
              v-for="e in tableRows"
              :key="e.date"
              type="button"
              class="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-[var(--accent)]/40"
              @click="openEditor(e.date, e.score)"
            >
              <OwlEmotionIcon :emotion="moodOwl(e.score)" active :size="36" />
              <div class="min-w-0 flex-1">
                <p class="text-sm font-medium capitalize text-[var(--foreground)]">
                  {{ formatMoodDate(e.date) }}
                </p>
                <p class="text-xs" :style="{ color: moodColor(e.score) }">
                  {{ e.score }}/10 · {{ moodLabel(e.score) }}
                </p>
              </div>
            </button>
            <p
              v-if="!tableRows.length"
              class="px-4 py-8 text-center text-sm text-[var(--muted-foreground)]"
            >
              Pas encore de note. Commence par aujourd’hui, ou rattrape un jour passé.
            </p>
          </div>
        </div>
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
              {{ editorExisting ? 'Modifier une humeur' : 'Noter une humeur' }}
            </h2>
            <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">
              0 au plus bas · 10 super bien
            </p>
          </div>
          <button
            type="button"
            class="rounded-lg p-1.5 text-[var(--muted-foreground)] transition hover:bg-[var(--muted)]"
            @click="closeEditor"
          >
            <X :size="16" />
          </button>
        </div>
        <div class="space-y-4 px-5 py-5">
          <div>
            <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Date</label>
            <input
              v-model="editorDate"
              type="date"
              :max="todayIso()"
              class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
            />
          </div>
          <MoodScale v-model:score="editorScore" :disabled="editorSaving" />
          <p v-if="editorError" class="text-xs text-red-600">{{ editorError }}</p>
        </div>
        <div class="flex justify-end gap-2 border-t border-[var(--border)] px-5 py-4">
          <button
            type="button"
            class="rounded-lg px-3 py-2 text-sm text-[var(--muted-foreground)] hover:bg-[var(--muted)]"
            :disabled="editorSaving"
            @click="closeEditor"
          >
            Annuler
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-2 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] disabled:opacity-50"
            :disabled="editorScore == null || editorSaving"
            @click="submitEditor"
          >
            <Loader v-if="editorSaving" :size="14" class="animate-spin" />
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
