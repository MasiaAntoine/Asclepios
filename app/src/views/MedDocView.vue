<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked, type Tokens } from 'marked'
import { useMedications, type MedicationCard } from '@/composables/useMedications'
import { ArrowLeft, BookOpen, ExternalLink, Pill } from '@lucide/vue'
import PdfButton from '@/components/PdfButton.vue'

const route = useRoute()
const router = useRouter()
const { getById, getDoc, load, loading: listLoading, list } = useMedications()

const medId = computed(() => route.params.id as string)
const med = ref<MedicationCard | undefined>()
const doc = ref<string | null>(null)
const docLoading = ref(false)
const docError = ref<string | null>(null)

watch(
  [medId, list],
  async () => {
    if (!list.value.length && !listLoading.value) await load()
    med.value = getById(medId.value)
    doc.value = null
    docError.value = null
    if (!med.value?.doc) return
    docLoading.value = true
    try {
      doc.value = await getDoc(med.value)
    } catch (e) {
      docError.value = e instanceof Error ? e.message : 'Fiche introuvable'
    } finally {
      docLoading.value = false
    }
  },
  { immediate: true },
)

function slugify(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
}

function extractPlainText(token: Tokens.Generic | string): string {
  if (typeof token === 'string') return token
  if ('tokens' in token && Array.isArray(token.tokens)) {
    return token.tokens.map((t) => extractPlainText(t)).join('')
  }
  if ('text' in token && typeof token.text === 'string') return token.text
  return ''
}

const renderedDoc = computed(() => {
  if (!doc.value) return ''
  const usedIds = new Set<string>()
  const renderer = new marked.Renderer()
  renderer.heading = ({ tokens, depth }: Tokens.Heading) => {
    const text = extractPlainText({ tokens } as Tokens.Generic)
    let id = slugify(text) || `h-${usedIds.size}`
    let n = 1
    while (usedIds.has(id)) id = `${slugify(text)}-${n++}`
    usedIds.add(id)
    const inner = marked.Parser.parseInline(tokens)
    return `<h${depth} id="${id}">${inner}</h${depth}>`
  }
  return (marked.parse(doc.value, { renderer, gfm: true }) as string)
    .replace(/<table>/g, '<div class="table-wrap"><table>')
    .replace(/<\/table>/g, '</table></div>')
})

const eventLabels: Record<string, string> = {
  debut: 'Début',
  maintien: 'Maintien',
  diminution: 'Diminution',
  augmentation: 'Augmentation',
  arret: 'Arrêt',
  reprise: 'Reprise',
}
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <div class="border-b border-[var(--border)] bg-[var(--card)] px-8 py-5">
      <div class="flex items-center gap-4">
        <button
          type="button"
          @click="router.push('/meds')"
          class="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border)] text-[var(--muted-foreground)] transition hover:bg-[var(--accent)] hover:text-[var(--foreground)]"
        >
          <ArrowLeft :size="16" />
        </button>
        <div class="min-w-0 flex-1">
          <h1 class="truncate text-lg font-bold text-[var(--foreground)]">
            {{ med?.nom ?? 'Médicament' }}
          </h1>
          <p v-if="med" class="mt-0.5 text-xs capitalize text-[var(--muted-foreground)]">
            {{ med.forme }} · {{ med.moment }}
            <template v-if="med.si_besoin"> · si besoin</template>
          </p>
        </div>
        <PdfButton
          v-if="med"
          generate-endpoint="/pdf/generate/traitements"
          label="Fiche PDF"
        />
        <a
          v-if="med?.source"
          :href="med.source"
          target="_blank"
          rel="noopener noreferrer"
          class="hidden sm:inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs font-medium text-[var(--muted-foreground)] transition hover:bg-[var(--accent)] hover:text-[var(--foreground)]"
        >
          <ExternalLink :size="12" />
          Source officielle
        </a>
      </div>
    </div>

    <div
      v-if="(listLoading || docLoading) && !med"
      class="flex flex-1 items-center justify-center text-sm text-[var(--muted-foreground)]"
    >
      Chargement…
    </div>

    <div
      v-else-if="!med"
      class="flex flex-1 flex-col items-center justify-center gap-4 text-center"
    >
      <div class="rounded-full bg-[var(--muted)] p-5">
        <Pill :size="32" class="text-[var(--muted-foreground)]" />
      </div>
      <p class="text-base font-medium">Médicament introuvable</p>
      <button
        type="button"
        @click="router.push('/meds')"
        class="rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)]"
      >
        Retour
      </button>
    </div>

    <div v-else class="flex-1 overflow-y-auto">
      <div class="mx-auto max-w-3xl space-y-8 px-8 py-8">
        <!-- Summary -->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
            <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
              Dose actuelle
            </p>
            <p class="mt-1 text-xl font-bold">{{ med.actuel?.dose ?? '—' }}</p>
            <p class="text-xs text-[var(--muted-foreground)]">{{ med.actuel?.posologie }}</p>
          </div>
          <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
            <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
              Statut
            </p>
            <p class="mt-2">
              <span
                v-if="med.actif"
                class="rounded-full bg-emerald-50 px-2.5 py-0.5 text-sm font-semibold text-emerald-800"
              >
                En cours
              </span>
              <span
                v-else
                class="rounded-full bg-red-50 px-2.5 py-0.5 text-sm font-semibold text-red-700"
              >
                Arrêté
              </span>
            </p>
            <p class="mt-2 text-xs text-[var(--muted-foreground)]">
              Dernier événement :
              {{ eventLabels[med.actuel?.evenement ?? ''] ?? med.actuel?.evenement }}
              · {{ med.actuel?.date }}
            </p>
          </div>
        </div>

        <!-- Dose history -->
        <div class="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)]">
          <div class="border-b border-[var(--border)] px-5 py-3">
            <h2 class="text-sm font-semibold">Historique des doses</h2>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead class="bg-[var(--secondary)] text-left text-xs uppercase tracking-wider text-[var(--muted-foreground)]">
                <tr>
                  <th class="px-5 py-3 font-medium">Date</th>
                  <th class="px-5 py-3 font-medium">Dose</th>
                  <th class="px-5 py-3 font-medium">Événement</th>
                  <th class="px-5 py-3 font-medium">Note</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(h, i) in [...med.historique].reverse()"
                  :key="h.date + h.dose + i"
                  class="border-t border-[var(--border)]"
                >
                  <td class="px-5 py-2.5">{{ h.date }}</td>
                  <td class="px-5 py-2.5 font-medium">{{ h.dose }}</td>
                  <td class="px-5 py-2.5 capitalize">
                    {{ eventLabels[h.evenement] ?? h.evenement }}
                  </td>
                  <td class="px-5 py-2.5 text-[var(--muted-foreground)] italic">
                    {{ h.note || '—' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Markdown fiche -->
        <div v-if="docLoading" class="py-8 text-center text-sm text-[var(--muted-foreground)]">
          Chargement de la fiche…
        </div>
        <div v-else-if="docError" class="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {{ docError }}
        </div>
        <div v-else-if="doc" class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 sm:p-8">
          <div class="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
            <BookOpen :size="13" />
            Fiche
          </div>
          <article class="prose" v-html="renderedDoc" />
        </div>
        <div
          v-else
          class="rounded-xl border border-dashed border-[var(--border)] px-4 py-8 text-center text-sm text-[var(--muted-foreground)]"
        >
          Pas de fiche documentaire associée
        </div>
      </div>
    </div>
  </div>
</template>
