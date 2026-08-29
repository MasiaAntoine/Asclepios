<script setup lang="ts">
import { ref } from 'vue'
import { Loader, Pencil, Save, X } from '@lucide/vue'
import { useSseStream } from '@/composables/usePdfApi'

const props = defineProps<{
  fichier: string
  titre: string
}>()

const emit = defineEmits<{ updated: [] }>()

const open = ref(false)
const fetching = ref(false)
const fetchError = ref<string | null>(null)

const posologie = ref('')
const arretTemporaire = ref('')
const notes = ref('')

const { lines, running, done, error: sseError, run } = useSseStream()

async function openDialog() {
  open.value = true
  fetching.value = true
  fetchError.value = null
  try {
    const res = await fetch(`/api/medication/${encodeURIComponent(props.fichier)}`)
    if (!res.ok) throw new Error(`Erreur ${res.status}`)
    const data = await res.json() as { posologie?: string; arret_temporaire?: string; notes?: string }
    posologie.value = data.posologie ?? ''
    arretTemporaire.value = data.arret_temporaire ?? ''
    notes.value = data.notes ?? ''
  } catch (e) {
    fetchError.value = e instanceof Error ? e.message : 'Erreur de chargement'
  } finally {
    fetching.value = false
  }
}

async function save() {
  await run('/medication/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      fichier: props.fichier,
      posologie: posologie.value || null,
      arret_temporaire: arretTemporaire.value || null,
      notes: notes.value || null,
    }),
  })
  if (!sseError.value) {
    emit('updated')
  }
}

function close() {
  if (running.value) return
  open.value = false
}
</script>

<template>
  <!-- Trigger -->
  <button
    type="button"
    @click="openDialog"
    class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-1.5 text-xs font-medium text-[var(--muted-foreground)] transition hover:border-[var(--primary)]/40 hover:text-[var(--primary)]"
  >
    <Pencil :size="13" />
    Mettre à jour
  </button>

  <!-- Overlay + Dialog -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-150"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-100"
      leave-to-class="opacity-0"
    >
      <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/50 backdrop-blur-sm"
          @click="close"
        />

        <!-- Panel -->
        <div class="relative z-10 w-full max-w-lg rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-2xl">

          <!-- Header -->
          <div class="flex items-center justify-between border-b border-[var(--border)] px-6 py-4">
            <div>
              <p class="font-semibold text-[var(--foreground)]">Mettre à jour — {{ titre }}</p>
              <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">{{ fichier }}</p>
            </div>
            <button
              @click="close"
              :disabled="running"
              class="rounded-lg p-1.5 text-[var(--muted-foreground)] transition hover:bg-[var(--muted)] hover:text-[var(--foreground)] disabled:opacity-40"
            >
              <X :size="18" />
            </button>
          </div>

          <!-- Body -->
          <div class="px-6 py-5 space-y-4">

            <div v-if="fetching" class="flex items-center gap-2 py-4 text-sm text-[var(--muted-foreground)]">
              <Loader :size="14" class="animate-spin" />
              Chargement des données actuelles…
            </div>

            <div v-else-if="fetchError" class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {{ fetchError }}
            </div>

            <template v-else>
              <!-- Posologie -->
              <div class="space-y-1.5">
                <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  Posologie actuelle
                </label>
                <input
                  v-model="posologie"
                  type="text"
                  :disabled="running"
                  class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder-[var(--muted-foreground)] transition focus:border-[var(--primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] disabled:opacity-50"
                  placeholder="ex. 25 µg — 1 comprimé le matin"
                />
              </div>

              <!-- Arrêt temporaire -->
              <div class="space-y-1.5">
                <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  Arrêt temporaire
                </label>
                <input
                  v-model="arretTemporaire"
                  type="text"
                  :disabled="running"
                  class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder-[var(--muted-foreground)] transition focus:border-[var(--primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] disabled:opacity-50"
                  placeholder="ex. 22/08/2025 → reprise 01/08/2026"
                />
              </div>

              <!-- Notes personnelles -->
              <div class="space-y-1.5">
                <label class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  Notes personnelles
                </label>
                <textarea
                  v-model="notes"
                  rows="5"
                  :disabled="running"
                  class="w-full resize-y rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder-[var(--muted-foreground)] transition focus:border-[var(--primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] disabled:opacity-50"
                  placeholder="Observations, ressenti, ajustements…"
                />
              </div>
            </template>

            <!-- Terminal SSE -->
            <div
              v-if="lines.length || running || sseError"
              class="max-h-36 overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--foreground)]/[0.03] p-3 font-mono text-[11px] leading-5"
            >
              <p v-if="running && !lines.length" class="flex items-center gap-1.5 text-[var(--muted-foreground)]">
                <Loader :size="10" class="animate-spin" /> Connexion…
              </p>
              <p v-for="(line, i) in lines" :key="i" :class="[
                line.startsWith('✗') ? 'text-red-600' :
                line.startsWith('✓') ? 'text-emerald-700' :
                line.startsWith('▶') ? 'text-[var(--primary)] font-semibold' :
                'text-[var(--muted-foreground)]'
              ]">{{ line }}</p>
              <p v-if="done && !sseError" class="font-semibold text-emerald-700">✓ Synchronisé avec OVH</p>
              <p v-if="sseError" class="font-semibold text-red-600">✗ {{ sseError }}</p>
            </div>
          </div>

          <!-- Footer -->
          <div class="flex justify-end gap-2 border-t border-[var(--border)] px-6 py-4">
            <button
              type="button"
              @click="close"
              :disabled="running"
              class="rounded-lg border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--muted-foreground)] transition hover:bg-[var(--accent)] disabled:opacity-40"
            >
              {{ done ? 'Fermer' : 'Annuler' }}
            </button>
            <button
              v-if="!done"
              type="button"
              @click="save"
              :disabled="running || fetching || !!fetchError"
              class="inline-flex items-center gap-1.5 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-[var(--primary)]/90 disabled:opacity-50"
            >
              <Loader v-if="running" :size="14" class="animate-spin" />
              <Save v-else :size="14" />
              {{ running ? 'Sauvegarde…' : 'Sauvegarder et synchroniser' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
