<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProfile } from '@/composables/useProfile'
import { useReports } from '@/composables/useReports'
import { usePoids } from '@/composables/usePoids'
import { useLabs } from '@/composables/useLabs'
import { useMedications } from '@/composables/useMedications'
import { useMedicationSeries } from '@/composables/useMedicationSeries'
import { formatOrdonnanceDate, useOrdonnances } from '@/composables/useOrdonnances'
import { formatLabDate, useLabPdfs } from '@/composables/useLabPdfs'
import PageShell from '@/components/PageShell.vue'
import {
  Activity,
  ArrowRight,
  BookOpen,
  Droplets,
  FileText,
  MessageSquare,
  Pill,
  Scale,
  ScrollText,
  Sparkles,
  TrendingDown,
  TrendingUp,
  UserRound,
} from '@lucide/vue'

const router = useRouter()

const {
  profil,
  age,
  imc,
  imcLabel,
  loading: profileLoading,
  error: profileError,
} = useProfile()

const { reports, loading: reportsLoading } = useReports()
const { dernier, delta, deltaRecent, loading: poidsLoading } = usePoids()
const {
  config: labsConfig,
  latestPrimary,
  loading: labsLoading,
} = useLabs()
const { actifs, loading: medsLoading } = useMedications()
const {
  config: rxConfig,
  treatment: rxTreatment,
  currentDose: rxDose,
  isActive: rxActive,
  loading: rxLoading,
} = useMedicationSeries()

const {
  items: ordonnances,
  loading: ordLoading,
  load: loadOrdonnances,
} = useOrdonnances()

const {
  items: labPdfs,
  loading: pdsLoading,
  load: loadLabPdfs,
} = useLabPdfs()

onMounted(() => {
  void loadOrdonnances()
  void loadLabPdfs()
})

const loading = computed(
  () =>
    (profileLoading.value && !profil.value) ||
    (reportsLoading.value && !reports.value.length) ||
    (poidsLoading.value && !dernier.value) ||
    labsLoading.value ||
    medsLoading.value ||
    rxLoading.value ||
    (ordLoading.value && !ordonnances.value.length) ||
    (pdsLoading.value && !labPdfs.value.length),
)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Bonjour'
  if (h < 18) return 'Bon après-midi'
  return 'Bonsoir'
})

const recentReports = computed(() => reports.value.slice(0, 3))
const recentOrdonnances = computed(() => ordonnances.value.slice(0, 3))
const recentLabs = computed(() => labPdfs.value.slice(0, 3))

function formatReportDate(dateStr: string) {
  if (!dateStr) return ''
  const [year, month, day] = dateStr.split('-')
  const months = [
    'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin',
    'Juil', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc',
  ]
  return `${parseInt(day)} ${months[parseInt(month) - 1]} ${year}`
}

function go(path: string) {
  void router.push(path)
}
</script>

<template>
  <PageShell title="Tableau de bord" max-width="xl">
    <template #description>
      <p class="mt-0.5 text-sm text-[var(--muted-foreground)]">
        <template v-if="profil">
          {{ greeting }}, {{ profil.prenom }}
          <template v-if="age !== null"> · {{ age }} ans</template>
        </template>
        <template v-else>Vue d’ensemble du suivi</template>
      </p>
      <p v-if="profileError" class="mt-1 text-xs text-red-600">{{ profileError }}</p>
    </template>

    <div v-if="loading && !profil" class="py-24 text-center text-sm text-[var(--muted-foreground)]">
      Chargement…
    </div>

    <div v-else class="space-y-8">
      <!-- Bannière Asclepios -->
      <div class="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[var(--primary)] to-[oklch(0.52_0.14_165)] p-6 text-white shadow-md">
        <div class="pointer-events-none absolute -right-8 -top-8 h-40 w-40 rounded-full bg-white/10" />
        <div class="pointer-events-none absolute -bottom-12 right-24 h-32 w-32 rounded-full bg-white/8" />
        <div class="relative z-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div class="max-w-md">
            <div class="flex items-center gap-2">
              <p class="text-xs font-semibold uppercase tracking-widest text-white/70">Asclepios</p>
              <span class="rounded-md bg-white/20 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-white">
                IA
              </span>
            </div>
            <h2 class="mt-1 text-2xl font-bold leading-tight">
              <template v-if="profil">{{ greeting }}, {{ profil.prenom }}</template>
              <template v-else>Ton allié santé</template>
            </h2>
            <p class="mt-2 text-sm text-white/80">
              Je connais ton dossier — pose-moi une question ou jette un œil à tes derniers docs.
            </p>
          </div>
          <button
            type="button"
            class="inline-flex shrink-0 items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-[var(--primary)] shadow-sm transition hover:bg-white/90"
            @click="go('/assistant')"
          >
            <MessageSquare :size="16" />
            Discuter
            <Sparkles :size="14" />
          </button>
        </div>
      </div>

      <!-- KPIs -->
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        <button
          type="button"
          class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 text-left transition hover:border-[var(--primary)]/40 hover:bg-[var(--accent)]/40"
          @click="go('/poids')"
        >
          <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Poids</p>
          <p class="mt-1 text-2xl font-bold tabular-nums">
            <template v-if="dernier">{{ dernier.poids_kg }}</template>
            <template v-else>—</template>
            <span class="text-sm font-medium text-[var(--muted-foreground)]"> kg</span>
          </p>
          <p
            v-if="deltaRecent != null"
            class="mt-1 flex items-center gap-1 text-xs"
            :class="deltaRecent > 0 ? 'text-amber-700' : deltaRecent < 0 ? 'text-emerald-700' : 'text-[var(--muted-foreground)]'"
          >
            <TrendingUp v-if="deltaRecent > 0" :size="12" />
            <TrendingDown v-else-if="deltaRecent < 0" :size="12" />
            {{ deltaRecent > 0 ? '+' : '' }}{{ deltaRecent }} kg
          </p>
        </button>

        <button
          type="button"
          class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 text-left transition hover:border-[var(--primary)]/40 hover:bg-[var(--accent)]/40"
          @click="go('/profil')"
        >
          <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">IMC</p>
          <p class="mt-1 text-2xl font-bold tabular-nums">
            <template v-if="imc != null">{{ imc.toFixed(1) }}</template>
            <template v-else>—</template>
          </p>
          <p v-if="imcLabel" class="mt-1 text-xs text-[var(--muted-foreground)]">{{ imcLabel }}</p>
        </button>

        <button
          type="button"
          class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 text-left transition hover:border-[var(--primary)]/40 hover:bg-[var(--accent)]/40"
          @click="go('/meds')"
        >
          <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Traitements</p>
          <p class="mt-1 text-2xl font-bold tabular-nums text-emerald-700">{{ actifs.length }}</p>
          <p class="mt-1 text-xs text-[var(--muted-foreground)]">en cours</p>
        </button>

        <button
          type="button"
          class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 text-left transition hover:border-[var(--primary)]/40 hover:bg-[var(--accent)]/40"
          @click="go('/rapports')"
        >
          <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Rapports</p>
          <p class="mt-1 text-2xl font-bold tabular-nums">{{ reports.length }}</p>
          <p class="mt-1 text-xs text-[var(--muted-foreground)]">au total</p>
        </button>

        <button
          type="button"
          class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 text-left transition hover:border-[var(--primary)]/40 hover:bg-[var(--accent)]/40"
          @click="go('/ordonnances')"
        >
          <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Ordonnances</p>
          <p class="mt-1 text-2xl font-bold tabular-nums">{{ ordonnances.length }}</p>
          <p class="mt-1 text-xs text-[var(--muted-foreground)]">PDF</p>
        </button>

        <button
          type="button"
          class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 text-left transition hover:border-[var(--primary)]/40 hover:bg-[var(--accent)]/40"
          @click="go('/prise-de-sang')"
        >
          <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Prises de sang</p>
          <p class="mt-1 text-2xl font-bold tabular-nums">{{ labPdfs.length }}</p>
          <p class="mt-1 text-xs text-[var(--muted-foreground)]">PDF</p>
        </button>
      </div>

      <!-- Raccourcis documents -->
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <button
          type="button"
          class="group flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 text-left transition hover:border-[var(--primary)]/40 hover:bg-[var(--accent)]/30"
          @click="go('/rapports')"
        >
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--accent)]">
            <FileText :size="18" class="text-[var(--primary)]" />
          </div>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-semibold text-[var(--foreground)]">Rapports</p>
            <p class="text-xs text-[var(--muted-foreground)]">Briefs & historiques</p>
          </div>
          <ArrowRight :size="14" class="text-[var(--muted-foreground)] transition group-hover:text-[var(--primary)]" />
        </button>
        <button
          type="button"
          class="group flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 text-left transition hover:border-[var(--primary)]/40 hover:bg-[var(--accent)]/30"
          @click="go('/ordonnances')"
        >
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--accent)]">
            <ScrollText :size="18" class="text-[var(--primary)]" />
          </div>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-semibold text-[var(--foreground)]">Ordonnances</p>
            <p class="text-xs text-[var(--muted-foreground)]">Médicaments & biologie</p>
          </div>
          <ArrowRight :size="14" class="text-[var(--muted-foreground)] transition group-hover:text-[var(--primary)]" />
        </button>
        <button
          type="button"
          class="group flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 text-left transition hover:border-[var(--primary)]/40 hover:bg-[var(--accent)]/30"
          @click="go('/prise-de-sang')"
        >
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--accent)]">
            <Droplets :size="18" class="text-[var(--primary)]" />
          </div>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-semibold text-[var(--foreground)]">Prise de sang</p>
            <p class="text-xs text-[var(--muted-foreground)]">Comptes-rendus labo</p>
          </div>
          <ArrowRight :size="14" class="text-[var(--muted-foreground)] transition group-hover:text-[var(--primary)]" />
        </button>
      </div>

      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <!-- Traitements actifs -->
        <section class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5">
          <div class="mb-4 flex items-center justify-between gap-3">
            <div class="flex items-center gap-2">
              <Pill :size="16" class="text-[var(--primary)]" />
              <h2 class="text-sm font-semibold text-[var(--foreground)]">Traitements en cours</h2>
            </div>
            <button
              type="button"
              class="inline-flex items-center gap-1 text-xs font-medium text-[var(--primary)] hover:underline"
              @click="go('/meds')"
            >
              Voir tout
              <ArrowRight :size="12" />
            </button>
          </div>
          <ul v-if="actifs.length" class="space-y-2">
            <li v-for="t in actifs.slice(0, 5)" :key="t.id">
              <button
                type="button"
                class="flex w-full items-center justify-between gap-3 rounded-lg px-2 py-2 text-left transition hover:bg-[var(--accent)]/50"
                @click="go(`/meds/${t.id}`)"
              >
                <div class="min-w-0">
                  <p class="truncate text-sm font-medium text-[var(--foreground)]">{{ t.nom }}</p>
                  <p class="text-xs text-[var(--muted-foreground)] capitalize">
                    {{ t.moment }}
                    <template v-if="t.si_besoin"> · si besoin</template>
                  </p>
                </div>
                <span
                  v-if="t.actuel"
                  class="shrink-0 rounded-md bg-[var(--secondary)] px-2 py-0.5 text-xs font-medium text-[var(--secondary-foreground)]"
                >
                  {{ t.actuel.dose }}
                </span>
              </button>
            </li>
          </ul>
          <p v-else class="py-6 text-center text-sm text-[var(--muted-foreground)]">
            Aucun traitement actif
          </p>
        </section>

        <!-- Analyses + posologie -->
        <section class="space-y-4">
          <button
            type="button"
            class="flex w-full flex-col rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 text-left transition hover:border-[var(--primary)]/40"
            @click="go('/suivi?tab=labs')"
          >
            <div class="mb-3 flex items-center justify-between gap-3">
              <div class="flex items-center gap-2">
                <Activity :size="16" class="text-[var(--primary)]" />
                <h2 class="text-sm font-semibold text-[var(--foreground)]">
                  {{ labsConfig.title || 'Analyses' }}
                </h2>
              </div>
              <ArrowRight :size="14" class="text-[var(--muted-foreground)]" />
            </div>
            <template v-if="latestPrimary">
              <p class="text-2xl font-bold tabular-nums text-[var(--foreground)]">
                {{ latestPrimary.value }}
                <span class="text-sm font-medium text-[var(--muted-foreground)]">
                  {{ latestPrimary.unit || labsConfig.markerUnit }}
                </span>
              </p>
              <p class="mt-1 text-xs text-[var(--muted-foreground)]">
                {{ latestPrimary.analyte }} · {{ latestPrimary.date }}
                <span
                  v-if="latestPrimary.out_of_range"
                  class="ml-1.5 text-amber-700"
                >hors normes</span>
              </p>
            </template>
            <p v-else class="text-sm text-[var(--muted-foreground)]">Pas encore de mesure</p>
          </button>

          <button
            type="button"
            class="flex w-full flex-col rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 text-left transition hover:border-[var(--primary)]/40"
            @click="go('/suivi?tab=rx')"
          >
            <div class="mb-3 flex items-center justify-between gap-3">
              <div class="flex items-center gap-2">
                <BookOpen :size="16" class="text-[var(--primary)]" />
                <h2 class="text-sm font-semibold text-[var(--foreground)]">
                  {{ rxConfig.title || 'Posologie' }}
                </h2>
              </div>
              <ArrowRight :size="14" class="text-[var(--muted-foreground)]" />
            </div>
            <template v-if="rxTreatment && rxDose">
              <p class="text-2xl font-bold tabular-nums text-[var(--foreground)]">
                {{ rxDose.doseLabel }}
              </p>
              <p class="mt-1 text-xs text-[var(--muted-foreground)]">
                {{ rxTreatment.nom }}
                <span class="mx-1">·</span>
                {{ rxDose.date }}
                <span
                  class="ml-1.5"
                  :class="rxActive ? 'text-emerald-700' : 'text-[var(--muted-foreground)]'"
                >
                  {{ rxActive ? 'actif' : 'arrêté' }}
                </span>
              </p>
            </template>
            <p v-else class="text-sm text-[var(--muted-foreground)]">Aucune série configurée</p>
          </button>
        </section>
      </div>

      <!-- Documents récents -->
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <section class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5">
          <div class="mb-3 flex items-center justify-between gap-3">
            <div class="flex items-center gap-2">
              <FileText :size="16" class="text-[var(--primary)]" />
              <h2 class="text-sm font-semibold">Derniers rapports</h2>
            </div>
            <button
              type="button"
              class="inline-flex items-center gap-1 text-xs font-medium text-[var(--primary)] hover:underline"
              @click="go('/rapports')"
            >
              Tous
              <ArrowRight :size="12" />
            </button>
          </div>
          <ul v-if="recentReports.length" class="space-y-1.5">
            <li v-for="r in recentReports" :key="r.id">
              <button
                type="button"
                class="flex w-full flex-col rounded-lg px-2 py-1.5 text-left transition hover:bg-[var(--accent)]/50"
                @click="go(`/rapports/${r.id}`)"
              >
                <span class="truncate text-sm font-medium text-[var(--foreground)]">{{ r.title }}</span>
                <span class="text-[11px] text-[var(--muted-foreground)]">{{ formatReportDate(r.date) }}</span>
              </button>
            </li>
          </ul>
          <p v-else class="py-4 text-center text-sm text-[var(--muted-foreground)]">Aucun rapport</p>
        </section>

        <section class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5">
          <div class="mb-3 flex items-center justify-between gap-3">
            <div class="flex items-center gap-2">
              <ScrollText :size="16" class="text-[var(--primary)]" />
              <h2 class="text-sm font-semibold">Dernières ordonnances</h2>
            </div>
            <button
              type="button"
              class="inline-flex items-center gap-1 text-xs font-medium text-[var(--primary)] hover:underline"
              @click="go('/ordonnances')"
            >
              Toutes
              <ArrowRight :size="12" />
            </button>
          </div>
          <ul v-if="recentOrdonnances.length" class="space-y-1.5">
            <li v-for="o in recentOrdonnances" :key="o.id">
              <button
                type="button"
                class="flex w-full flex-col rounded-lg px-2 py-1.5 text-left transition hover:bg-[var(--accent)]/50"
                @click="go(`/ordonnances/${encodeURIComponent(o.id)}`)"
              >
                <span class="truncate text-sm font-medium text-[var(--foreground)]">
                  {{
                    o.kind === 'biologie'
                      ? `Biologie · ${formatOrdonnanceDate(o.date)}`
                      : `Ordonnance · ${formatOrdonnanceDate(o.date)}`
                  }}
                </span>
                <span class="truncate text-[11px] text-[var(--muted-foreground)]">{{ o.prescriber }}</span>
              </button>
            </li>
          </ul>
          <p v-else class="py-4 text-center text-sm text-[var(--muted-foreground)]">Aucune ordonnance</p>
        </section>

        <section class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5">
          <div class="mb-3 flex items-center justify-between gap-3">
            <div class="flex items-center gap-2">
              <Droplets :size="16" class="text-[var(--primary)]" />
              <h2 class="text-sm font-semibold">Dernières prises de sang</h2>
            </div>
            <button
              type="button"
              class="inline-flex items-center gap-1 text-xs font-medium text-[var(--primary)] hover:underline"
              @click="go('/prise-de-sang')"
            >
              Toutes
              <ArrowRight :size="12" />
            </button>
          </div>
          <ul v-if="recentLabs.length" class="space-y-1.5">
            <li v-for="lab in recentLabs" :key="lab.id">
              <button
                type="button"
                class="flex w-full flex-col rounded-lg px-2 py-1.5 text-left transition hover:bg-[var(--accent)]/50"
                @click="go(`/prise-de-sang/${encodeURIComponent(lab.id)}`)"
              >
                <span class="truncate text-sm font-medium text-[var(--foreground)]">
                  {{ lab.date ? `Résultats · ${formatLabDate(lab.date)}` : lab.title }}
                </span>
                <span class="text-[11px] text-[var(--muted-foreground)]">{{ lab.lab }}</span>
              </button>
            </li>
          </ul>
          <p v-else class="py-4 text-center text-sm text-[var(--muted-foreground)]">Aucun PDF</p>
        </section>
      </div>

      <!-- Profil + poids -->
      <div class="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <button
          type="button"
          class="flex flex-col rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 text-left transition hover:border-[var(--primary)]/40"
          @click="go('/poids')"
        >
          <div class="mb-3 flex items-center gap-2">
            <Scale :size="16" class="text-[var(--primary)]" />
            <h2 class="text-sm font-semibold">Poids</h2>
          </div>
          <template v-if="dernier">
            <p class="text-xl font-bold tabular-nums">{{ dernier.poids_kg }} kg</p>
            <p class="mt-1 text-xs text-[var(--muted-foreground)]">au {{ dernier.date }}</p>
            <p
              v-if="delta != null"
              class="mt-3 text-xs"
              :class="delta > 0 ? 'text-amber-700' : delta < 0 ? 'text-emerald-700' : 'text-[var(--muted-foreground)]'"
            >
              {{ delta > 0 ? '+' : '' }}{{ delta }} kg sur la période suivie
            </p>
          </template>
          <p v-else class="text-sm text-[var(--muted-foreground)]">Pas de données</p>
        </button>

        <button
          type="button"
          class="flex flex-col rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 text-left transition hover:border-[var(--primary)]/40"
          @click="go('/profil')"
        >
          <div class="mb-3 flex items-center gap-2">
            <UserRound :size="16" class="text-[var(--primary)]" />
            <h2 class="text-sm font-semibold">Profil</h2>
          </div>
          <template v-if="profil">
            <p class="text-xl font-bold">{{ profil.prenom }} {{ profil.nom }}</p>
            <p class="mt-1 text-xs text-[var(--muted-foreground)] capitalize">
              {{ profil.sexe }}
              <span class="mx-1">·</span>
              {{ profil.taille_cm }} cm
            </p>
          </template>
          <p v-else class="text-sm text-[var(--muted-foreground)]">Profil indisponible</p>
        </button>
      </div>
    </div>
  </PageShell>
</template>
