<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchOrdonnanceDetail,
  formatOrdonnanceDate,
  ordonnancePdfFileUrl,
  type OrdonnanceDetail,
} from '@/composables/useOrdonnances'
import { useProfile } from '@/composables/useProfile'
import PageShell from '@/components/PageShell.vue'
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Download,
  FlaskConical,
  MapPin,
  Phone,
  Pill,
  ScrollText,
  Stethoscope,
} from '@lucide/vue'

const route = useRoute()
const router = useRouter()
const { profil, age } = useProfile()

const detail = ref<OrdonnanceDetail | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const pdfId = computed(() => String(route.params.id || ''))

async function load() {
  if (!pdfId.value) return
  loading.value = true
  error.value = null
  detail.value = null
  try {
    detail.value = await fetchOrdonnanceDetail(pdfId.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Chargement impossible'
  } finally {
    loading.value = false
  }
}

watch(pdfId, () => void load(), { immediate: true })

const fullName = computed(() => {
  if (detail.value?.meta.patient) return detail.value.meta.patient
  if (profil.value) return `${profil.value.prenom} ${profil.value.nom}`
  return 'Patient'
})

function go(id: string | null) {
  if (!id) return
  void router.push(`/ordonnances/${encodeURIComponent(id)}`)
}
</script>

<template>
  <PageShell max-width="narrow">
    <template #header>
      <div class="flex items-center gap-3">
        <button
          type="button"
          class="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border)] text-[var(--muted-foreground)] transition hover:bg-[var(--accent)] hover:text-[var(--foreground)]"
          @click="router.push('/ordonnances')"
        >
          <ArrowLeft :size="16" />
        </button>
        <div class="min-w-0 flex-1">
          <h1 class="truncate text-lg font-bold text-[var(--foreground)]">
            {{
              detail?.meta.kind === 'biologie'
                ? (detail?.meta.date ? `Biologie du ${formatOrdonnanceDate(detail.meta.date)}` : 'Ordonnance de biologie')
                : (detail?.meta.date ? `Ordonnance du ${formatOrdonnanceDate(detail.meta.date)}` : 'Ordonnance')
            }}
          </h1>
          <p v-if="detail" class="truncate text-xs text-[var(--muted-foreground)]">
            {{ detail.meta.prescriber || 'Prescripteur inconnu' }}
            <template v-if="detail.meta.specialty"> · {{ detail.meta.specialty }}</template>
          </p>
        </div>
      </div>
    </template>

    <div v-if="error" class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {{ error }}
    </div>
    <div v-else-if="loading" class="py-24 text-center text-sm text-[var(--muted-foreground)]">
      Analyse du PDF…
    </div>
    <div v-else-if="detail" class="space-y-4 pb-10">
      <!-- Header card -->
      <section class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 shadow-sm">
        <p class="text-base font-bold text-[var(--foreground)]">{{ fullName }}</p>
        <p class="mt-0.5 text-sm text-[var(--muted-foreground)]">
          <template v-if="detail.meta.patient_birth">Né(e) le {{ detail.meta.patient_birth }}</template>
          <template v-else-if="profil">
            {{ profil.date_naissance }} · {{ profil.sexe }}
            <template v-if="age != null"> · {{ age }} ans</template>
          </template>
        </p>

        <div class="mt-4 flex items-start gap-3 border-t border-[var(--border)] pt-4">
          <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)]">
            <ScrollText :size="16" class="text-[var(--primary)]" />
          </div>
          <div class="min-w-0 space-y-1">
            <p class="font-semibold text-[var(--foreground)]">
              <template v-if="detail.meta.kind === 'biologie'">
                Biologie du {{ formatOrdonnanceDate(detail.meta.date) }}
              </template>
              <template v-else>
                Ordonnance du {{ formatOrdonnanceDate(detail.meta.date) }}
              </template>
            </p>
            <p v-if="detail.meta.prescriber" class="flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
              <Stethoscope :size="12" />
              {{ detail.meta.prescriber }}
              <template v-if="detail.meta.specialty"> · {{ detail.meta.specialty }}</template>
            </p>
            <p v-if="detail.meta.address" class="flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
              <MapPin :size="12" />
              {{ detail.meta.address }}
            </p>
            <p v-if="detail.meta.phone" class="flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
              <Phone :size="12" />
              {{ detail.meta.phone }}
            </p>
            <p v-if="detail.meta.duration" class="text-xs text-[var(--muted-foreground)]">
              {{ detail.meta.duration }}
            </p>
            <p v-if="detail.meta.signed_via" class="text-xs text-[var(--muted-foreground)]">
              Signé via {{ detail.meta.signed_via }}
              <template v-if="detail.meta.signed_at"> le {{ detail.meta.signed_at }}</template>
            </p>
            <p v-if="detail.meta.e_prescription" class="font-mono text-[11px] text-[var(--muted-foreground)]">
              e-prescription {{ detail.meta.e_prescription }}
            </p>
          </div>
        </div>

        <div class="mt-4 flex flex-wrap gap-2">
          <a
            :href="ordonnancePdfFileUrl(detail.id)"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-[var(--primary)]/40 px-3 py-2 text-sm font-medium text-[var(--primary)] transition hover:bg-[var(--primary)]/10 sm:flex-none"
          >
            <Download :size="14" />
            Télécharger
          </a>
        </div>

        <div class="mt-4 flex items-center justify-between border-t border-[var(--border)] pt-3 text-sm">
          <button
            type="button"
            class="inline-flex items-center gap-1 text-[var(--muted-foreground)] transition hover:text-[var(--primary)] disabled:opacity-30"
            :disabled="!detail.navigation.prev_id"
            @click="go(detail.navigation.prev_id)"
          >
            <ChevronLeft :size="16" />
            Précédent
          </button>
          <span class="text-xs text-[var(--muted-foreground)]">
            {{ detail.navigation.index + 1 }} / {{ detail.navigation.total }}
          </span>
          <button
            type="button"
            class="inline-flex items-center gap-1 text-[var(--muted-foreground)] transition hover:text-[var(--primary)] disabled:opacity-30"
            :disabled="!detail.navigation.next_id"
            @click="go(detail.navigation.next_id)"
          >
            Suivant
            <ChevronRight :size="16" />
          </button>
        </div>
      </section>

      <p
        v-if="!detail.parsable || detail.note"
        class="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
      >
        {{ detail.note || 'Parsing structuré limité. Consultez le PDF source.' }}
      </p>

      <!-- Médicaments -->
      <section v-if="detail.meta.kind !== 'biologie'" class="space-y-2">
        <h2 class="flex items-center gap-2 px-1 text-base font-bold text-[var(--foreground)]">
          <Pill :size="16" class="text-[var(--primary)]" />
          Médicaments prescrits
          <span class="text-sm font-normal text-[var(--muted-foreground)]">
            ({{ detail.medications.length }})
          </span>
        </h2>

        <div
          v-if="!detail.medications.length"
          class="rounded-2xl border border-dashed border-[var(--border)] px-4 py-8 text-center text-sm text-[var(--muted-foreground)]"
        >
          Aucun médicament détecté — ouvrez le PDF.
        </div>

        <div
          v-else
          class="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-sm divide-y divide-[var(--border)]"
        >
          <div
            v-for="(med, idx) in detail.medications"
            :key="idx"
            class="flex items-start gap-3 px-4 py-3.5"
          >
            <div class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)]">
              <ClipboardList :size="14" class="text-[var(--primary)]" />
            </div>
            <div class="min-w-0 flex-1">
              <p class="font-semibold text-[var(--foreground)]">{{ med.name }}</p>
              <p v-if="med.posology" class="mt-0.5 text-sm text-[var(--muted-foreground)]">
                {{ med.posology }}
              </p>
              <div class="mt-2 flex flex-wrap gap-1.5">
                <span
                  v-if="med.brand"
                  class="rounded-full bg-[var(--secondary)] px-2 py-0.5 text-[10px] font-medium text-[var(--secondary-foreground)]"
                >
                  {{ med.brand }}
                </span>
                <span
                  v-if="med.dose"
                  class="rounded-full bg-[var(--accent)] px-2 py-0.5 text-[10px] font-medium text-[var(--accent-foreground)]"
                >
                  {{ med.dose }}
                </span>
                <span
                  v-if="med.form"
                  class="rounded-full bg-[var(--muted)] px-2 py-0.5 text-[10px] font-medium text-[var(--muted-foreground)]"
                >
                  {{ med.form }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Analyses biologie -->
      <section v-else class="space-y-2">
        <h2 class="flex items-center gap-2 px-1 text-base font-bold text-[var(--foreground)]">
          <FlaskConical :size="16" class="text-[var(--primary)]" />
          Analyses prescrites
          <span class="text-sm font-normal text-[var(--muted-foreground)]">
            ({{ (detail.exams || []).length }})
          </span>
        </h2>
        <div
          v-if="!(detail.exams || []).length"
          class="rounded-2xl border border-dashed border-[var(--border)] px-4 py-8 text-center text-sm text-[var(--muted-foreground)]"
        >
          Aucune analyse détectée — ouvrez le PDF.
        </div>
        <ul
          v-else
          class="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-sm divide-y divide-[var(--border)]"
        >
          <li
            v-for="(exam, idx) in detail.exams"
            :key="idx"
            class="flex items-center gap-3 px-4 py-3 text-sm font-medium text-[var(--foreground)]"
          >
            <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--primary)]" />
            {{ exam }}
          </li>
        </ul>
      </section>
    </div>
  </PageShell>
</template>
