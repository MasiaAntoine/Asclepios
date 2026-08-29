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
import annotationPlugin from 'chartjs-plugin-annotation'
import { Line } from 'vue-chartjs'
import type { ChartOptions, TooltipItem } from 'chart.js'
import 'chartjs-adapter-date-fns'
import { fr } from 'date-fns/locale'
import { useLabs } from '@/composables/useLabs'
import { useMedicationSeries } from '@/composables/useMedicationSeries'
import { useDateRange } from '@/composables/useDateRange'
import DateRangeFilter from '@/components/DateRangeFilter.vue'
import { baseChartOptions, chartColors, formatFrDate } from '@/lib/chartTheme'
import { Activity, AlertTriangle, FlaskConical, Pill, TrendingDown, TrendingUp } from '@lucide/vue'
import PdfButton from '@/components/PdfButton.vue'
import AddSuiviEntryDialog from '@/components/AddSuiviEntryDialog.vue'

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
  annotationPlugin,
)

// ── Tabs ──────────────────────────────────────────────────────────────────────

type Tab = 'labs' | 'rx'

const route = useRoute()
const router = useRouter()

const activeTab = ref<Tab>((route.query.tab as Tab) === 'rx' ? 'rx' : 'labs')

watch(activeTab, (tab) => {
  void router.replace({ query: { ...route.query, tab } })
})

// ── Composables ───────────────────────────────────────────────────────────────

const {
  config: labsConfig,
  primary,
  secondary,
  doses: labsDoses,
  linkedTreatment,
  loading: labsLoading,
  error: labsError,
  reload: reloadLabs,
} = useLabs()

const {
  config: medConfig,
  treatment,
  doses: medDoses,
  currentDose,
  isActive,
  loading: medLoading,
  error: medError,
  reload: reloadMed,
} = useMedicationSeries()

async function onLabsEntryAdded() {
  await reloadLabs()
}

async function onRxEntryAdded() {
  await reloadMed()
}

// ── Shared event labels ───────────────────────────────────────────────────────

const eventLabels: Record<string, string> = {
  debut: 'Début',
  maintien: 'Maintien',
  diminution: 'Diminution',
  augmentation: 'Augmentation',
  arret: 'Arrêt',
  reprise: 'Reprise',
}

function eventClass(e: string) {
  if (e === 'arret') return 'bg-red-50 text-red-700'
  if (e === 'augmentation' || e === 'reprise') return 'bg-amber-50 text-amber-800'
  if (e === 'diminution') return 'bg-sky-50 text-sky-800'
  return 'bg-[var(--secondary)] text-[var(--secondary-foreground)]'
}

// ── LABS tab logic ─────────────────────────────────────────────────────────────

const markerLabel = computed(
  () =>
    `${labsConfig.value.primaryAnalyte || 'Marqueur'}${labsConfig.value.markerUnit ? ` (${labsConfig.value.markerUnit})` : ''}`,
)
const doseLabel = computed(() => {
  const name = linkedTreatment.value?.nom ?? 'Traitement'
  return labsConfig.value.doseUnit ? `${name} (${labsConfig.value.doseUnit})` : name
})

const labsLastDate = computed(() => {
  const dates = [
    ...primary.value.map((p) => p.dateObj.getTime()),
    ...labsDoses.value.map((d) => d.dateObj.getTime()),
  ]
  return dates.length ? new Date(Math.max(...dates)) : null
})

const {
  preset: labsPreset,
  customFrom: labsFrom,
  customTo: labsTo,
  bounds: labsBounds,
  inRange: labsInRange,
  setPreset: labsSetPreset,
} = useDateRange(labsLastDate)

const filteredPrimary = computed(() => primary.value.filter((p) => labsInRange(p.dateObj)))
const filteredSecondary = computed(() => secondary.value.filter((p) => labsInRange(p.dateObj)))
const filteredLabsDoses = computed(() => labsDoses.value.filter((d) => labsInRange(d.dateObj)))

const latestInRange = computed(() =>
  filteredPrimary.value.length ? filteredPrimary.value[filteredPrimary.value.length - 1] : null,
)
const labsDoseInRange = computed(() => {
  const { to } = labsBounds.value
  const end = to ?? new Date()
  const relevant = labsDoses.value.filter((d) => d.dateObj.getTime() <= end.getTime())
  return relevant.length ? relevant[relevant.length - 1] : null
})
const outOfRangeCount = computed(() => filteredPrimary.value.filter((p) => p.out_of_range).length)

const labsDosePoints = computed(() => {
  if (!labsDoses.value.length) return []
  const { from, to } = labsBounds.value
  const full: { x: number; y: number }[] = []
  for (const d of labsDoses.value) {
    if (full.length) full.push({ x: d.dateObj.getTime(), y: full[full.length - 1].y })
    full.push({ x: d.dateObj.getTime(), y: d.dose_ug })
  }
  const lastPrimary = primary.value[primary.value.length - 1]
  const lastDose = labsDoses.value[labsDoses.value.length - 1]
  if (lastPrimary && lastDose && lastPrimary.dateObj > lastDose.dateObj) {
    full.push({ x: lastPrimary.dateObj.getTime(), y: lastDose.dose_ug })
  }
  if (!from && !to) return full
  const fromT = from?.getTime() ?? -Infinity
  const toT = to?.getTime() ?? Infinity
  let yAtStart: number | null = null
  for (const p of full) if (p.x <= fromT) yAtStart = p.y
  const clipped = full.filter((p) => p.x >= fromT && p.x <= toT)
  if (yAtStart !== null && from && (clipped.length === 0 || clipped[0].x > fromT)) {
    clipped.unshift({ x: fromT, y: yAtStart })
  }
  return clipped
})

const labsChartData = computed(() => ({
  datasets: [
    {
      label: markerLabel.value,
      data: filteredPrimary.value.map((p) => ({ x: p.dateObj.getTime(), y: p.value })),
      borderColor: chartColors.marker,
      backgroundColor: chartColors.markerSoft,
      pointBackgroundColor: filteredPrimary.value.map((p) =>
        p.out_of_range ? chartColors.danger : chartColors.marker,
      ),
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
      pointRadius: 5,
      pointHoverRadius: 7,
      borderWidth: 2.5,
      tension: 0.2,
      yAxisID: 'y',
      order: 1,
    },
    {
      label: doseLabel.value,
      data: labsDosePoints.value,
      borderColor: chartColors.dose,
      backgroundColor: 'transparent',
      pointRadius: 0,
      pointHoverRadius: 4,
      borderWidth: 2,
      borderDash: [6, 4],
      yAxisID: 'y1',
      order: 2,
    },
  ],
}))

const labsChartOptions = computed((): ChartOptions<'line'> => {
  const base = baseChartOptions()
  const refLow = labsConfig.value.refLow
  const refHigh = labsConfig.value.refHigh
  const hasRef = refLow > 0 || refHigh > 0
  return {
    ...base,
    plugins: {
      ...base.plugins,
      annotation: hasRef
        ? {
            annotations: {
              refBand: {
                type: 'box',
                yMin: refLow,
                yMax: refHigh,
                yScaleID: 'y',
                backgroundColor: chartColors.primaryFill,
                borderWidth: 0,
                label: {
                  display: true,
                  content: `Réf. ≈ ${refLow}–${refHigh}`,
                  position: 'start',
                  color: chartColors.muted,
                  font: { size: 10 },
                },
              },
            },
          }
        : undefined,
      tooltip: {
        ...base.plugins.tooltip,
        callbacks: {
          title: (items: TooltipItem<'line'>[]) =>
            formatFrDate(new Date(items[0]?.parsed.x ?? 0)),
          label: (ctx: TooltipItem<'line'>) => {
            const y = ctx.parsed.y
            if (y == null) return ''
            if (ctx.dataset.yAxisID === 'y1')
              return `Dose : ${y}${labsConfig.value.doseUnit ? ` ${labsConfig.value.doseUnit}` : ''}`
            return `${labsConfig.value.primaryAnalyte || 'Valeur'} : ${y}${labsConfig.value.markerUnit ? ` ${labsConfig.value.markerUnit}` : ''}`
          },
        },
      },
    },
    scales: {
      x: {
        ...base.scales.x,
        adapters: { date: { locale: fr } },
        time: { tooltipFormat: 'dd MMM yyyy', displayFormats: { month: 'MMM yy', year: 'yyyy' } },
        min: labsBounds.value.from?.getTime(),
        max: labsBounds.value.to?.getTime(),
      },
      y: {
        ...base.scales.y,
        position: 'left',
        title: { display: true, text: markerLabel.value, color: chartColors.marker, font: { size: 11 } },
        ticks: { ...base.scales.y.ticks, color: chartColors.marker },
      },
      y1: {
        position: 'right',
        grid: { drawOnChartArea: false },
        border: { display: false },
        title: { display: true, text: doseLabel.value, color: chartColors.dose, font: { size: 11 } },
        ticks: { color: chartColors.dose, font: { size: 11 } },
        min: 0,
        suggestedMax: Math.max(60, ...labsDoses.value.map((d) => d.dose_ug), 50),
      },
    },
  }
})

// ── RX tab logic ──────────────────────────────────────────────────────────────

const seriesLabel = computed(() => {
  const unit = medConfig.value.doseUnit
  return unit ? `Dose (${unit})` : 'Dose'
})

const medLastDate = computed(() =>
  medDoses.value.length ? medDoses.value[medDoses.value.length - 1].dateObj : null,
)

const {
  preset: medPreset,
  customFrom: medFrom,
  customTo: medTo,
  bounds: medBounds,
  inRange: medInRange,
  setPreset: medSetPreset,
} = useDateRange(medLastDate)

const filteredMedDoses = computed(() => medDoses.value.filter((d) => medInRange(d.dateObj)))

const medDoseInRange = computed(() => {
  const { to } = medBounds.value
  const end = to ?? new Date()
  const relevant = medDoses.value.filter((d) => d.dateObj.getTime() <= end.getTime())
  return relevant.length ? relevant[relevant.length - 1] : null
})

const maxDose = computed(() =>
  filteredMedDoses.value.length ? Math.max(...filteredMedDoses.value.map((d) => d.doseValue)) : 0,
)
const minDose = computed(() =>
  filteredMedDoses.value.length ? Math.min(...filteredMedDoses.value.map((d) => d.doseValue)) : 0,
)

const medDosePoints = computed(() => {
  if (!medDoses.value.length) return []
  const { from, to } = medBounds.value
  const full: { x: number; y: number }[] = []
  for (const d of medDoses.value) {
    if (full.length) full.push({ x: d.dateObj.getTime(), y: full[full.length - 1].y })
    full.push({ x: d.dateObj.getTime(), y: d.doseValue })
  }
  if (!from && !to) return full
  const fromT = from?.getTime() ?? -Infinity
  const toT = to?.getTime() ?? Infinity
  let yAtStart: number | null = null
  for (const p of full) if (p.x <= fromT) yAtStart = p.y
  const clipped = full.filter((p) => p.x >= fromT && p.x <= toT)
  if (yAtStart !== null && from && (clipped.length === 0 || clipped[0].x > fromT)) {
    clipped.unshift({ x: fromT, y: yAtStart })
  }
  if (to && clipped.length) {
    const last = clipped[clipped.length - 1]
    if (last.x < toT) clipped.push({ x: toT, y: last.y })
  }
  return clipped
})

const medChartData = computed(() => ({
  datasets: [
    {
      label: seriesLabel.value,
      data: medDosePoints.value,
      borderColor: chartColors.primary,
      backgroundColor: chartColors.primaryFill,
      pointBackgroundColor: chartColors.primary,
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
      pointRadius: 4,
      pointHoverRadius: 6,
      borderWidth: 2.5,
      fill: true,
      tension: 0,
    },
  ],
}))

const medChartOptions = computed((): ChartOptions<'line'> => {
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
            const unit = medConfig.value.doseUnit
            return unit ? `Dose : ${y} ${unit}` : `Dose : ${y}`
          },
        },
      },
    },
    scales: {
      x: {
        ...base.scales.x,
        adapters: { date: { locale: fr } },
        time: { tooltipFormat: 'dd MMM yyyy', displayFormats: { month: 'MMM yy', year: 'yyyy' } },
        min: medBounds.value.from?.getTime(),
        max: medBounds.value.to?.getTime(),
      },
      y: {
        ...base.scales.y,
        title: { display: true, text: seriesLabel.value, color: chartColors.primary, font: { size: 11 } },
        min: 0,
        suggestedMax: Math.max(maxDose.value + 2, 10),
      },
    },
  }
})
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <!-- ── Header ──────────────────────────────────────────────────────────── -->
    <div class="border-b border-[var(--border)] bg-[var(--card)] px-8 py-5">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <!-- Tabs -->
        <div class="flex items-center gap-1 rounded-xl bg-[var(--muted)] p-1">
          <button
            v-for="tab in ([{ id: 'labs', label: labsConfig.title }, { id: 'rx', label: medConfig.title }] as const)"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'rounded-lg px-5 py-2 text-sm font-medium transition-all',
              activeTab === tab.id
                ? 'bg-[var(--card)] text-[var(--foreground)] shadow-sm'
                : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]',
            ]"
          >
            {{ tab.label }}
          </button>
        </div>

        <!-- Actions -->
        <div class="flex flex-wrap items-center gap-2">
          <PdfButton
            v-if="activeTab === 'labs'"
            generate-endpoint="/pdf/generate/labs"
            label="Compte-rendu PDF"
          />
          <PdfButton
            v-else
            generate-endpoint="/pdf/generate/traitements"
            label="Compte-rendu PDF"
          />
          <AddSuiviEntryDialog
            v-if="activeTab === 'labs'"
            type="labs"
            :csv="labsConfig.csv"
            :primary-analyte="labsConfig.primaryAnalyte"
            :marker-unit="labsConfig.markerUnit"
            :ref-low="labsConfig.refLow"
            :ref-high="labsConfig.refHigh"
            :titre="labsConfig.title"
            @added="onLabsEntryAdded"
          />
          <AddSuiviEntryDialog
            v-else-if="activeTab === 'rx'"
            type="rx"
            :treatment-name-includes="medConfig.treatmentNameIncludes"
            :dose-unit="medConfig.doseUnit"
            :titre="medConfig.title"
            @added="onRxEntryAdded"
          />
        </div>
      </div><!-- end flex justify-between -->
    </div><!-- end header -->

    <!-- ── Content ────────────────────────────────────────────────────────── -->
    <div class="flex-1 overflow-y-auto px-8 py-8">
      <div class="mx-auto max-w-5xl space-y-6">

        <!-- ════ LABS tab ════ -->
        <template v-if="activeTab === 'labs'">
          <div v-if="labsError" class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {{ labsError }}
          </div>
          <div v-else-if="labsLoading && !primary.length" class="py-16 text-center text-sm text-[var(--muted-foreground)]">
            Chargement…
          </div>

          <template v-else>
            <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3">
              <DateRangeFilter
                :preset="labsPreset"
                :custom-from="labsFrom"
                :custom-to="labsTo"
                @update:preset="labsPreset = $event"
                @update:custom-from="labsFrom = $event"
                @update:custom-to="labsTo = $event"
                @select="labsSetPreset"
              />
            </div>

            <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
                <div class="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)]">
                  <FlaskConical :size="16" class="text-[var(--primary)]" />
                </div>
                <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Dernier marqueur</p>
                <p class="mt-1 text-xl font-bold" :class="latestInRange?.out_of_range ? 'text-red-600' : ''">
                  {{ latestInRange ? `${latestInRange.value} ${latestInRange.unit}` : '—' }}
                </p>
                <p class="text-xs text-[var(--muted-foreground)]">
                  {{ latestInRange?.date }}
                  <template v-if="latestInRange"> · {{ latestInRange.lab }}</template>
                </p>
              </div>

              <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
                <div class="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)]">
                  <Pill :size="16" class="text-[var(--primary)]" />
                </div>
                <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Dose actuelle</p>
                <p class="mt-1 text-xl font-bold">{{ labsDoseInRange ? labsDoseInRange.doseLabel : '—' }}</p>
                <p class="text-xs text-[var(--muted-foreground)]">
                  <template v-if="labsDoseInRange">
                    {{ eventLabels[labsDoseInRange.evenement] ?? labsDoseInRange.evenement }} · {{ labsDoseInRange.date }}
                  </template>
                  <template v-else>Aucun historique</template>
                </p>
              </div>

              <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
                <div class="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)]">
                  <AlertTriangle :size="16" class="text-[var(--primary)]" />
                </div>
                <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Hors norme</p>
                <p class="mt-1 text-xl font-bold">{{ outOfRangeCount }} / {{ filteredPrimary.length }}</p>
                <p class="text-xs text-[var(--muted-foreground)]">dosages hors références labo</p>
              </div>
            </div>

            <div class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5">
              <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
                <h2 class="text-sm font-semibold text-[var(--foreground)]">Évolution</h2>
                <p class="text-xs text-[var(--muted-foreground)]">Bande de référence · points rouges = hors norme labo</p>
              </div>
              <div v-if="filteredPrimary.length || labsDosePoints.length" class="h-96 w-full">
                <Line :data="labsChartData" :options="labsChartOptions" />
              </div>
              <p v-else class="py-16 text-center text-sm text-[var(--muted-foreground)]">Aucune donnée sur cette période</p>
            </div>

            <div v-if="linkedTreatment" class="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)]">
              <div class="border-b border-[var(--border)] px-5 py-3">
                <h2 class="flex items-center gap-2 text-sm font-semibold">
                  <Pill :size="14" class="text-[var(--primary)]" /> Historique du traitement
                </h2>
              </div>
              <div class="overflow-x-auto">
                <table class="w-full text-sm">
                  <thead class="bg-[var(--secondary)] text-left text-xs uppercase tracking-wider text-[var(--muted-foreground)]">
                    <tr>
                      <th class="px-5 py-3 font-medium">Date</th>
                      <th class="px-5 py-3 font-medium">Dose</th>
                      <th class="px-5 py-3 font-medium">Événement</th>
                      <th class="px-5 py-3 font-medium">Posologie</th>
                      <th class="px-5 py-3 font-medium">Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="d in [...filteredLabsDoses].reverse()"
                      :key="d.date + d.doseLabel"
                      class="border-t border-[var(--border)]"
                    >
                      <td class="px-5 py-2.5">{{ d.date }}</td>
                      <td class="px-5 py-2.5 font-medium">{{ d.doseLabel }}</td>
                      <td class="px-5 py-2.5 capitalize">{{ eventLabels[d.evenement] ?? d.evenement }}</td>
                      <td class="px-5 py-2.5 text-[var(--muted-foreground)]">
                        {{ linkedTreatment.historique.find((h) => h.date === d.date)?.posologie }}
                      </td>
                      <td class="px-5 py-2.5 italic text-[var(--muted-foreground)]">{{ d.note || '—' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div class="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)]">
              <div class="border-b border-[var(--border)] px-5 py-3">
                <h2 class="flex items-center gap-2 text-sm font-semibold">
                  <Activity :size="14" class="text-[var(--primary)]" /> Dosages
                </h2>
              </div>
              <div class="overflow-x-auto">
                <table class="w-full text-sm">
                  <thead class="bg-[var(--secondary)] text-left text-xs uppercase tracking-wider text-[var(--muted-foreground)]">
                    <tr>
                      <th class="px-5 py-3 font-medium">Date</th>
                      <th class="px-5 py-3 font-medium">Valeur</th>
                      <th class="px-5 py-3 font-medium">Réf. labo</th>
                      <th class="px-5 py-3 font-medium">Statut</th>
                      <th class="px-5 py-3 font-medium">Labo</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="p in [...filteredPrimary].reverse()"
                      :key="p.date + p.value"
                      class="border-t border-[var(--border)]"
                    >
                      <td class="px-5 py-2.5">{{ p.date }}</td>
                      <td class="px-5 py-2.5 font-medium">{{ p.value }} {{ p.unit }}</td>
                      <td class="px-5 py-2.5 text-[var(--muted-foreground)]">{{ p.ref_low ?? '—' }} – {{ p.ref_high ?? '—' }}</td>
                      <td class="px-5 py-2.5">
                        <span v-if="p.out_of_range" class="rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-700">Hors norme</span>
                        <span v-else class="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-800">OK</span>
                      </td>
                      <td class="px-5 py-2.5 text-[var(--muted-foreground)]">{{ p.lab }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div v-if="filteredSecondary.length" class="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)]">
              <div class="border-b border-[var(--border)] px-5 py-3">
                <h2 class="text-sm font-semibold">Autres analytes</h2>
              </div>
              <div class="overflow-x-auto">
                <table class="w-full text-sm">
                  <thead class="bg-[var(--secondary)] text-left text-xs uppercase tracking-wider text-[var(--muted-foreground)]">
                    <tr>
                      <th class="px-5 py-3 font-medium">Date</th>
                      <th class="px-5 py-3 font-medium">Analyte</th>
                      <th class="px-5 py-3 font-medium">Valeur</th>
                      <th class="px-5 py-3 font-medium">Réf.</th>
                      <th class="px-5 py-3 font-medium">Statut</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="(p, i) in [...filteredSecondary].reverse()"
                      :key="p.date + p.analyte + i"
                      class="border-t border-[var(--border)]"
                    >
                      <td class="px-5 py-2.5">{{ p.date }}</td>
                      <td class="px-5 py-2.5 font-medium">{{ p.analyte }}</td>
                      <td class="px-5 py-2.5">{{ p.value }} {{ p.unit }}</td>
                      <td class="px-5 py-2.5 text-[var(--muted-foreground)]">{{ p.ref_low ?? '—' }} – {{ p.ref_high ?? '—' }}</td>
                      <td class="px-5 py-2.5">
                        <span v-if="p.out_of_range" class="rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-700">Hors norme</span>
                        <span v-else class="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-800">OK</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </template>
        </template>

        <!-- ════ RX tab ════ -->
        <template v-else>
          <div v-if="medError" class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {{ medError }}
          </div>
          <div v-else-if="medLoading && !medDoses.length" class="py-16 text-center text-sm text-[var(--muted-foreground)]">
            Chargement…
          </div>

          <template v-else>
            <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3">
              <DateRangeFilter
                :preset="medPreset"
                :custom-from="medFrom"
                :custom-to="medTo"
                @update:preset="medPreset = $event"
                @update:custom-from="medFrom = $event"
                @update:custom-to="medTo = $event"
                @select="medSetPreset"
              />
            </div>

            <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
                <div class="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)]">
                  <Pill :size="16" class="text-[var(--primary)]" />
                </div>
                <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Dose actuelle</p>
                <p class="mt-1 text-xl font-bold">{{ medDoseInRange ? medDoseInRange.doseLabel : '—' }}</p>
                <p class="text-xs text-[var(--muted-foreground)]">
                  <template v-if="medDoseInRange">
                    {{ eventLabels[medDoseInRange.evenement] ?? medDoseInRange.evenement }} · {{ medDoseInRange.date }}
                  </template>
                  <template v-else-if="treatment">Aucun historique sur la période</template>
                  <template v-else>Traitement introuvable</template>
                </p>
              </div>

              <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
                <div class="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)]">
                  <Activity :size="16" class="text-[var(--primary)]" />
                </div>
                <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Statut</p>
                <p class="mt-1 text-xl font-bold">
                  <span v-if="isActive" class="rounded-full bg-emerald-50 px-2.5 py-0.5 text-sm font-semibold text-emerald-800">En cours</span>
                  <span v-else class="rounded-full bg-red-50 px-2.5 py-0.5 text-sm font-semibold text-red-700">Arrêté</span>
                </p>
                <p class="mt-2 text-xs capitalize text-[var(--muted-foreground)]">
                  {{ treatment?.moment ?? '—' }}
                  <template v-if="treatment?.si_besoin"> · si besoin</template>
                </p>
              </div>

              <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
                <div class="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)]">
                  <component
                    :is="(medDoseInRange?.doseValue ?? 0) <= (currentDose?.doseValue ?? 0) ? TrendingDown : TrendingUp"
                    :size="16"
                    class="text-[var(--primary)]"
                  />
                </div>
                <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Sur la période</p>
                <p class="mt-1 text-xl font-bold">
                  {{ filteredMedDoses.length }} événement{{ filteredMedDoses.length > 1 ? 's' : '' }}
                </p>
                <p class="text-xs text-[var(--muted-foreground)]">
                  Min {{ minDose }}{{ medConfig.doseUnit ? ` ${medConfig.doseUnit}` : '' }}
                  · Max {{ maxDose }}{{ medConfig.doseUnit ? ` ${medConfig.doseUnit}` : '' }}
                </p>
              </div>
            </div>

            <div class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5">
              <h2 class="mb-4 text-sm font-semibold text-[var(--foreground)]">Courbe de dose</h2>
              <div v-if="medDosePoints.length" class="h-80 w-full">
                <Line :data="medChartData" :options="medChartOptions" />
              </div>
              <p v-else class="py-16 text-center text-sm text-[var(--muted-foreground)]">Aucune donnée sur cette période</p>
            </div>

            <div class="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)]">
              <div class="border-b border-[var(--border)] px-5 py-3">
                <h2 class="flex items-center gap-2 text-sm font-semibold">
                  <Pill :size="14" class="text-[var(--primary)]" /> Historique
                </h2>
              </div>
              <div class="overflow-x-auto">
                <table class="w-full text-sm">
                  <thead class="bg-[var(--secondary)] text-left text-xs uppercase tracking-wider text-[var(--muted-foreground)]">
                    <tr>
                      <th class="px-5 py-3 font-medium">Date</th>
                      <th class="px-5 py-3 font-medium">Dose</th>
                      <th class="px-5 py-3 font-medium">Événement</th>
                      <th class="px-5 py-3 font-medium">Posologie</th>
                      <th class="px-5 py-3 font-medium">Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="d in [...filteredMedDoses].reverse()"
                      :key="d.date + d.doseLabel + d.evenement"
                      class="border-t border-[var(--border)]"
                    >
                      <td class="px-5 py-2.5">{{ d.date }}</td>
                      <td class="px-5 py-2.5 font-medium">{{ d.doseLabel }}</td>
                      <td class="px-5 py-2.5">
                        <span :class="['rounded-full px-2 py-0.5 text-[10px] font-medium', eventClass(d.evenement)]">
                          {{ eventLabels[d.evenement] ?? d.evenement }}
                        </span>
                      </td>
                      <td class="px-5 py-2.5 text-[var(--muted-foreground)]">{{ d.posologie }}</td>
                      <td class="px-5 py-2.5 italic text-[var(--muted-foreground)]">{{ d.note || '—' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </template>
        </template>

      </div>
    </div>
  </div>
</template>
