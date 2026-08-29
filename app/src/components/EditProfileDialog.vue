<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useSseStream } from '@/composables/usePdfApi'
import type { Profil } from '@/composables/useProfile'
import { Pencil, X, Loader } from '@lucide/vue'

const props = defineProps<{ profil: Profil }>()
const emit = defineEmits<{ (e: 'saved'): void }>()

const open = ref(false)
const success = ref(false)
const terminalEl = ref<HTMLElement | null>(null)
const { lines, running, done: streamDone, error: streamError, run, cancel, reset } = useSseStream()

const prenom = ref('')
const nom = ref('')
const dateNaissance = ref('')
const sexe = ref('homme')
const tailleCm = ref('')
const tabacType = ref('')
const tabacDebut = ref('')
const tabacNicotine = ref('')
const tabacNote = ref('')

const canSubmit = computed(
  () =>
    !running.value &&
    prenom.value.trim() &&
    nom.value.trim() &&
    dateNaissance.value.trim() &&
    sexe.value &&
    parseFloat(tailleCm.value) > 0,
)

watch(streamDone, (v) => {
  if (v && !streamError.value) {
    success.value = true
    emit('saved')
  }
})

function fillFromProfil() {
  prenom.value = props.profil.prenom
  nom.value = props.profil.nom
  dateNaissance.value = props.profil.date_naissance
  sexe.value = props.profil.sexe
  tailleCm.value = String(props.profil.taille_cm)
  tabacType.value = props.profil.tabac?.type ?? ''
  tabacDebut.value = props.profil.tabac?.debut ?? ''
  tabacNicotine.value =
    props.profil.tabac?.nicotine_mg_ml != null ? String(props.profil.tabac.nicotine_mg_ml) : ''
  tabacNote.value = props.profil.tabac?.note ?? ''
}

function openDialog() {
  reset()
  success.value = false
  fillFromProfil()
  open.value = true
}

function closeDialog() {
  if (!running.value) {
    cancel()
    open.value = false
  }
}

async function submit() {
  success.value = false
  await run('/profil/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prenom: prenom.value.trim(),
      nom: nom.value.trim(),
      date_naissance: dateNaissance.value.trim(),
      sexe: sexe.value,
      taille_cm: parseFloat(tailleCm.value),
      tabac_type: tabacType.value.trim(),
      tabac_debut: tabacDebut.value.trim(),
      tabac_nicotine_mg_ml: tabacNicotine.value ? parseFloat(tabacNicotine.value) : null,
      tabac_note: tabacNote.value.trim(),
    }),
  })
}

function scrollBottom() {
  if (terminalEl.value) terminalEl.value.scrollTop = terminalEl.value.scrollHeight
}

const inputClass =
  'w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20'
</script>

<template>
  <button
    type="button"
    class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm font-medium text-[var(--foreground)] transition hover:bg-[var(--accent)]"
    @click="openDialog"
  >
    <Pencil :size="15" />
    Modifier
  </button>

  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm"
      @click.self="closeDialog"
    >
      <div class="relative max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-[var(--card)] shadow-2xl ring-1 ring-[var(--border)]">
        <div class="sticky top-0 z-10 flex items-center justify-between border-b border-[var(--border)] bg-[var(--card)] px-6 py-4">
          <div>
            <h2 class="text-base font-semibold text-[var(--foreground)]">Modifier le profil</h2>
            <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">Identité, taille et tabac</p>
          </div>
          <button
            type="button"
            class="rounded-lg p-1.5 text-[var(--muted-foreground)] transition hover:bg-[var(--muted)]"
            @click="closeDialog"
          >
            <X :size="16" />
          </button>
        </div>

        <div class="space-y-4 px-6 py-5">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Prénom *</label>
              <input v-model="prenom" type="text" :class="inputClass" />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Nom *</label>
              <input v-model="nom" type="text" :class="inputClass" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Naissance (JJ/MM/AAAA) *</label>
              <input v-model="dateNaissance" type="text" placeholder="15/08/2001" :class="inputClass" />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Sexe *</label>
              <select v-model="sexe" :class="inputClass">
                <option value="homme">Homme</option>
                <option value="femme">Femme</option>
                <option value="autre">Autre</option>
              </select>
            </div>
          </div>

          <div>
            <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Taille (cm) *</label>
            <input v-model="tailleCm" type="number" step="1" min="50" max="250" :class="inputClass" />
          </div>

          <div class="rounded-xl border border-[var(--border)] p-3 space-y-3">
            <p class="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">Tabac</p>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Type</label>
                <input v-model="tabacType" type="text" :class="inputClass" />
              </div>
              <div>
                <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Depuis</label>
                <input v-model="tabacDebut" type="text" placeholder="09/04/2025" :class="inputClass" />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Nicotine (mg/ml)</label>
                <input v-model="tabacNicotine" type="number" step="0.1" :class="inputClass" />
              </div>
              <div>
                <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Note</label>
                <input v-model="tabacNote" type="text" :class="inputClass" />
              </div>
            </div>
          </div>

          <div
            v-if="lines.length || running || streamError"
            ref="terminalEl"
            class="max-h-36 overflow-y-auto rounded-xl border border-[var(--border)] bg-[oklch(0.12_0.02_165)] p-3 font-mono text-[11px] leading-5 text-slate-200"
            @vue:updated="scrollBottom"
          >
            <p v-for="(line, i) in lines" :key="i" class="text-slate-300">{{ line }}</p>
            <p v-if="running" class="mt-1 flex items-center gap-1.5 text-slate-400">
              <Loader :size="12" class="animate-spin" /> En cours…
            </p>
            <p v-if="streamError" class="mt-1 text-red-400">{{ streamError }}</p>
            <p v-if="success" class="mt-1 font-semibold text-emerald-400">✓ Profil enregistré</p>
          </div>
        </div>

        <div class="sticky bottom-0 flex justify-end gap-2 border-t border-[var(--border)] bg-[var(--card)] px-6 py-4">
          <button
            type="button"
            class="rounded-lg px-3 py-2 text-sm text-[var(--muted-foreground)] hover:bg-[var(--muted)]"
            :disabled="running"
            @click="closeDialog"
          >
            {{ success ? 'Fermer' : 'Annuler' }}
          </button>
          <button
            v-if="!success"
            type="button"
            class="inline-flex items-center gap-2 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] disabled:opacity-50"
            :disabled="!canSubmit"
            @click="submit"
          >
            <Loader v-if="running" :size="14" class="animate-spin" />
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
