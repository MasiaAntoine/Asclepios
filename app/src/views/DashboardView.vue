<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProfile } from '@/composables/useProfile'
import { useReports } from '@/composables/useReports'
import { usePoids } from '@/composables/usePoids'
import { useLabs } from '@/composables/useLabs'
import { useMedications } from '@/composables/useMedications'
import { useMedicationSeries } from '@/composables/useMedicationSeries'
import { useSseStream } from '@/composables/usePdfApi'
import {
  Activity,
  ArrowRight,
  BookOpen,
  Cloud,
  FileText,
  Loader,
  Pill,
  Scale,
  Terminal,
  TrendingDown,
  TrendingUp,
  UserRound,
  X,
} from '@lucide/vue'
import Mascotte from '@/components/Mascotte.vue'

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

const loading = computed(
  () =>
    (profileLoading.value && !profil.value) ||
    (reportsLoading.value && !reports.value.length) ||
    (poidsLoading.value && !dernier.value) ||
    labsLoading.value ||
    medsLoading.value ||
    rxLoading.value,
)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Bonjour'
  if (h < 18) return 'Bon après-midi'
  return 'Bonsoir'
})

const recentReports = computed(() => reports.value.slice(0, 4))

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
  router.push(path)
}

// ── Pipeline sync ──────────────────────────────────────────────────────────
const { lines: syncLines, running: syncRunning, done: syncDone, error: syncError, run: runPipeline, cancel: cancelPipeline } = useSseStream()
const showSyncPanel = ref(false)
const terminalEl = ref<HTMLElement | null>(null)

async function startPipeline() {
  showSyncPanel.value = true
  await runPipeline('/pipeline/run')
}

function scrollToBottom() {
  if (terminalEl.value) {
    terminalEl.value.scrollTop = terminalEl.value.scrollHeight
  }
}
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <div class="border-b border-[var(--border)] bg-[var(--card)] px-8 py-6">
      <h1 class="text-2xl font-bold text-[var(--foreground)]">Tableau de bord</h1>
      <p class="mt-0.5 text-sm text-[var(--muted-foreground)]">
        <template v-if="profil">
          {{ greeting }}, {{ profil.prenom }}
          <template v-if="age !== null"> · {{ age }} ans</template>
        </template>
        <template v-else>Vue d’ensemble du suivi</template>
      </p>
      <p v-if="profileError" class="mt-1 text-xs text-red-600">{{ profileError }}</p>
    </div>

    <div class="flex-1 overflow-y-auto px-8 py-8">
      <div v-if="loading && !profil" class="py-24 text-center text-sm text-[var(--muted-foreground)]">
        Chargement…
      </div>

      <div v-else class="mx-auto max-w-6xl space-y-8">
        <!-- ── Bannière de bienvenue avec mascotte ── -->
        <div class="relative overflow-visible rounded-2xl bg-gradient-to-br from-[var(--primary)] to-[oklch(0.52_0.14_165)] px-6 pt-6 pb-24 text-white shadow-md">
          <!-- Cercles décoratifs -->
          <div class="pointer-events-none absolute -right-8 -top-8 h-40 w-40 rounded-full bg-white/10"/>
          <div class="pointer-events-none absolute bottom-0 right-24 h-32 w-32 rounded-full bg-white/8"/>
          <!-- Mascotte ancrée en bas à droite de la card -->
          <div class="pointer-events-none absolute bottom-0 right-4 z-10 hidden sm:block">
            <Mascotte pose="waving" class="h-72 w-auto drop-shadow-2xl"/>
          </div>
          <!-- Texte -->
          <div class="relative z-10 max-w-sm">
            <p class="text-xs font-semibold uppercase tracking-widest text-white/70">Asclepios</p>
            <h2 class="mt-1 text-2xl font-bold leading-tight">
              <template v-if="profil">{{ greeting }}, {{ profil.prenom }} 👋</template>
              <template v-else>Votre suivi médical</template>
            </h2>
            <p class="mt-2 text-sm text-white/80">
              <template v-if="profil">
                Tout va bien ? Je suis là pour vous aider à suivre votre santé.
              </template>
              <template v-else>
                Consultez vos données de santé en un coup d'œil.
              </template>
            </p>
          </div>
        </div>

        <!-- KPIs -->
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <button
            type="button"
            class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 text-left transition hover:border-[var(--primary)]/40 hover:bg-[var(--accent)]/40"
            @click="go('/poids')"
          >
            <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
              Poids
            </p>
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
            <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
              IMC
            </p>
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
            <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
              Traitements
            </p>
            <p class="mt-1 text-2xl font-bold tabular-nums text-emerald-700">{{ actifs.length }}</p>
            <p class="mt-1 text-xs text-[var(--muted-foreground)]">en cours</p>
          </button>

          <button
            type="button"
            class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 text-left transition hover:border-[var(--primary)]/40 hover:bg-[var(--accent)]/40"
            @click="go('/rapports')"
          >
            <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
              Rapports
            </p>
            <p class="mt-1 text-2xl font-bold tabular-nums">{{ reports.length }}</p>
            <p class="mt-1 text-xs text-[var(--muted-foreground)]">au total</p>
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
              @click="go('/labs')"
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
              @click="go('/rx')"
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

        <!-- Poids résumé + profil -->
        <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <button
            type="button"
            class="flex flex-col rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 text-left transition hover:border-[var(--primary)]/40 lg:col-span-1"
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
            class="flex flex-col rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 text-left transition hover:border-[var(--primary)]/40 lg:col-span-1"
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

          <div class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 lg:col-span-1">
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
            <p v-else class="py-4 text-center text-sm text-[var(--muted-foreground)]">
              Aucun rapport
            </p>
          </div>
        </div>

        <!-- ── Synchronisation OVH ─────────────────────────────────────── -->
        <section class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5">
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div class="flex items-center gap-2">
                <Cloud :size="16" class="text-[var(--primary)]" />
                <h2 class="text-sm font-semibold text-[var(--foreground)]">Générer les PDFs et synchroniser OVH</h2>
              </div>
              <p class="mt-1 text-xs text-[var(--muted-foreground)]">
                Génère tous les comptes-rendus PDF puis pousse les données chiffrées vers OVH Object Storage.
              </p>
            </div>
            <div class="flex shrink-0 flex-wrap gap-2">
              <button
                v-if="!syncRunning"
                type="button"
                class="inline-flex items-center gap-2 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] shadow-sm transition hover:opacity-90"
                @click="startPipeline"
              >
                <Terminal :size="15" />
                Lancer le pipeline
              </button>
              <button
                v-else
                type="button"
                class="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-100"
                @click="cancelPipeline"
              >
                <X :size="15" />
                Annuler
              </button>
              <button
                v-if="showSyncPanel && !syncRunning"
                type="button"
                class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-2 text-sm text-[var(--muted-foreground)] transition hover:bg-[var(--accent)]"
                @click="showSyncPanel = false"
              >
                <X :size="14" />
                Fermer
              </button>
            </div>
          </div>

          <!-- Terminal live -->
          <div
            v-if="showSyncPanel"
            ref="terminalEl"
            class="mt-4 max-h-72 overflow-y-auto rounded-xl border border-[var(--border)] bg-[oklch(0.12_0.02_165)] p-4 font-mono text-[11.5px] leading-5 text-slate-200 shadow-inner"
            @vue:updated="scrollToBottom"
          >
            <p v-if="!syncLines.length" class="text-slate-500">En attente…</p>
            <p
              v-for="(line, i) in syncLines"
              :key="i"
              :class="[
                line.startsWith('✗') ? 'text-red-400' :
                line.startsWith('✓') ? 'text-emerald-400' :
                line.startsWith('▶') ? 'text-[var(--primary)] font-semibold' :
                line.startsWith('↑') ? 'text-sky-400' :
                line.startsWith('×') ? 'text-amber-400' :
                line.startsWith('🚀') ? 'text-[var(--primary)] font-bold' :
                line.startsWith('🏁') ? 'text-emerald-400 font-bold' :
                'text-slate-300'
              ]"
            >{{ line }}</p>
            <p v-if="syncRunning" class="mt-1 flex items-center gap-1.5 text-slate-400">
              <Loader :size="12" class="animate-spin" />
              <span>En cours…</span>
            </p>
            <p v-if="syncDone && !syncError" class="mt-1 font-semibold text-emerald-400">🏁 Pipeline terminé avec succès.</p>
            <p v-if="syncError" class="mt-1 font-semibold text-red-400">✗ {{ syncError }}</p>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
