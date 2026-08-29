<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useSseStream } from '@/composables/usePdfApi'
import type { Doctor } from '@/composables/useDoctors'
import { Pencil, Plus, Trash2, X, Loader } from '@lucide/vue'

const props = defineProps<{
  mode: 'create' | 'edit'
  doctor?: Doctor | null
}>()

const emit = defineEmits<{ (e: 'saved'): void; (e: 'deleted'): void }>()

const open = ref(false)
const success = ref(false)
const deleting = ref(false)
const terminalEl = ref<HTMLElement | null>(null)
const { lines, running, done: streamDone, error: streamError, run, cancel, reset } = useSseStream()

const titre = ref('Dr')
const prenom = ref('')
const nom = ref('')
const specialite = ref('')
const role = ref('')
const telephone = ref('')
const doctolib = ref('')
const voie = ref('')
const codePostal = ref('')
const ville = ref('')
const presentation = ref('')
const notes = ref('')

const canSubmit = computed(
  () =>
    !running.value &&
    prenom.value.trim() &&
    nom.value.trim() &&
    specialite.value.trim(),
)

watch(streamDone, (v) => {
  if (v && !streamError.value) {
    success.value = true
    if (deleting.value) emit('deleted')
    else emit('saved')
  }
})

function fill() {
  if (props.mode === 'edit' && props.doctor) {
    const d = props.doctor
    titre.value = d.titre || 'Dr'
    prenom.value = d.prenom
    nom.value = d.nom
    specialite.value = d.specialite
    role.value = d.role ?? ''
    telephone.value = d.telephone ?? ''
    doctolib.value = d.doctolib ?? ''
    voie.value = d.adresse?.voie ?? ''
    codePostal.value = d.adresse?.code_postal ?? ''
    ville.value = d.adresse?.ville ?? ''
    presentation.value = d.presentation ?? ''
    notes.value = d.notes ?? ''
  } else {
    titre.value = 'Dr'
    prenom.value = ''
    nom.value = ''
    specialite.value = ''
    role.value = ''
    telephone.value = ''
    doctolib.value = ''
    voie.value = ''
    codePostal.value = ''
    ville.value = ''
    presentation.value = ''
    notes.value = ''
  }
}

function openDialog() {
  reset()
  success.value = false
  deleting.value = false
  fill()
  open.value = true
}

function closeDialog() {
  if (!running.value) {
    cancel()
    open.value = false
  }
}

function payload() {
  return {
    id: props.mode === 'edit' ? props.doctor?.id : null,
    titre: titre.value.trim(),
    prenom: prenom.value.trim(),
    nom: nom.value.trim(),
    specialite: specialite.value.trim(),
    role: role.value.trim(),
    telephone: telephone.value.trim(),
    doctolib: doctolib.value.trim(),
    voie: voie.value.trim(),
    code_postal: codePostal.value.trim(),
    ville: ville.value.trim(),
    presentation: presentation.value.trim(),
    notes: notes.value.trim(),
  }
}

async function submit() {
  success.value = false
  deleting.value = false
  const endpoint =
    props.mode === 'edit' && props.doctor
      ? `/doctors/${props.doctor.id}/update`
      : '/doctors'
  await run(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload()),
  })
}

async function remove() {
  if (!props.doctor || !confirm(`Supprimer ${props.doctor.prenom} ${props.doctor.nom} ?`)) return
  success.value = false
  deleting.value = true
  await run(`/doctors/${props.doctor.id}/delete`, { method: 'POST' })
}

function scrollBottom() {
  if (terminalEl.value) terminalEl.value.scrollTop = terminalEl.value.scrollHeight
}

const inputClass =
  'w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20'

defineExpose({ openDialog })
</script>

<template>
  <button
    v-if="mode === 'create'"
    type="button"
    class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--primary)]/30 bg-[var(--primary)]/8 px-3 py-2 text-sm font-medium text-[var(--primary)] transition hover:bg-[var(--primary)]/15"
    @click="openDialog"
  >
    <Plus :size="15" />
    Ajouter un médecin
  </button>
  <button
    v-else
    type="button"
    class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-2.5 py-1.5 text-xs font-medium text-[var(--foreground)] transition hover:bg-[var(--accent)]"
    @click.stop="openDialog"
  >
    <Pencil :size="13" />
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
            <h2 class="text-base font-semibold text-[var(--foreground)]">
              {{ mode === 'create' ? 'Nouveau médecin' : 'Modifier le médecin' }}
            </h2>
            <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">Informations principales</p>
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
          <div class="grid grid-cols-3 gap-3">
            <div>
              <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Titre</label>
              <input v-model="titre" type="text" :class="inputClass" />
            </div>
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
              <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Spécialité *</label>
              <input v-model="specialite" type="text" :class="inputClass" />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Rôle</label>
              <input v-model="role" type="text" placeholder="Médecin traitant…" :class="inputClass" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Téléphone</label>
              <input v-model="telephone" type="text" :class="inputClass" />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Doctolib</label>
              <input v-model="doctolib" type="url" :class="inputClass" />
            </div>
          </div>

          <div>
            <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Adresse</label>
            <input v-model="voie" type="text" placeholder="Voie" class="mb-2" :class="inputClass" />
            <div class="grid grid-cols-3 gap-2">
              <input v-model="codePostal" type="text" placeholder="CP" :class="inputClass" />
              <input v-model="ville" type="text" placeholder="Ville" class="col-span-2" :class="inputClass" />
            </div>
          </div>

          <div>
            <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Présentation</label>
            <textarea v-model="presentation" rows="3" :class="inputClass" />
          </div>

          <div>
            <label class="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Notes</label>
            <input v-model="notes" type="text" :class="inputClass" />
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
            <p v-if="success" class="mt-1 font-semibold text-emerald-400">✓ Enregistré</p>
          </div>
        </div>

        <div class="sticky bottom-0 flex items-center justify-between gap-2 border-t border-[var(--border)] bg-[var(--card)] px-6 py-4">
          <button
            v-if="mode === 'edit' && !success"
            type="button"
            class="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-red-600 hover:bg-red-50"
            :disabled="running"
            @click="remove"
          >
            <Trash2 :size="14" />
            Supprimer
          </button>
          <div v-else />
          <div class="flex gap-2">
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
              <Loader v-if="running && !deleting" :size="14" class="animate-spin" />
              Enregistrer
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
