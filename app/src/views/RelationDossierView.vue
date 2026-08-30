<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import {
  useProfile,
  type RelationPassee,
  type RelationSuite,
} from '@/composables/useProfile'
import { fetchText } from '@/lib/dataClient'
import PageShell from '@/components/PageShell.vue'
import { ArrowLeft, Calendar, FileText, Heart, User } from '@lucide/vue'

const route = useRoute()
const router = useRouter()
const { profil, load, loading: profilLoading } = useProfile()

const slug = computed(() => String(route.params.slug || '').replace(/\.md$/i, ''))

const LIEN_LABELS: Record<string, string> = {
  plan_cul: 'relation sexuelle ponctuelle', // legacy
  sexuelle_ponctuelle: 'relation sexuelle ponctuelle',
  tromperie: 'tromperie',
  revue: 'recontact',
}

function suiteLabel(a: RelationSuite): string {
  const name = a.prenom
    ? a.nom
      ? `${a.prenom} ${a.nom}`
      : a.prenom
    : a.note || 'prénom inconnu'
  const lien = LIEN_LABELS[a.lien] || a.lien
  const extra = a.prenom && a.note ? ` (${a.note})` : ''
  return `${name} (${lien})${extra}`
}

function parseFrDate(value: string | null | undefined): Date | null {
  if (!value) return null
  const m = value.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
  if (!m) return null
  const d = new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1]))
  return Number.isNaN(d.getTime()) ? null : d
}

function relationDuree(r: RelationPassee): string | null {
  const from = parseFrDate(r.debut)
  const to = parseFrDate(r.fin)
  if (from && to && to >= from) {
    let months =
      (to.getFullYear() - from.getFullYear()) * 12 +
      (to.getMonth() - from.getMonth())
    if (to.getDate() - from.getDate() < 0) months -= 1
    const endProbe = new Date(from)
    endProbe.setMonth(endProbe.getMonth() + months)
    const daysLeft = Math.round((to.getTime() - endProbe.getTime()) / 86_400_000)
    if (daysLeft >= 25) months += 1
    if (months <= 0) {
      const days = Math.round((to.getTime() - from.getTime()) / 86_400_000) + 1
      if (days < 14) return `${days} jour${days > 1 ? 's' : ''}`
      return `${Math.max(1, Math.round(days / 7))} semaine${days >= 14 ? 's' : ''}`
    }
    if (months < 12) return `${months} mois`
    const years = Math.floor(months / 12)
    const rem = months % 12
    if (rem === 0) return `${years} an${years > 1 ? 's' : ''}`
    return `${years} an${years > 1 ? 's' : ''} ${rem} mois`
  }
  return r.duree || null
}

function formatAgeParts(p: { years: number; months: number }): string {
  const bits: string[] = []
  if (p.years > 0) bits.push(`${p.years} an${p.years > 1 ? 's' : ''}`)
  if (p.months > 0 || p.years === 0) bits.push(`${p.months} mois`)
  return bits.join(' ')
}

function ageAtDate(birth: Date, at: Date): { years: number; months: number } | null {
  let years = at.getFullYear() - birth.getFullYear()
  let months = at.getMonth() - birth.getMonth()
  if (at.getDate() < birth.getDate()) months -= 1
  if (months < 0) {
    years -= 1
    months += 12
  }
  if (years < 0) return null
  return { years, months }
}

const relationAgeLabel = computed(() => {
  const r = relation.value
  const birth = parseFrDate(profil.value?.date_naissance)
  if (!r || !birth) return null
  const from = parseFrDate(r.debut)
  const to = parseFrDate(r.fin)
  if (from && to) {
    const a = ageAtDate(birth, from)
    const b = ageAtDate(birth, to)
    if (!a || !b) return null
    const fromS = formatAgeParts(a)
    const toS = formatAgeParts(b)
    return fromS === toS ? fromS : `${fromS} → ${toS}`
  }
  if (from) {
    const a = ageAtDate(birth, from)
    return a ? formatAgeParts(a) : null
  }
  if (to) {
    const b = ageAtDate(birth, to)
    return b ? formatAgeParts(b) : null
  }
  return null
})

const relation = computed(() => {
  const list = profil.value?.relations_passees ?? []
  return (
    list.find((r) => r.dossier && r.dossier.replace(/\.md$/i, '') === slug.value) ??
    null
  )
})

const displayName = computed(() => {
  if (!relation.value) return slug.value
  return relation.value.nom
    ? `${relation.value.prenom} ${relation.value.nom}`
    : relation.value.prenom
})

const markdown = ref('')
const mdLoading = ref(false)
const mdError = ref<string | null>(null)

watch(
  slug,
  async () => {
    markdown.value = ''
    mdError.value = null
    if (!slug.value) return
    mdLoading.value = true
    try {
      if (!profil.value) await load()
      const file =
        profil.value?.relations_passees?.find(
          (r) => r.dossier && r.dossier.replace(/\.md$/i, '') === slug.value,
        )?.dossier ?? `${slug.value}.md`
      markdown.value = await fetchText(`relations/${file}`)
    } catch (e) {
      mdError.value = e instanceof Error ? e.message : 'Dossier introuvable'
    } finally {
      mdLoading.value = false
    }
  },
  { immediate: true },
)

const html = computed(() => {
  if (!markdown.value) return ''
  return marked.parse(markdown.value, { gfm: true, breaks: true }) as string
})
</script>

<template>
  <PageShell max-width="md">
    <template #header>
      <div class="flex items-start gap-4">
        <button
          type="button"
          class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-[var(--border)] text-[var(--muted-foreground)] transition hover:bg-[var(--accent)] hover:text-[var(--foreground)]"
          aria-label="Retour au profil"
          @click="router.push({ name: 'profile' })"
        >
          <ArrowLeft :size="16" />
        </button>
        <div class="min-w-0 flex-1">
          <div
            class="mb-1 flex items-center gap-2 text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]"
          >
            <Heart :size="12" class="text-[var(--primary)]" />
            Dossier relation
          </div>
          <h1 class="truncate text-2xl font-bold text-[var(--foreground)]">
            {{ displayName }}
          </h1>
          <p
            v-if="relation"
            class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-[var(--muted-foreground)]"
          >
            <span
              v-if="relation.debut || relation.fin"
              class="inline-flex items-center gap-1"
            >
              <Calendar :size="13" />
              {{ relation.debut || '?' }} → {{ relation.fin || '?' }}
            </span>
            <template v-if="relationDuree(relation)">
              <span class="text-[var(--border)]">·</span>
              {{ relationDuree(relation) }}
            </template>
            <template v-if="relationAgeLabel">
              <span class="text-[var(--border)]">·</span>
              ton âge {{ relationAgeLabel }}
            </template>
            <template v-if="relation.note">
              <span class="text-[var(--border)]">·</span>
              {{ relation.note }}
            </template>
          </p>
        </div>
      </div>
    </template>

    <div
      v-if="profilLoading || mdLoading"
      class="py-20 text-center text-sm text-[var(--muted-foreground)]"
    >
      Chargement du dossier…
    </div>

    <div
      v-else-if="mdError || !markdown"
      class="flex flex-col items-center justify-center gap-4 py-20 text-center"
    >
      <div class="rounded-full bg-[var(--secondary)] p-5">
        <FileText :size="28" class="text-[var(--muted-foreground)]" />
      </div>
      <p class="text-base font-medium">Dossier introuvable</p>
      <p class="max-w-sm text-sm text-[var(--muted-foreground)]">
        {{ mdError || 'Aucun contenu pour cette relation.' }}
      </p>
      <button
        type="button"
        class="rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)]"
        @click="router.push({ name: 'profile' })"
      >
        Retour au profil
      </button>
    </div>

    <div v-else class="space-y-6">
      <div
        v-if="relation?.apres?.length"
        class="rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3"
      >
        <p
          class="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)]"
        >
          Après la relation
        </p>
        <ul class="flex flex-wrap gap-2">
          <li
            v-for="(a, i) in relation.apres"
            :key="`apres-${i}`"
            class="inline-flex items-center gap-1.5 rounded-full bg-[var(--secondary)] px-2.5 py-1 text-xs text-[var(--secondary-foreground)]"
          >
            <User :size="11" />
            {{ suiteLabel(a) }}
          </li>
        </ul>
      </div>

      <article
        class="prose rounded-2xl border border-[var(--border)] bg-[var(--card)] px-6 py-6 sm:px-8 sm:py-8"
        v-html="html"
      />
    </div>
  </PageShell>
</template>
