<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchLabPdfDetail,
  formatLabDate,
  labPdfFileUrl,
  type LabPdfDetail,
} from '@/composables/useLabPdfs'
import { useProfile } from '@/composables/useProfile'
import LabAnalyteRow from '@/components/LabAnalyteRow.vue'
import PageShell from '@/components/PageShell.vue'
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Download,
  Droplets,
  FlaskConical,
  HeartPulse,
  Pill,
} from '@lucide/vue'

const route = useRoute()
const router = useRouter()
const { profil, age } = useProfile()

const detail = ref<LabPdfDetail | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const showAllSummary = ref(false)

const pdfId = computed(() => String(route.params.id || ''))

const sectionIcon = (title: string) => {
  const t = title.toLowerCase()
  if (t.includes('hématolog') || t.includes('hematolog')) return Droplets
  if (t.includes('hémostas') || t.includes('hemostas')) return HeartPulse
  if (t.includes('enzym') || t.includes('biochim') || t.includes('immun')) return FlaskConical
  if (t.includes('thyro') || t.includes('hormon')) return Pill
  return FlaskConical
}

async function load() {
  if (!pdfId.value) return
  loading.value = true
  error.value = null
  detail.value = null
  showAllSummary.value = false
  try {
    detail.value = await fetchLabPdfDetail(pdfId.value)
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

const summaryVisible = computed(() => {
  const all = detail.value?.out_of_range_summary ?? []
  if (showAllSummary.value) return all
  return all.slice(0, 3)
})

function go(id: string | null) {
  if (!id) return
  void router.push(`/prise-de-sang/${encodeURIComponent(id)}`)
}
</script>

<template>
  <PageShell max-width="narrow">
    <template #header>
      <div class="flex items-center gap-3">
        <button
          type="button"
          class="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border)] text-[var(--muted-foreground)] transition hover:bg-[var(--accent)] hover:text-[var(--foreground)]"
          @click="router.push('/prise-de-sang')"
        >
          <ArrowLeft :size="16" />
        </button>
        <div class="min-w-0 flex-1">
          <h1 class="truncate text-lg font-bold text-[var(--foreground)]">
            {{
              detail?.meta.date
                ? `Résultats du ${formatLabDate(detail.meta.date)}`
                : 'Prise de sang'
            }}
          </h1>
          <p v-if="detail" class="truncate text-xs text-[var(--muted-foreground)]">
            {{ detail.meta.lab }}
            <template v-if="detail.meta.dossier"> · Dossier n° {{ detail.meta.dossier }}</template>
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
        <p v-if="profil" class="mt-0.5 text-sm text-[var(--muted-foreground)]">
          {{ profil.date_naissance }} · {{ profil.sexe }}
          <template v-if="age != null"> · {{ age }} ans</template>
        </p>

        <div class="mt-4 flex items-start gap-3 border-t border-[var(--border)] pt-4">
          <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)]">
            <ClipboardList :size="16" class="text-[var(--primary)]" />
          </div>
          <div class="min-w-0">
            <p class="font-semibold text-[var(--foreground)]">
              Résultats du {{ formatLabDate(detail.meta.date) }}
            </p>
            <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">
              {{ detail.meta.lab }}
              <template v-if="detail.meta.dossier"> · Dossier n° {{ detail.meta.dossier }}</template>
            </p>
            <p v-if="detail.meta.prescriber" class="mt-2 text-xs text-[var(--muted-foreground)]">
              Prescrit par {{ detail.meta.prescriber }}
            </p>
            <p v-if="detail.meta.validated_at" class="text-xs text-[var(--muted-foreground)]">
              Validé le {{ detail.meta.validated_at }}
              <template v-if="detail.meta.validated_by"> par {{ detail.meta.validated_by }}</template>
            </p>
            <p v-if="detail.meta.sampled_at" class="text-xs text-[var(--muted-foreground)]">
              Prélèvement du {{ detail.meta.sampled_at }}
            </p>
          </div>
        </div>

        <div class="mt-4 flex flex-wrap gap-2">
          <a
            :href="labPdfFileUrl(detail.id)"
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

      <!-- Summary -->
      <section
        v-if="detail.out_of_range_summary.length"
        class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 shadow-sm"
      >
        <h2 class="mb-3 flex items-center gap-2 text-base font-bold text-[var(--foreground)]">
          <ClipboardList :size="16" class="text-[var(--primary)]" />
          Résumé des résultats
        </h2>
        <ul class="space-y-3">
          <li
            v-for="(line, i) in summaryVisible"
            :key="i"
            class="border-l-4 border-[#f2cc8f] pl-3"
          >
            <p class="flex items-start gap-2 text-sm font-semibold text-[var(--foreground)]">
              <span class="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-[#e07a5f]" />
              {{ line }}
            </p>
          </li>
        </ul>
        <button
          v-if="detail.out_of_range_summary.length > 3"
          type="button"
          class="mt-4 inline-flex items-center gap-1 text-sm font-medium text-[var(--primary)]"
          @click="showAllSummary = !showAllSummary"
        >
          {{ showAllSummary ? 'Voir moins' : 'Voir plus' }}
        </button>
      </section>

      <p
        v-if="!detail.parsable"
        class="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
      >
        Parsing structuré limité pour ce laboratoire. Consultez le PDF source.
      </p>

      <!-- Sections -->
      <section v-for="sec in detail.sections" :key="sec.title" class="space-y-2">
        <h2 class="flex items-center gap-2 px-1 text-base font-bold text-[var(--foreground)]">
          <component :is="sectionIcon(sec.title)" :size="16" class="text-[var(--primary)]" />
          {{ sec.title }}
        </h2>
        <div class="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-sm">
          <LabAnalyteRow v-for="(item, idx) in sec.items" :key="`${sec.title}-${idx}`" :item="item" />
        </div>
      </section>
    </div>
  </PageShell>
</template>
