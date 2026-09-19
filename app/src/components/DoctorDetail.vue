<script setup lang="ts">
import { ref } from 'vue'
import {
  BookOpen,
  Briefcase,
  Building2,
  CreditCard,
  ExternalLink,
  FileText,
  Globe,
  Languages,
  Link,
  Mail,
  MapPin,
  Phone,
  UserRound,
} from '@lucide/vue'
import { doctorFullName, doctorPhotoUrl, type Doctor } from '@/composables/useDoctors'
import DoctorEditDialog from '@/components/DoctorEditDialog.vue'

const props = defineProps<{
  doctor: Doctor
  compact?: boolean
}>()

const emit = defineEmits<{
  report: [doctorId: string]
  saved: []
  deleted: []
}>()

const photoFailed = ref(false)

function initials(doctor: Doctor) {
  return `${doctor.prenom[0] ?? ''}${doctor.nom[0] ?? ''}`.toUpperCase()
}
</script>

<template>
  <div>
    <div
      :class="
        compact
          ? 'flex flex-col gap-4 pb-2'
          : 'flex flex-col gap-5 border-b border-[var(--border)] bg-[var(--accent)]/40 px-6 py-5 sm:flex-row sm:items-center'
      "
    >
      <div class="flex items-center gap-4">
        <div class="relative shrink-0">
          <img
            v-if="doctorPhotoUrl(doctor) && !photoFailed"
            :src="doctorPhotoUrl(doctor)!"
            :alt="doctorFullName(doctor)"
            class="rounded-full object-cover ring-2 ring-[var(--primary)]/30 shadow-sm"
            :class="compact ? 'h-16 w-16' : 'h-20 w-20'"
            @error="photoFailed = true"
          />
          <div
            v-else
            class="flex items-center justify-center rounded-full bg-[var(--primary)] text-white shadow-sm"
            :class="compact ? 'h-16 w-16' : 'h-20 w-20'"
          >
            <span class="font-bold leading-none" :class="compact ? 'text-xl' : 'text-2xl'">
              {{ initials(doctor) }}
            </span>
          </div>
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="text-lg font-bold text-[var(--foreground)]">{{ doctorFullName(doctor) }}</h2>
            <span
              v-if="doctor.role"
              class="rounded-full bg-[var(--primary)] px-2.5 py-0.5 text-xs font-semibold text-white"
            >
              {{ doctor.role }}
            </span>
          </div>
          <p class="font-medium text-[var(--primary)]">{{ doctor.specialite }}</p>
          <div
            v-if="doctor.adresse"
            class="mt-1 flex items-center gap-1.5 text-sm text-[var(--muted-foreground)]"
          >
            <MapPin :size="13" />
            {{ doctor.adresse.voie }}, {{ doctor.adresse.code_postal }} {{ doctor.adresse.ville }}
          </div>
        </div>
      </div>

      <div class="flex flex-col gap-2 sm:min-w-[12rem]">
        <button
          type="button"
          class="flex items-center justify-center gap-1.5 rounded-lg bg-[var(--primary)] px-3 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-[var(--primary)]/90"
          @click="emit('report', doctor.id)"
        >
          <FileText :size="14" />
          Générer un rapport
        </button>
        <DoctorEditDialog
          mode="edit"
          :doctor="doctor"
          @saved="emit('saved')"
          @deleted="emit('deleted')"
        />
        <a
          v-if="doctor.doctolib"
          :href="doctor.doctolib"
          target="_blank"
          rel="noopener"
          class="flex items-center justify-center gap-1.5 rounded-lg bg-[var(--primary)] px-3 py-2.5 text-sm font-medium text-white"
        >
          <ExternalLink :size="14" />
          Doctolib
        </a>
        <a
          v-if="doctor.site_web"
          :href="doctor.site_web"
          target="_blank"
          rel="noopener"
          class="flex items-center justify-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-2.5 text-sm font-medium"
        >
          <Link :size="14" />
          Site web
        </a>
        <a
          v-if="doctor.telephone"
          :href="`tel:${doctor.telephone.replace(/\s/g, '')}`"
          class="flex items-center justify-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-2.5 text-sm font-medium"
        >
          <Phone :size="14" />
          {{ doctor.telephone }}
        </a>
        <a
          v-if="doctor.email"
          :href="`mailto:${doctor.email}`"
          class="flex items-center justify-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-2.5 text-sm font-medium"
        >
          <Mail :size="14" />
          {{ doctor.email }}
        </a>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6 py-5 md:grid-cols-2 md:p-6">
      <div v-if="doctor.presentation || doctor.approches?.length" class="space-y-3">
        <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
          <UserRound :size="13" class="text-[var(--primary)]" />
          Présentation
        </h3>
        <p v-if="doctor.presentation" class="text-sm leading-relaxed text-[var(--foreground)]">
          {{ doctor.presentation }}
        </p>
        <div v-if="doctor.approches?.length" class="flex flex-wrap gap-1.5">
          <span
            v-for="a in doctor.approches"
            :key="a"
            class="rounded-full bg-[var(--secondary)] px-2.5 py-1 text-xs font-medium text-[var(--secondary-foreground)]"
          >
            {{ a }}
          </span>
        </div>
      </div>

      <div v-if="doctor.tarifs?.length" class="space-y-3">
        <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
          <CreditCard :size="13" class="text-[var(--primary)]" />
          Tarifs
        </h3>
        <div class="divide-y divide-[var(--border)] overflow-hidden rounded-xl border border-[var(--border)]">
          <div
            v-for="t in doctor.tarifs"
            :key="t.label"
            class="flex items-center justify-between px-4 py-2.5"
          >
            <span class="text-sm">{{ t.label }}</span>
            <span class="font-semibold text-[var(--primary)]">{{ t.valeur }}</span>
          </div>
        </div>
        <div class="space-y-1 text-xs text-[var(--muted-foreground)]">
          <p v-if="doctor.convention">{{ doctor.convention }}</p>
          <p v-if="doctor.tiers_payant">Tiers payant : {{ doctor.tiers_payant }}</p>
          <p v-if="doctor.carte_vitale">Carte Vitale acceptée</p>
          <p v-if="doctor.paiements?.length">{{ doctor.paiements.join(', ') }}</p>
        </div>
      </div>

      <div v-if="doctor.formations?.length" class="space-y-3">
        <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
          <BookOpen :size="13" class="text-[var(--primary)]" />
          Formations
        </h3>
        <div class="space-y-2">
          <div v-for="f in doctor.formations" :key="f.label" class="flex gap-3">
            <span v-if="f.annee" class="mt-0.5 shrink-0 text-xs font-bold text-[var(--primary)]">{{ f.annee }}</span>
            <span class="text-sm">{{ f.label }}</span>
          </div>
        </div>
      </div>

      <div v-if="doctor.experiences?.length" class="space-y-3">
        <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
          <Briefcase :size="13" class="text-[var(--primary)]" />
          Expérience
        </h3>
        <div class="space-y-2">
          <div v-for="e in doctor.experiences" :key="e.label" class="flex gap-3">
            <span v-if="e.depuis" class="mt-0.5 shrink-0 text-xs font-bold text-[var(--primary)]">{{ e.depuis }}→</span>
            <span class="text-sm">{{ e.label }}</span>
          </div>
        </div>
      </div>

      <div v-if="doctor.langues?.length" class="space-y-3">
        <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
          <Languages :size="13" class="text-[var(--primary)]" />
          Langues
        </h3>
        <div class="flex flex-col gap-1.5">
          <div
            v-for="l in doctor.langues"
            :key="typeof l === 'string' ? l : l.langue"
            class="flex items-center justify-between rounded-lg bg-[var(--accent)]/50 px-3 py-1.5"
          >
            <span class="flex items-center gap-1.5 text-sm font-medium">
              <Globe :size="11" class="text-[var(--primary)]" />
              {{ typeof l === 'string' ? l : l.langue }}
            </span>
            <span v-if="typeof l !== 'string' && l.niveau" class="text-xs text-[var(--muted-foreground)]">
              {{ l.niveau }}
            </span>
          </div>
        </div>
      </div>

      <div v-if="doctor.modalites?.length" class="space-y-3">
        <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
          <Briefcase :size="13" class="text-[var(--primary)]" />
          Modalités
        </h3>
        <div class="flex flex-wrap gap-1.5">
          <span
            v-for="m in doctor.modalites"
            :key="m"
            class="rounded-full bg-[var(--secondary)] px-2.5 py-1 text-xs font-medium"
          >
            {{ m }}
          </span>
        </div>
      </div>

      <div v-if="doctor.affiliations?.length" class="space-y-3">
        <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
          <Globe :size="13" class="text-[var(--primary)]" />
          Affiliations
        </h3>
        <ul class="space-y-1">
          <li v-for="a in doctor.affiliations" :key="a" class="flex items-start gap-1.5 text-sm">
            <span class="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--primary)]" />
            {{ a }}
          </li>
        </ul>
      </div>

      <div
        v-if="doctor.infos_legales && Object.values(doctor.infos_legales).some(Boolean)"
        class="space-y-3"
      >
        <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
          <Building2 :size="13" class="text-[var(--primary)]" />
          Informations légales
        </h3>
        <div class="space-y-1 text-xs text-[var(--muted-foreground)]">
          <p v-if="doctor.infos_legales.rpps">
            RPPS : <span class="font-mono text-[var(--foreground)]">{{ doctor.infos_legales.rpps }}</span>
          </p>
          <p v-if="doctor.infos_legales.adeli">
            ADELI : <span class="font-mono text-[var(--foreground)]">{{ doctor.infos_legales.adeli }}</span>
          </p>
          <p v-if="doctor.infos_legales.siren">
            SIREN : <span class="font-mono text-[var(--foreground)]">{{ doctor.infos_legales.siren }}</span>
          </p>
          <p v-if="doctor.infos_legales.siret">
            SIRET : <span class="font-mono text-[var(--foreground)]">{{ doctor.infos_legales.siret }}</span>
          </p>
        </div>
      </div>

      <div v-if="doctor.notes" class="space-y-2 md:col-span-2">
        <h3 class="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
          Notes personnelles
        </h3>
        <p class="rounded-xl border border-[var(--border)] bg-[var(--accent)]/30 p-4 text-sm leading-relaxed">
          {{ doctor.notes }}
        </p>
      </div>
    </div>
  </div>
</template>
