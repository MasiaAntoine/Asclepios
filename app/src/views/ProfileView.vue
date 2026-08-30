<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useProfile, ageLabel } from '@/composables/useProfile'
import type { RelationSuite } from '@/composables/useProfile'
import {
  Cigarette,
  CreditCard,
  ExternalLink,
  FileText,
  Heart,
  PawPrint,
  Pill,
  Ruler,
  Scale,
  Shield,
  User,
  Users,
} from '@lucide/vue'
import EditProfileDialog from '@/components/EditProfileDialog.vue'
import PageShell from '@/components/PageShell.vue'
import { dataUrl } from '@/lib/dataClient'

const {
  profil,
  photoUrl,
  age,
  dernierPoids,
  imc,
  imcLabel,
  traitementsActifs,
  traitementsArretes,
  traitementsMisAJour,
  loading,
  error,
  reload,
} = useProfile()

async function onProfileSaved() {
  await reload()
}

const photoFailed = ref(false)

const fullName = computed(() =>
  profil.value ? `${profil.value.prenom} ${profil.value.nom}` : '',
)

const initials = computed(() => {
  if (!profil.value) return '?'
  return `${profil.value.prenom[0] ?? ''}${profil.value.nom[0] ?? ''}`.toUpperCase()
})

/** Parse JJ/MM/AAAA → Date locale (début de journée). */
function parseFrDate(value: string | null | undefined): Date | null {
  if (!value) return null
  const m = value.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
  if (!m) return null
  const d = new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1]))
  return Number.isNaN(d.getTime()) ? null : d
}

/** Durée calculée depuis debut/fin (prioritaire sur le champ duree saisi). */
function relationDuree(r: {
  debut?: string | null
  fin?: string | null
  duree?: string | null
}): string | null {
  const from = parseFrDate(r.debut)
  const to = parseFrDate(r.fin)
  if (from && to && to >= from) {
    let months =
      (to.getFullYear() - from.getFullYear()) * 12 +
      (to.getMonth() - from.getMonth())
    const dayDiff = to.getDate() - from.getDate()
    if (dayDiff < 0) months -= 1
    // Ajuste si quasi-mois complet (ex. 15/02 → 14/08 = 6 mois)
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

/** Âge pendant la relation (à partir de ta date de naissance). */
function relationAgeLabel(r: {
  debut?: string | null
  fin?: string | null
}): string | null {
  const birth = parseFrDate(profil.value?.date_naissance)
  if (!birth) return null
  const from = parseFrDate(r.debut)
  const to = parseFrDate(r.fin)
  if (from && to) {
    const a = ageAtDate(birth, from)
    const b = ageAtDate(birth, to)
    if (!a || !b) return null
    const fromS = formatAgeParts(a)
    const toS = formatAgeParts(b)
    if (fromS === toS) return fromS
    return `${fromS} → ${toS}`
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
}

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

function dossierSlug(file: string): string {
  return file.replace(/\.md$/i, '')
}

const mutuelleDocUrl = computed(() => {
  const doc = profil.value?.mutuelle?.document
  return doc ? dataUrl(doc) : null
})

const mutuelleNoticeUrl = computed(() => {
  const doc = profil.value?.mutuelle?.notice_md
  return doc ? dataUrl(doc) : null
})

const mutuelleContratUrl = computed(() => {
  const doc = profil.value?.mutuelle?.contrat_pdf
  return doc ? dataUrl(doc) : null
})

const garantieLabels: Record<string, string> = {
  pharmacie: 'Pharmacie',
  laboratoire_radiologie: 'Labo / Radiologie',
  transport: 'Transport',
  auxiliaires_medicaux: 'Auxiliaires médicaux',
  soins_dentaires: 'Soins dentaires',
  soins_externes: 'Soins externes',
  consultations: 'Consultations',
  centre_de_sante: 'Centre de santé',
  hospitalisation: 'Hospitalisation',
  audioprotheses_optique_protheses_dentaires: 'Audio / Optique / Prothèses dentaires',
}

function eventLabel(e: string) {
  const map: Record<string, string> = {
    debut: 'Début',
    maintien: 'Maintien',
    diminution: 'Diminution',
    augmentation: 'Augmentation',
    arret: 'Arrêt',
    reprise: 'Reprise',
  }
  return map[e] ?? e
}

function eventClass(e: string) {
  if (e === 'arret') return 'bg-red-50 text-red-700'
  if (e === 'augmentation' || e === 'reprise') return 'bg-amber-50 text-amber-800'
  if (e === 'diminution') return 'bg-sky-50 text-sky-800'
  return 'bg-[var(--secondary)] text-[var(--secondary-foreground)]'
}
</script>

<template>
  <PageShell
    title="Profil patient"
    description="Identité, constantes et traitements en cours"
    max-width="lg"
  >
    <template #actions>
      <EditProfileDialog v-if="profil" :profil="profil" @saved="onProfileSaved" />
    </template>

    <div v-if="error" class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {{ error }}
    </div>
    <div v-else-if="loading && !profil" class="py-24 text-center text-sm text-[var(--muted-foreground)]">
      Chargement du profil…
    </div>
    <div v-else-if="profil" class="space-y-8">
        <!-- Hero identity -->
        <section class="flex flex-col gap-6 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 sm:flex-row sm:items-center">
          <div class="relative h-28 w-28 shrink-0 overflow-hidden rounded-2xl bg-[var(--accent)] shadow-sm ring-1 ring-[var(--border)]">
            <img
              v-if="!photoFailed"
              :src="photoUrl"
              :alt="fullName"
              class="h-full w-full object-cover"
              @error="photoFailed = true"
            />
            <div
              v-else
              class="flex h-full w-full items-center justify-center text-2xl font-bold text-[var(--primary)]"
            >
              {{ initials }}
            </div>
          </div>
          <div class="min-w-0 flex-1">
            <h2 class="text-2xl font-bold tracking-tight text-[var(--foreground)]">
              {{ fullName }}
            </h2>
            <p class="mt-1 text-sm text-[var(--muted-foreground)] capitalize">
              {{ profil.sexe }}
              <span class="mx-1.5 text-[var(--border)]">·</span>
              Né le {{ profil.date_naissance }}
              <template v-if="age !== null">
                <span class="mx-1.5 text-[var(--border)]">·</span>
                {{ age }} ans
              </template>
            </p>

            <div class="mt-4 flex flex-wrap gap-2">
              <span class="inline-flex items-center gap-1.5 rounded-full bg-[var(--secondary)] px-3 py-1 text-xs font-medium text-[var(--secondary-foreground)]">
                <Ruler :size="12" />
                {{ profil.taille_cm }} cm
              </span>
              <span
                v-if="dernierPoids"
                class="inline-flex items-center gap-1.5 rounded-full bg-[var(--secondary)] px-3 py-1 text-xs font-medium text-[var(--secondary-foreground)]"
              >
                <Scale :size="12" />
                {{ dernierPoids.poids_kg }} kg
                <span class="text-[var(--muted-foreground)]">({{ dernierPoids.date }})</span>
              </span>
              <span
                v-if="imc !== null"
                class="inline-flex items-center gap-1.5 rounded-full bg-[var(--accent)] px-3 py-1 text-xs font-medium text-[var(--accent-foreground)]"
              >
                IMC {{ imc.toFixed(1) }}
                <span class="opacity-70">— {{ imcLabel }}</span>
              </span>
              <span
                v-if="profil.securite_sociale?.nir"
                class="inline-flex items-center gap-1.5 rounded-full bg-[var(--secondary)] px-3 py-1 font-mono text-xs font-medium text-[var(--secondary-foreground)]"
              >
                <CreditCard :size="12" />
                {{ profil.securite_sociale.nir }}
              </span>
            </div>
          </div>
        </section>

        <!-- Sécurité sociale / Carte Vitale -->
        <section
          v-if="profil.securite_sociale"
          class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6"
        >
          <h3 class="mb-4 flex items-center gap-2 text-lg font-semibold text-[var(--foreground)]">
            <CreditCard :size="18" class="text-[var(--primary)]" />
            Sécurité sociale
          </h3>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <p class="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
                N° de sécurité sociale (NIR)
              </p>
              <p class="mt-1 font-mono text-lg font-semibold tracking-wide text-[var(--foreground)]">
                {{ profil.securite_sociale.nir }}
              </p>
            </div>
            <div v-if="profil.securite_sociale.carte_vitale_emise_le">
              <p class="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
                Carte Vitale émise le
              </p>
              <p class="mt-1 text-lg font-semibold text-[var(--foreground)]">
                {{ profil.securite_sociale.carte_vitale_emise_le }}
              </p>
            </div>
          </div>
          <div
            v-if="profil.securite_sociale.carte_vitale_verso"
            class="mt-5 rounded-xl border border-[var(--border)] bg-[var(--accent)]/40 p-4"
          >
            <p class="mb-3 text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
              Verso carte Vitale
            </p>
            <dl class="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
              <div>
                <dt class="text-xs text-[var(--muted-foreground)]">Période</dt>
                <dd class="font-medium text-[var(--foreground)]">
                  {{ profil.securite_sociale.carte_vitale_verso.periode }}
                  <span class="ml-1 text-[var(--muted-foreground)]">
                    {{ profil.securite_sociale.carte_vitale_verso.type }}
                  </span>
                </dd>
              </div>
              <div>
                <dt class="text-xs text-[var(--muted-foreground)]">Fabricant</dt>
                <dd class="font-medium text-[var(--foreground)]">
                  {{ profil.securite_sociale.carte_vitale_verso.fabricant }}
                </dd>
              </div>
              <div class="col-span-2">
                <dt class="text-xs text-[var(--muted-foreground)]">N° / indice</dt>
                <dd class="font-mono font-medium text-[var(--foreground)]">
                  {{ profil.securite_sociale.carte_vitale_verso.numero }}
                  <template v-if="profil.securite_sociale.carte_vitale_verso.indice">
                    {{ profil.securite_sociale.carte_vitale_verso.indice }}
                  </template>
                </dd>
              </div>
            </dl>
          </div>
        </section>

        <!-- Mutuelle -->
        <section
          v-if="profil.mutuelle"
          class="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6"
        >
          <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
            <h3 class="flex items-center gap-2 text-lg font-semibold text-[var(--foreground)]">
              <Shield :size="18" class="text-[var(--primary)]" />
              Mutuelle
            </h3>
            <div class="flex flex-wrap gap-2">
              <a
                v-if="mutuelleNoticeUrl"
                :href="mutuelleNoticeUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--primary)]/30 bg-[var(--primary)]/10 px-3 py-1.5 text-xs font-medium text-[var(--primary)] transition hover:bg-[var(--primary)]/20"
              >
                <ExternalLink :size="12" />
                Notice .md
              </a>
              <a
                v-if="mutuelleContratUrl"
                :href="mutuelleContratUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs font-medium text-[var(--muted-foreground)] transition hover:bg-[var(--accent)] hover:text-[var(--foreground)]"
              >
                <ExternalLink :size="12" />
                Contrat PDF
              </a>
              <a
                v-if="mutuelleDocUrl"
                :href="mutuelleDocUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs font-medium text-[var(--muted-foreground)] transition hover:bg-[var(--accent)] hover:text-[var(--foreground)]"
              >
                <ExternalLink :size="12" />
                Carte PDF
              </a>
            </div>
          </div>

          <div class="mb-4">
            <p class="text-xl font-bold text-[var(--foreground)]">
              {{ profil.mutuelle.organisme }}
              <span
                v-if="profil.mutuelle.unite_gestion"
                class="ml-2 text-sm font-medium text-[var(--muted-foreground)]"
              >
                {{ profil.mutuelle.unite_gestion }}
              </span>
            </p>
            <p
              v-if="profil.mutuelle.adresse"
              class="mt-1 whitespace-pre-line text-sm text-[var(--muted-foreground)]"
            >
              {{ profil.mutuelle.adresse }}
            </p>
            <p
              v-if="profil.mutuelle.validite"
              class="mt-2 text-sm text-[var(--foreground)]"
            >
              Validité
              <span class="font-medium">
                du {{ profil.mutuelle.validite.debut }}
                au {{ profil.mutuelle.validite.fin }}
              </span>
            </p>
          </div>

          <dl class="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3 lg:grid-cols-4">
            <div v-if="profil.mutuelle.numero_amc">
              <dt class="text-xs text-[var(--muted-foreground)]">N° AMC</dt>
              <dd class="font-mono font-medium text-[var(--foreground)]">
                {{ profil.mutuelle.numero_amc }}
              </dd>
            </div>
            <div v-if="profil.mutuelle.numero_adherent">
              <dt class="text-xs text-[var(--muted-foreground)]">N° adhérent</dt>
              <dd class="font-mono font-medium text-[var(--foreground)]">
                {{ profil.mutuelle.numero_adherent }}
              </dd>
            </div>
            <div v-if="profil.mutuelle.numero_teletransmission">
              <dt class="text-xs text-[var(--muted-foreground)]">N° télétransmission</dt>
              <dd class="font-mono font-medium text-[var(--foreground)]">
                {{ profil.mutuelle.numero_teletransmission }}
              </dd>
            </div>
            <div v-if="profil.mutuelle.type_convention || profil.mutuelle.roc">
              <dt class="text-xs text-[var(--muted-foreground)]">Type conv. / ROC</dt>
              <dd class="font-medium text-[var(--foreground)]">
                {{ profil.mutuelle.type_convention || '—' }}
                <span class="text-[var(--muted-foreground)]"> / </span>
                {{ profil.mutuelle.roc || '—' }}
              </dd>
            </div>
            <div v-if="profil.mutuelle.reseau_tiers_payant">
              <dt class="text-xs text-[var(--muted-foreground)]">Tiers payant</dt>
              <dd class="font-medium text-[var(--foreground)]">
                {{ profil.mutuelle.reseau_tiers_payant }}
              </dd>
            </div>
            <div v-if="profil.mutuelle.carte_imprimee_le">
              <dt class="text-xs text-[var(--muted-foreground)]">Carte imprimée le</dt>
              <dd class="font-medium text-[var(--foreground)]">
                {{ profil.mutuelle.carte_imprimee_le }}
              </dd>
            </div>
          </dl>

          <div
            v-if="profil.mutuelle.contact"
            class="mt-5 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2"
          >
            <p v-if="profil.mutuelle.contact.telephone">
              <span class="text-[var(--muted-foreground)]">Tél. Henner :</span>
              {{ profil.mutuelle.contact.telephone }}
            </p>
            <p v-if="profil.mutuelle.contact.email">
              <span class="text-[var(--muted-foreground)]">Email :</span>
              <a
                :href="`mailto:${profil.mutuelle.contact.email}`"
                class="text-[var(--primary)] hover:underline"
              >{{ profil.mutuelle.contact.email }}</a>
            </p>
            <p v-if="profil.mutuelle.contact.viamedis_tel">
              <span class="text-[var(--muted-foreground)]">Tél. Viamedis :</span>
              {{ profil.mutuelle.contact.viamedis_tel }}
            </p>
            <p v-if="profil.mutuelle.contact.site">
              <a
                :href="profil.mutuelle.contact.site"
                target="_blank"
                rel="noopener noreferrer"
                class="text-[var(--primary)] hover:underline"
              >{{ profil.mutuelle.contact.site.replace(/^https?:\/\//, '') }}</a>
            </p>
          </div>

          <div
            v-if="profil.mutuelle.garanties_tiers_payant"
            class="mt-5 rounded-xl border border-[var(--border)] bg-[var(--accent)]/40 p-4"
          >
            <p class="mb-3 text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
              Garanties tiers payant
            </p>
            <dl class="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
              <div
                v-for="(valeur, cle) in profil.mutuelle.garanties_tiers_payant"
                :key="cle"
                class="flex justify-between gap-3 border-b border-[var(--border)]/50 pb-1.5 last:border-0"
              >
                <dt class="text-[var(--muted-foreground)]">
                  {{ garantieLabels[cle] ?? cle }}
                </dt>
                <dd class="text-right font-medium text-[var(--foreground)]">{{ valeur }}</dd>
              </div>
            </dl>
          </div>
        </section>

        <!-- Stats row -->
        <section class="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
            <div class="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--accent)]">
              <Scale :size="18" class="text-[var(--primary)]" />
            </div>
            <p class="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Poids</p>
            <p class="mt-1 text-2xl font-bold text-[var(--foreground)]">
              {{ dernierPoids ? `${dernierPoids.poids_kg} kg` : '—' }}
            </p>
            <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">
              {{ dernierPoids ? `Mesuré le ${dernierPoids.date}` : 'Aucune mesure' }}
            </p>
          </div>

          <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
            <div class="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--accent)]">
              <Ruler :size="18" class="text-[var(--primary)]" />
            </div>
            <p class="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Taille</p>
            <p class="mt-1 text-2xl font-bold text-[var(--foreground)]">{{ profil.taille_cm }} cm</p>
            <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">
              IMC {{ imc !== null ? imc.toFixed(1) : '—' }}
            </p>
          </div>

          <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
            <div class="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--accent)]">
              <Cigarette :size="18" class="text-[var(--primary)]" />
            </div>
            <p class="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Tabac</p>
            <p class="mt-1 text-lg font-bold capitalize text-[var(--foreground)]">{{ profil.tabac.type }}</p>
            <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">
              Depuis {{ profil.tabac.debut }}
              <template v-if="profil.tabac.nicotine_mg_ml">
                · {{ profil.tabac.nicotine_mg_ml }} mg/ml
              </template>
            </p>
          </div>
        </section>

        <!-- Traitements actifs -->
        <section>
          <div class="mb-4 flex items-end justify-between gap-4">
            <div>
              <h3 class="flex items-center gap-2 text-lg font-semibold text-[var(--foreground)]">
                <Pill :size="18" class="text-[var(--primary)]" />
                Traitements en cours
              </h3>
              <p class="mt-0.5 text-xs text-[var(--muted-foreground)]">
                Mis à jour le {{ traitementsMisAJour }}
              </p>
            </div>
          </div>

          <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div
              v-for="t in traitementsActifs"
              :key="t.id"
              class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5"
            >
              <div class="flex items-start justify-between gap-3">
                <div>
                  <h4 class="font-semibold text-[var(--foreground)]">{{ t.nom }}</h4>
                  <p class="mt-0.5 text-xs capitalize text-[var(--muted-foreground)]">
                    {{ t.forme }} · {{ t.moment }}
                    <template v-if="t.si_besoin"> · si besoin</template>
                  </p>
                </div>
                <span
                  v-if="t.si_besoin"
                  class="shrink-0 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-800"
                >
                  Si besoin
                </span>
                <span
                  v-else
                  class="shrink-0 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-800"
                >
                  Quotidien
                </span>
              </div>

              <div class="mt-4 rounded-lg bg-[var(--muted)] px-3 py-2.5">
                <p class="text-sm font-semibold text-[var(--foreground)]">{{ t.actuel.dose }}</p>
                <p class="text-xs text-[var(--muted-foreground)]">{{ t.actuel.posologie }}</p>
              </div>

              <div class="mt-3 flex flex-wrap items-center gap-2 text-xs text-[var(--muted-foreground)]">
                <span :class="['rounded-full px-2 py-0.5 font-medium', eventClass(t.actuel.evenement)]">
                  {{ eventLabel(t.actuel.evenement) }}
                </span>
                <span>depuis {{ t.actuel.date }}</span>
                <span v-if="t.actuel.note" class="italic">— {{ t.actuel.note }}</span>
              </div>
            </div>
          </div>

          <div v-if="!traitementsActifs.length" class="rounded-xl border border-dashed border-[var(--border)] p-8 text-center text-sm text-[var(--muted-foreground)]">
            Aucun traitement actif
          </div>
        </section>

        <!-- Traitements arrêtés -->
        <section v-if="traitementsArretes.length">
          <h3 class="mb-4 text-sm font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
            Traitements arrêtés
          </h3>
          <div class="space-y-2">
            <div
              v-for="t in traitementsArretes"
              :key="t.id"
              class="flex items-center justify-between gap-4 rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3 opacity-70"
            >
              <div>
                <p class="text-sm font-medium text-[var(--foreground)]">{{ t.nom }}</p>
                <p class="text-xs text-[var(--muted-foreground)]">
                  Arrêté le {{ t.actuel?.date }}
                  <template v-if="t.actuel?.note"> — {{ t.actuel.note }}</template>
                </p>
              </div>
              <span class="rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-700">
                Arrêt
              </span>
            </div>
          </div>
        </section>

        <!-- Famille & entourage -->
        <section class="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <!-- Parents & fratrie -->
          <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
            <h3 class="mb-4 flex items-center gap-2 text-sm font-semibold text-[var(--foreground)]">
              <Users :size="16" class="text-[var(--primary)]" />
              Famille
            </h3>
            <ul class="space-y-3">
              <li class="flex items-start gap-3">
                <div class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--secondary)]">
                  <User :size="14" class="text-[var(--primary)]" />
                </div>
                <div>
                  <p class="text-sm font-medium">{{ profil.parents.pere.prenom }} {{ profil.parents.pere.nom }}</p>
                  <p class="text-xs text-[var(--muted-foreground)]">
                    Père
                    <template v-if="ageLabel(profil.parents.pere.date_naissance)">
                      · {{ ageLabel(profil.parents.pere.date_naissance) }}
                    </template>
                  </p>
                </div>
              </li>
              <li class="flex items-start gap-3">
                <div class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--secondary)]">
                  <User :size="14" class="text-[var(--primary)]" />
                </div>
                <div>
                  <p class="text-sm font-medium">{{ profil.parents.mere.prenom }} {{ profil.parents.mere.nom }}</p>
                  <p class="text-xs text-[var(--muted-foreground)]">
                    Mère
                    <template v-if="ageLabel(profil.parents.mere.date_naissance)">
                      · {{ ageLabel(profil.parents.mere.date_naissance) }}
                    </template>
                  </p>
                </div>
              </li>
              <li
                v-for="(s, i) in profil.fratrie"
                :key="`fratrie-${i}`"
                class="flex items-start gap-3"
              >
                <div class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--secondary)]">
                  <User :size="14" class="text-[var(--primary)]" />
                </div>
                <div>
                  <p class="text-sm font-medium">{{ s.prenom }} {{ s.nom }}</p>
                  <p class="text-xs capitalize text-[var(--muted-foreground)]">
                    {{ s.lien }}
                    <template v-if="ageLabel(s.date_naissance)">
                      · {{ ageLabel(s.date_naissance) }}
                    </template>
                  </p>
                </div>
              </li>
            </ul>
          </div>

          <!-- Entourage + animaux -->
          <div class="space-y-6">
            <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
              <h3 class="mb-4 flex items-center gap-2 text-sm font-semibold text-[var(--foreground)]">
                <Heart :size="16" class="text-[var(--primary)]" />
                Entourage
              </h3>
              <ul class="space-y-3">
                <li
                  v-for="(p, i) in profil.entourage"
                  :key="`entourage-${i}`"
                  class="flex items-start gap-3"
                >
                  <div class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--secondary)]">
                    <User :size="14" class="text-[var(--primary)]" />
                  </div>
                  <div class="min-w-0 flex-1">
                    <div class="flex flex-wrap items-center gap-2">
                      <p class="text-sm font-medium">{{ p.prenom }} {{ p.nom }}</p>
                      <span
                        v-if="p.personne_de_confiance"
                        class="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-800"
                      >
                        <Shield :size="10" />
                        Personne de confiance
                      </span>
                    </div>
                    <p class="text-xs capitalize text-[var(--muted-foreground)]">
                      {{ p.lien }}
                      <template v-if="ageLabel(p.date_naissance)">
                        · {{ ageLabel(p.date_naissance) }}
                      </template>
                    </p>
                  </div>
                </li>
              </ul>
            </div>

            <div v-if="profil.animaux.length" class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
              <h3 class="mb-4 flex items-center gap-2 text-sm font-semibold text-[var(--foreground)]">
                <PawPrint :size="16" class="text-[var(--primary)]" />
                Animaux
              </h3>
              <ul class="space-y-3">
                <li
                  v-for="(a, i) in profil.animaux"
                  :key="`animal-${i}`"
                  class="flex items-start gap-3"
                >
                  <div class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--secondary)]">
                    <PawPrint :size="14" class="text-[var(--primary)]" />
                  </div>
                  <div>
                    <p class="text-sm font-medium">{{ a.nom }}</p>
                    <p class="text-xs capitalize text-[var(--muted-foreground)]">
                      {{ a.espece }}{{ a.race ? ` · ${a.race}` : '' }}
                      <template v-if="ageLabel(a.date_naissance)">
                        · {{ ageLabel(a.date_naissance) }}
                      </template>
                    </p>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </section>

        <!-- Relations passées (contexte personnel / patterns) -->
        <section
          v-if="profil.vie_amoureuse || profil.relations_passees?.length"
          class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5"
        >
          <h3 class="mb-1 flex items-center gap-2 text-sm font-semibold text-[var(--foreground)]">
            <Heart :size="16" class="text-[var(--primary)]" />
            Relations passées
          </h3>
          <p class="mb-4 text-xs text-[var(--muted-foreground)]">
            Contexte personnel pour repérer des patterns — pas un showcase.
          </p>
          <p
            v-if="profil.vie_amoureuse?.note"
            class="mb-4 rounded-lg border border-[var(--border)] bg-[var(--accent)]/40 px-3 py-2.5 text-sm leading-relaxed text-[var(--foreground)]"
          >
            {{ profil.vie_amoureuse.note }}
          </p>
          <div
            v-if="profil.vie_amoureuse?.estimation_totale || profil.vie_amoureuse?.premiere_vers"
            class="mb-4 flex flex-wrap gap-2"
          >
            <span
              v-if="profil.vie_amoureuse.premiere_vers"
              class="rounded-full bg-[var(--secondary)] px-2.5 py-0.5 text-[10px] font-medium text-[var(--secondary-foreground)]"
            >
              Première vers {{ profil.vie_amoureuse.premiere_vers }}
            </span>
            <span
              v-if="profil.vie_amoureuse.estimation_totale"
              class="rounded-full bg-[var(--secondary)] px-2.5 py-0.5 text-[10px] font-medium text-[var(--secondary-foreground)]"
            >
              ~{{ profil.vie_amoureuse.estimation_totale }} au total
            </span>
          </div>
          <ul v-if="profil.relations_passees?.length" class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <li
              v-for="(r, i) in profil.relations_passees"
              :key="`rel-${i}`"
              class="flex items-start gap-3 rounded-lg bg-[var(--accent)]/30 px-3 py-2.5"
            >
              <div class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--secondary)]">
                <User :size="14" class="text-[var(--primary)]" />
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex items-start justify-between gap-2">
                  <p class="text-sm font-medium text-[var(--foreground)]">
                    {{ r.nom ? `${r.prenom} ${r.nom}` : r.prenom }}
                  </p>
                  <RouterLink
                    v-if="r.dossier"
                    :to="{ name: 'relation-dossier', params: { slug: dossierSlug(r.dossier) } }"
                    class="inline-flex shrink-0 items-center gap-1 rounded-md border border-[var(--border)] bg-[var(--card)] px-2 py-0.5 text-[10px] font-medium text-[var(--primary)] transition hover:bg-[var(--secondary)]"
                  >
                    <FileText :size="11" />
                    Dossier
                  </RouterLink>
                </div>
                <p class="text-xs text-[var(--muted-foreground)]">
                  <template v-if="r.debut || r.fin">
                    {{ r.debut || '?' }} → {{ r.fin || '?' }}
                    <template v-if="relationDuree(r)">
                      <span class="text-[var(--muted-foreground)]/80">
                        · {{ relationDuree(r) }}
                      </span>
                    </template>
                  </template>
                  <template v-else-if="relationDuree(r)">{{ relationDuree(r) }}</template>
                  <template v-if="(r.debut || r.fin || relationDuree(r)) && r.note"> · </template>
                  <template v-if="r.note">{{ r.note }}</template>
                </p>
                <p
                  v-if="relationAgeLabel(r)"
                  class="mt-0.5 text-[11px] text-[var(--muted-foreground)]/85"
                >
                  Ton âge · {{ relationAgeLabel(r) }}
                </p>
                <p
                  v-if="r.apres?.length"
                  class="mt-1.5 text-[11px] leading-relaxed text-[var(--muted-foreground)]/90"
                >
                  <span class="font-medium text-[var(--muted-foreground)]">Après · </span>
                  <template v-for="(a, j) in r.apres" :key="`apres-${i}-${j}`">
                    <template v-if="j > 0"> · </template>
                    {{ suiteLabel(a) }}
                  </template>
                </p>
              </div>
            </li>
          </ul>
        </section>
      </div>
  </PageShell>
</template>
