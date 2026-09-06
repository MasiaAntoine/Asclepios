<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useSseStream } from '@/composables/usePdfApi'
import PageShell from '@/components/PageShell.vue'
import {
  Cloud,
  CloudDownload,
  CloudUpload,
  HardDrive,
  KeyRound,
  Loader,
  Server,
  X,
} from '@lucide/vue'

interface SettingsStatus {
  cursor_api_configured: boolean
  ovh_configured: boolean
  sync_files_tracked: number
  sync_state_date: string | null
  ai_model: string
  app_version: string
  vault_files: number
  vault_bytes: number
  ovh_bytes_estimated: number
  storage_class: string
  storage_region: string
  storage_eur_ht_per_gib_month: number
  storage_eur_ht_per_month: number
  storage_eur_ttc_per_month: number
}

const status = ref<SettingsStatus | null>(null)
const statusError = ref<string | null>(null)
const statusLoading = ref(true)

const {
  lines: syncLines,
  running: syncRunning,
  done: syncDone,
  error: syncError,
  run: runStream,
  cancel: cancelStream,
} = useSseStream()

const showTerminal = ref(false)
const terminalEl = ref<HTMLElement | null>(null)
const lastAction = ref('')

async function loadStatus() {
  statusLoading.value = true
  statusError.value = null
  try {
    const res = await fetch('/api/settings/status')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    status.value = (await res.json()) as SettingsStatus
  } catch (e) {
    statusError.value = e instanceof Error ? e.message : 'Erreur'
  } finally {
    statusLoading.value = false
  }
}

async function runAction(endpoint: string, label: string) {
  lastAction.value = label
  showTerminal.value = true
  await runStream(endpoint)
  await loadStatus()
}

function scrollBottom() {
  if (terminalEl.value) terminalEl.value.scrollTop = terminalEl.value.scrollHeight
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`
  const units = ['Ko', 'Mo', 'Go', 'To']
  let value = bytes / 1024
  let i = 0
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024
    i += 1
  }
  const digits = value >= 10 ? 0 : 1
  return `${value.toFixed(digits).replace('.', ',')} ${units[i]}`
}

function formatEur(amount: number, digits?: number): string {
  const fraction = digits ?? (amount < 0.01 ? 4 : 2)
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: fraction,
    maximumFractionDigits: fraction,
  }).format(amount)
}

const vaultSizeLabel = computed(() =>
  status.value ? formatSize(status.value.vault_bytes) : '',
)
const ovhSizeLabel = computed(() =>
  status.value ? formatSize(status.value.ovh_bytes_estimated) : '',
)
const monthlyCostLabel = computed(() => {
  if (!status.value) return ''
  const ttc = status.value.storage_eur_ttc_per_month
  if (ttc < 0.01) return 'moins de 0,01\u00a0€'
  return formatEur(ttc)
})

onMounted(() => {
  void loadStatus()
})
</script>

<template>
  <PageShell
    title="Paramètres"
    description="Synchronisation OVH et configuration"
    max-width="sm"
  >
    <div class="space-y-6">
      <!-- Statut -->
      <section class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5">
        <h2 class="mb-4 text-sm font-semibold text-[var(--foreground)]">État du système</h2>
        <p v-if="statusLoading" class="text-sm text-[var(--muted-foreground)]">Chargement…</p>
        <p v-else-if="statusError" class="text-sm text-red-600">{{ statusError }}</p>
        <div v-else-if="status" class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div class="flex items-start gap-3 rounded-xl bg-[var(--muted)]/60 px-4 py-3">
            <Server :size="18" class="mt-0.5 text-[var(--primary)]" />
            <div>
              <p class="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">OVH</p>
              <p class="mt-0.5 text-sm font-semibold" :class="status.ovh_configured ? 'text-emerald-700' : 'text-amber-700'">
                {{ status.ovh_configured ? 'Configuré' : 'Variables manquantes' }}
              </p>
              <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">
                {{ status.sync_files_tracked }} fichier{{ status.sync_files_tracked > 1 ? 's' : '' }} suivi{{ status.sync_files_tracked > 1 ? 's' : '' }}
                <template v-if="status.sync_state_date"> · état du {{ status.sync_state_date }}</template>
              </p>
            </div>
          </div>
          <div class="flex items-start gap-3 rounded-xl bg-[var(--muted)]/60 px-4 py-3">
            <KeyRound :size="18" class="mt-0.5 text-[var(--primary)]" />
            <div>
              <p class="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">IA Cursor</p>
              <p class="mt-0.5 text-sm font-semibold" :class="status.cursor_api_configured ? 'text-emerald-700' : 'text-amber-700'">
                {{ status.cursor_api_configured ? 'Clé présente' : 'CURSOR_API_KEY absente' }}
              </p>
              <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">Modèle : {{ status.ai_model }}</p>
            </div>
          </div>
        </div>
        <p v-if="status" class="mt-3 text-xs text-[var(--muted-foreground)]">
          Asclepios {{ status.app_version }} · secrets uniquement dans <code class="rounded bg-[var(--muted)] px-1">.env</code>
        </p>
      </section>

      <!-- Stockage -->
      <section v-if="status" class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5">
        <div class="mb-4 flex items-center gap-2">
          <HardDrive :size="16" class="text-[var(--primary)]" />
          <h2 class="text-sm font-semibold text-[var(--foreground)]">Stockage du vault</h2>
        </div>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div class="rounded-xl bg-[var(--muted)]/60 px-4 py-3">
            <p class="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Données locales</p>
            <p class="mt-1 text-lg font-semibold tabular-nums text-[var(--foreground)]">{{ vaultSizeLabel }}</p>
            <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">
              {{ status.vault_files }} fichier{{ status.vault_files > 1 ? 's' : '' }}
              · {{ ovhSizeLabel }} chiffrés sur OVH
            </p>
          </div>
          <div class="rounded-xl bg-[var(--muted)]/60 px-4 py-3">
            <p class="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Coût mensuel</p>
            <p class="mt-1 text-lg font-semibold tabular-nums text-[var(--foreground)]">{{ monthlyCostLabel }}</p>
            <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">
              {{ formatEur(status.storage_eur_ttc_per_month) }} TTC
              · {{ formatEur(status.storage_eur_ht_per_month) }} HT
            </p>
          </div>
        </div>
        <p class="mt-3 text-xs text-[var(--muted-foreground)]">
          Estimation {{ status.storage_class }} ({{ status.storage_region }})
          à {{ formatEur(status.storage_eur_ht_per_gib_month, 4) }} HT / Gio / mois.
          Pas de frais d’API, d’entrée ni de sortie.
        </p>
      </section>

      <!-- Sync -->
      <section class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5">
        <div class="mb-4 flex items-center gap-2">
          <Cloud :size="16" class="text-[var(--primary)]" />
          <h2 class="text-sm font-semibold text-[var(--foreground)]">Synchronisation OVH</h2>
        </div>
        <p class="mb-4 text-xs text-[var(--muted-foreground)]">
          Push envoie les fichiers locaux chiffrés. Pull récupère depuis le bucket (écrase le local si conflit).
        </p>
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="inline-flex items-center gap-2 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] disabled:opacity-50"
            :disabled="syncRunning"
            @click="runAction('/sync/push', 'Push')"
          >
            <CloudUpload :size="15" />
            Push
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--accent)] disabled:opacity-50"
            :disabled="syncRunning"
            @click="runAction('/sync/pull', 'Pull')"
          >
            <CloudDownload :size="15" />
            Pull
          </button>
          <button
            v-if="syncRunning"
            type="button"
            class="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm font-medium text-red-700"
            @click="cancelStream"
          >
            <X :size="15" />
            Annuler
          </button>
        </div>
      </section>

      <!-- Terminal -->
      <section v-if="showTerminal" class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-[var(--foreground)]">
            Journal{{ lastAction ? ` — ${lastAction}` : '' }}
          </h2>
          <button
            v-if="!syncRunning"
            type="button"
            class="text-xs text-[var(--muted-foreground)] hover:underline"
            @click="showTerminal = false"
          >
            Masquer
          </button>
        </div>
        <div
          ref="terminalEl"
          class="max-h-80 overflow-y-auto rounded-xl border border-[var(--border)] bg-[oklch(0.12_0.02_165)] p-4 font-mono text-[11.5px] leading-5 text-slate-200"
          @vue:updated="scrollBottom"
        >
          <p v-if="!syncLines.length && !syncRunning" class="text-slate-500">En attente…</p>
          <p
            v-for="(line, i) in syncLines"
            :key="i"
            :class="[
              line.startsWith('✗') ? 'text-red-400' :
              line.startsWith('✓') ? 'text-emerald-400' :
              line.startsWith('▶') ? 'text-[var(--primary)] font-semibold' :
              'text-slate-300',
            ]"
          >{{ line }}</p>
          <p v-if="syncRunning" class="mt-1 flex items-center gap-1.5 text-slate-400">
            <Loader :size="12" class="animate-spin" />
            En cours…
          </p>
          <p v-if="syncDone && !syncError" class="mt-1 font-semibold text-emerald-400">✓ Terminé</p>
          <p v-if="syncError" class="mt-1 font-semibold text-red-400">✗ {{ syncError }}</p>
        </div>
      </section>
    </div>
  </PageShell>
</template>
