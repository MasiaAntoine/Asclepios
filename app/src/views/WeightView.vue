<script setup lang="ts">
import { computed } from 'vue'
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
import { usePoids } from '@/composables/usePoids'
import { useDateRange } from '@/composables/useDateRange'
import DateRangeFilter from '@/components/DateRangeFilter.vue'
import { baseChartOptions, chartColors, formatFrDate } from '@/lib/chartTheme'
import { Scale, TrendingDown, TrendingUp, Ruler, Activity } from '@lucide/vue'
import PdfButton from '@/components/PdfButton.vue'
import AddWeightDialog from '@/components/AddWeightDialog.vue'

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

const { entries, tailleCm, loading, error, reload } = usePoids()

async function onWeightAdded() {
  await reload()
}

const lastDate = computed(() =>
  entries.value.length ? entries.value[entries.value.length - 1].dateObj : null,
)
const { preset, customFrom, customTo, inRange, setPreset } = useDateRange(lastDate)

const filtered = computed(() => entries.value.filter((e) => inRange(e.dateObj)))

const premier = computed(() => filtered.value[0] ?? null)
const dernier = computed(() =>
  filtered.value.length ? filtered.value[filtered.value.length - 1] : null,
)
const min = computed(() =>
  filtered.value.length
    ? filtered.value.reduce((a, b) => (a.poids_kg < b.poids_kg ? a : b))
    : null,
)
const max = computed(() =>
  filtered.value.length
    ? filtered.value.reduce((a, b) => (a.poids_kg > b.poids_kg ? a : b))
    : null,
)
const delta = computed(() =>
  premier.value && dernier.value
    ? Number((dernier.value.poids_kg - premier.value.poids_kg).toFixed(2))
    : null,
)
const deltaRecent = computed(() => {
  const f = filtered.value
  if (f.length < 2) return null
  return Number((f[f.length - 1].poids_kg - f[f.length - 2].poids_kg).toFixed(2))
})

const tableRows = computed(() => {
  const reversed = [...filtered.value].reverse()
  return reversed.map((e, i) => {
    const older = reversed[i + 1]
    const d = older ? Number((e.poids_kg - older.poids_kg).toFixed(2)) : null
    return { ...e, delta: d }
  })
})

const chartData = computed(() => ({
  datasets: [
    {
      label: 'Poids (kg)',
      data: filtered.value.map((e) => ({ x: e.dateObj.getTime(), y: e.poids_kg })),
      borderColor: chartColors.primary,
      backgroundColor: chartColors.primaryFill,
      pointBackgroundColor: chartColors.primary,
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
            const imc = tailleCm.value
              ? (y / (tailleCm.value / 100) ** 2).toFixed(1)
              : null
            return imc ? `Poids : ${y} kg  ·  IMC ${imc}` : `Poids : ${y} kg`
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
        title: {
          display: true,
          text: 'kg',
          color: chartColors.muted,
          font: { size: 11 },
        },
        suggestedMin: min.value ? Math.floor(min.value.poids_kg - 2) : undefined,
        suggestedMax: max.value ? Math.ceil(max.value.poids_kg + 2) : undefined,
      },
    },
  }
})

function deltaClass(v: number | null) {
  if (v == null || v === 0) return 'text-[var(--muted-foreground)]'
  return v > 0 ? 'text-amber-700' : 'text-emerald-700'
}

function onSelectPreset(id: Parameters<typeof setPreset>[0]) {
  setPreset(id)
}
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <div class="border-b border-[var(--border)] bg-[var(--card)] px-8 py-6">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold text-[var(--foreground)]">Suivi du poids</h1>
          <p class="mt-0.5 text-sm text-[var(--muted-foreground)]">
            {{ filtered.length }} mesure{{ filtered.length > 1 ? 's' : '' }}
            <span v-if="filtered.length !== entries.length" class="opacity-70">
              / {{ entries.length }}
            </span>
            <template v-if="premier && dernier">
              · {{ premier.date }} → {{ dernier.date }}
            </template>
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <AddWeightDialog @added="onWeightAdded" />
          <PdfButton
            download-endpoint="/pdf/download/poids"
            label="Télécharger le PDF"
          />
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto px-8 py-8">
      <div class="mx-auto max-w-5xl space-y-6">
        <div v-if="error" class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {{ error }}
        </div>
        <div v-else-if="loading && !entries.length" class="py-16 text-center text-sm text-[var(--muted-foreground)]">
          Chargement…
        </div>

        <template v-else>
        <!-- Date range -->
        <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3">
          <DateRangeFilter
            :preset="preset"
            :custom-from="customFrom"
            :custom-to="customTo"
            @update:preset="preset = $event"
            @update:custom-from="customFrom = $event"
            @update:custom-to="customTo = $event"
            @select="onSelectPreset"
          />
        </div>

        <!-- Stats -->
        <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
            <div class="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)]">
              <Scale :size="16" class="text-[var(--primary)]" />
            </div>
            <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Dernier poids</p>
            <p class="mt-1 text-xl font-bold">{{ dernier ? `${dernier.poids_kg} kg` : '—' }}</p>
            <p class="text-xs text-[var(--muted-foreground)]">{{ dernier?.date }}</p>
          </div>

          <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
            <div class="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)]">
              <Ruler :size="16" class="text-[var(--primary)]" />
            </div>
            <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">IMC</p>
            <p class="mt-1 text-xl font-bold">{{ dernier?.imc?.toFixed(1) ?? '—' }}</p>
            <p class="text-xs text-[var(--muted-foreground)]">Taille {{ tailleCm }} cm</p>
          </div>

          <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
            <div class="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)]">
              <component :is="(deltaRecent ?? 0) <= 0 ? TrendingDown : TrendingUp" :size="16" class="text-[var(--primary)]" />
            </div>
            <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Dernière variation</p>
            <p class="mt-1 text-xl font-bold" :class="deltaClass(deltaRecent)">
              {{ deltaRecent == null ? '—' : `${deltaRecent > 0 ? '+' : ''}${deltaRecent} kg` }}
            </p>
            <p class="text-xs text-[var(--muted-foreground)]">vs mesure précédente</p>
          </div>

          <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
            <div class="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)]">
              <Activity :size="16" class="text-[var(--primary)]" />
            </div>
            <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Évolution totale</p>
            <p class="mt-1 text-xl font-bold" :class="deltaClass(delta)">
              {{ delta == null ? '—' : `${delta > 0 ? '+' : ''}${delta} kg` }}
            </p>
            <p class="text-xs text-[var(--muted-foreground)]">
              Min {{ min?.poids_kg ?? '—' }} · Max {{ max?.poids_kg ?? '—' }}
            </p>
          </div>
        </div>

        <!-- Chart -->
        <div class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5">
          <h2 class="mb-4 text-sm font-semibold text-[var(--foreground)]">Courbe de poids</h2>
          <div v-if="filtered.length" class="h-80 w-full">
            <Line :data="chartData" :options="chartOptions" />
          </div>
          <p v-else class="py-16 text-center text-sm text-[var(--muted-foreground)]">
            Aucune mesure sur cette période
          </p>
        </div>

        <!-- Table -->
        <div class="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)]">
          <div class="border-b border-[var(--border)] px-5 py-3">
            <h2 class="text-sm font-semibold">Historique des mesures</h2>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead class="bg-[var(--secondary)] text-left text-xs uppercase tracking-wider text-[var(--muted-foreground)]">
                <tr>
                  <th class="px-5 py-3 font-medium">Date</th>
                  <th class="px-5 py-3 font-medium">Poids</th>
                  <th class="px-5 py-3 font-medium">IMC</th>
                  <th class="px-5 py-3 font-medium">Δ</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="e in tableRows"
                  :key="e.date + e.poids_kg"
                  class="border-t border-[var(--border)]"
                >
                  <td class="px-5 py-2.5">{{ e.date }}</td>
                  <td class="px-5 py-2.5 font-medium">{{ e.poids_kg }} kg</td>
                  <td class="px-5 py-2.5 text-[var(--muted-foreground)]">
                    {{ e.imc?.toFixed(1) ?? '—' }}
                  </td>
                  <td class="px-5 py-2.5">
                    <span v-if="e.delta != null" :class="deltaClass(e.delta)">
                      {{ e.delta > 0 ? '+' : '' }}{{ e.delta }}
                    </span>
                    <span v-else class="text-[var(--muted-foreground)]">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        </template>
      </div>
    </div>
  </div>
</template>
