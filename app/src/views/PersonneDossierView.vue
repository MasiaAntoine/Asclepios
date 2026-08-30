<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import {
  useProfile,
  ageLabel,
  type Animal,
  type Personne,
} from '@/composables/useProfile'
import { dataUrl, fetchText } from '@/lib/dataClient'
import PageShell from '@/components/PageShell.vue'
import {
  ArrowLeft,
  FileText,
  PawPrint,
  Shield,
  User,
  Users,
} from '@lucide/vue'

type PersonneEntry = {
  kind: 'personne' | 'animal'
  role: string
  dossier: string
  displayName: string
  dateNaissance?: string | null
  photo?: string | null
  personneDeConfiance?: boolean
  espece?: string
  race?: string
}

const route = useRoute()
const router = useRouter()
const { profil, load, loading: profilLoading } = useProfile()

const slug = computed(() => String(route.params.slug || '').replace(/\.md$/i, ''))

function matchDossier(file: string | null | undefined): boolean {
  return !!file && file.replace(/\.md$/i, '') === slug.value
}

function findEntry(): PersonneEntry | null {
  const p = profil.value
  if (!p) return null

  const parents: { role: string; person: Personne }[] = [
    { role: 'Père', person: p.parents.pere },
    { role: 'Mère', person: p.parents.mere },
  ]
  for (const { role, person } of parents) {
    if (matchDossier(person.dossier)) {
      return {
        kind: 'personne',
        role,
        dossier: person.dossier!,
        displayName: `${person.prenom} ${person.nom}`.trim(),
        dateNaissance: person.date_naissance,
        photo: person.photo,
      }
    }
  }
  for (const s of p.fratrie) {
    if (matchDossier(s.dossier)) {
      return {
        kind: 'personne',
        role: s.lien || 'Fratrie',
        dossier: s.dossier!,
        displayName: `${s.prenom} ${s.nom}`.trim(),
        dateNaissance: s.date_naissance,
        photo: s.photo,
      }
    }
  }
  for (const e of p.entourage) {
    if (matchDossier(e.dossier)) {
      return {
        kind: 'personne',
        role: e.lien || 'Entourage',
        dossier: e.dossier!,
        displayName: `${e.prenom} ${e.nom}`.trim(),
        dateNaissance: e.date_naissance,
        photo: e.photo,
        personneDeConfiance: e.personne_de_confiance,
      }
    }
  }
  for (const a of p.animaux as Animal[]) {
    if (matchDossier(a.dossier)) {
      return {
        kind: 'animal',
        role: a.espece + (a.race ? ` · ${a.race}` : ''),
        dossier: a.dossier!,
        displayName: a.nom,
        dateNaissance: a.date_naissance,
        photo: a.photo,
        espece: a.espece,
        race: a.race,
      }
    }
  }
  return null
}

const entry = computed(() => findEntry())

const photoSrc = computed(() => {
  const photo = entry.value?.photo
  if (!photo) return null
  if (photo.startsWith('http')) return photo
  return dataUrl(photo)
})

const photoFailed = ref(false)

const markdown = ref('')
const mdLoading = ref(false)
const mdError = ref<string | null>(null)

watch(
  slug,
  async () => {
    markdown.value = ''
    mdError.value = null
    photoFailed.value = false
    if (!slug.value) return
    mdLoading.value = true
    try {
      if (!profil.value) await load()
      const found = findEntry()
      const file = found?.dossier ?? `${slug.value}.md`
      markdown.value = await fetchText(`personnes/${file}`)
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

const displayName = computed(
  () => entry.value?.displayName || slug.value,
)
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
        <div
          class="mt-0.5 h-12 w-12 shrink-0 overflow-hidden rounded-full bg-[var(--secondary)] ring-1 ring-[var(--border)]"
        >
          <img
            v-if="photoSrc && !photoFailed"
            :src="photoSrc"
            :alt="displayName"
            class="h-full w-full object-cover"
            @error="photoFailed = true"
          />
          <div v-else class="flex h-full w-full items-center justify-center">
            <PawPrint
              v-if="entry?.kind === 'animal'"
              :size="18"
              class="text-[var(--primary)]"
            />
            <User v-else :size="18" class="text-[var(--primary)]" />
          </div>
        </div>
        <div class="min-w-0 flex-1">
          <div
            class="mb-1 flex items-center gap-2 text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]"
          >
            <Users :size="12" class="text-[var(--primary)]" />
            Dossier
            {{ entry?.kind === 'animal' ? 'animal' : 'personne' }}
          </div>
          <h1 class="truncate text-2xl font-bold text-[var(--foreground)]">
            {{ displayName }}
          </h1>
          <p
            v-if="entry"
            class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm capitalize text-[var(--muted-foreground)]"
          >
            <span>{{ entry.role }}</span>
            <template v-if="ageLabel(entry.dateNaissance)">
              <span class="text-[var(--border)]">·</span>
              {{ ageLabel(entry.dateNaissance) }}
            </template>
            <span
              v-if="entry.personneDeConfiance"
              class="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium normal-case text-emerald-800"
            >
              <Shield :size="10" />
              Personne de confiance
            </span>
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
        {{ mdError || 'Aucun contenu pour cette personne.' }}
      </p>
      <button
        type="button"
        class="rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)]"
        @click="router.push({ name: 'profile' })"
      >
        Retour au profil
      </button>
    </div>

    <div v-else>
      <article
        class="prose rounded-2xl border border-[var(--border)] bg-[var(--card)] px-6 py-6 sm:px-8 sm:py-8"
        v-html="html"
      />
    </div>
  </PageShell>
</template>
