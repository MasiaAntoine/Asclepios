<script setup lang="ts">
import { ref } from 'vue'
import {
  BookOpen,
  Briefcase,
  Building2,
  CreditCard,
  ExternalLink,
  Globe,
  Languages,
  Link,
  Mail,
  MapPin,
  Phone,
  Stethoscope,
  UserRound,
} from '@lucide/vue'
import { useDoctors, doctorFullName, doctorPhotoUrl, type Doctor } from '@/composables/useDoctors'
import DoctorEditDialog from '@/components/DoctorEditDialog.vue'

const { doctors, loading, error, reload } = useDoctors()

const selected = ref<Doctor | null>(null)
const photoFailed = ref<Record<string, boolean>>({})

async function onDoctorsChanged() {
  await reload()
  if (selected.value) {
    selected.value = doctors.value.find((d) => d.id === selected.value?.id) ?? null
  }
}

function initials(doctor: Doctor) {
  return `${doctor.prenom[0] ?? ''}${doctor.nom[0] ?? ''}`.toUpperCase()
}

function selectDoctor(doctor: Doctor) {
  selected.value = selected.value?.id === doctor.id ? null : doctor
  photoFailed.value = {}
}
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <!-- Header -->
    <div class="border-b border-[var(--border)] bg-[var(--card)] px-8 py-6">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold text-[var(--foreground)]">Équipe médicale</h1>
          <p class="mt-0.5 text-sm text-[var(--muted-foreground)]">
            {{ doctors.length }} praticien{{ doctors.length > 1 ? 's' : '' }} dans votre suivi
          </p>
          <p v-if="error" class="mt-1 text-xs text-red-600">{{ error }}</p>
        </div>
        <DoctorEditDialog mode="create" @saved="onDoctorsChanged" />
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto px-8 py-8">
      <div v-if="loading && !doctors.length" class="py-24 text-center text-sm text-[var(--muted-foreground)]">
        Chargement…
      </div>

      <div v-else class="mx-auto max-w-5xl space-y-6">
        <!-- Cards list -->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <button
            v-for="doctor in doctors"
            :key="doctor.id"
            @click="selectDoctor(doctor)"
            :class="[
              'group relative flex flex-col gap-4 overflow-hidden rounded-2xl border bg-[var(--card)] p-5 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md',
              selected?.id === doctor.id
                ? 'border-[var(--primary)] ring-2 ring-[var(--primary)]/20'
                : 'border-[var(--border)] hover:border-[var(--primary)]/40',
            ]"
          >
            <!-- Accent top bar -->
            <div class="absolute inset-x-0 top-0 h-0.5 bg-[var(--primary)] opacity-0 transition-opacity group-hover:opacity-100" />

            <!-- Identity -->
            <div class="flex items-center gap-4">
              <!-- Avatar -->
              <div class="relative shrink-0">
                <img
                  v-if="doctorPhotoUrl(doctor) && !photoFailed[doctor.id]"
                  :src="doctorPhotoUrl(doctor)!"
                  :alt="doctorFullName(doctor)"
                  @error="photoFailed[doctor.id] = true"
                  class="h-14 w-14 rounded-full object-cover ring-2 ring-[var(--primary)]/20"
                />
                <!-- Fallback icon -->
                <div
                  v-else
                  class="flex h-14 w-14 items-center justify-center rounded-full bg-[var(--primary)] text-white"
                >
                  <span class="text-lg font-bold leading-none">{{ initials(doctor) }}</span>
                </div>
                <!-- Spécialité dot -->
                <div class="absolute -bottom-0.5 -right-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-[var(--card)] shadow-sm ring-1 ring-[var(--border)]">
                  <Stethoscope :size="11" class="text-[var(--primary)]" />
                </div>
              </div>

              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2 flex-wrap">
                  <p class="truncate font-semibold text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors">
                    {{ doctorFullName(doctor) }}
                  </p>
                  <span
                    v-if="doctor.role"
                    class="shrink-0 rounded-full bg-[var(--primary)] px-2 py-0.5 text-[10px] font-semibold text-white"
                  >
                    {{ doctor.role }}
                  </span>
                </div>
                <p class="text-sm text-[var(--primary)]">{{ doctor.specialite }}</p>
                <p v-if="doctor.adresse" class="mt-0.5 flex items-center gap-1 text-xs text-[var(--muted-foreground)]">
                  <MapPin :size="11" />
                  {{ doctor.adresse.ville }}
                </p>
              </div>
            </div>

            <!-- Convention badge -->
            <div v-if="doctor.convention" class="flex items-center gap-1.5 rounded-lg bg-[var(--accent)] px-3 py-1.5 text-xs text-[var(--muted-foreground)]">
              <CreditCard :size="11" class="text-[var(--primary)]" />
              {{ doctor.convention }}
            </div>
          </button>
        </div>

        <!-- Detail panel -->
        <Transition
          enter-active-class="transition-all duration-300"
          enter-from-class="opacity-0 -translate-y-2"
          leave-active-class="transition-all duration-200"
          leave-to-class="opacity-0 -translate-y-2"
        >
          <div
            v-if="selected"
            :key="selected.id"
            class="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-sm"
          >
            <!-- Panel header -->
            <div class="flex items-center gap-5 border-b border-[var(--border)] bg-[var(--accent)]/40 px-6 py-5">
              <!-- Big avatar -->
              <div class="relative shrink-0">
                <img
                  v-if="doctorPhotoUrl(selected) && !photoFailed[selected.id + '_detail']"
                  :src="doctorPhotoUrl(selected)!"
                  :alt="doctorFullName(selected)"
                  @error="photoFailed[selected.id + '_detail'] = true"
                  class="h-20 w-20 rounded-full object-cover ring-2 ring-[var(--primary)]/30 shadow-sm"
                />
                <div
                  v-else
                  class="flex h-20 w-20 items-center justify-center rounded-full bg-[var(--primary)] text-white shadow-sm"
                >
                  <span class="text-2xl font-bold leading-none">{{ initials(selected) }}</span>
                </div>
              </div>

              <div class="flex-1">
                <div class="flex items-center gap-2.5 flex-wrap">
                  <h2 class="text-xl font-bold text-[var(--foreground)]">{{ doctorFullName(selected) }}</h2>
                  <span
                    v-if="selected.role"
                    class="rounded-full bg-[var(--primary)] px-2.5 py-0.5 text-xs font-semibold text-white"
                  >
                    {{ selected.role }}
                  </span>
                </div>
                <p class="font-medium text-[var(--primary)]">{{ selected.specialite }}</p>
                <div v-if="selected.adresse" class="mt-1 flex items-center gap-1.5 text-sm text-[var(--muted-foreground)]">
                  <MapPin :size="13" />
                  {{ selected.adresse.voie }}, {{ selected.adresse.code_postal }} {{ selected.adresse.ville }}
                </div>
              </div>

              <div class="flex flex-col gap-2">
                <DoctorEditDialog
                  mode="edit"
                  :doctor="selected"
                  @saved="onDoctorsChanged"
                  @deleted="() => { selected = null; onDoctorsChanged() }"
                />
                <a
                  v-if="selected.doctolib"
                  :href="selected.doctolib"
                  target="_blank"
                  rel="noopener"
                  class="flex items-center gap-1.5 rounded-lg bg-[var(--primary)] px-3 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-[var(--primary)]/90"
                >
                  <ExternalLink :size="14" />
                  Doctolib
                </a>
                <a
                  v-if="selected.site_web"
                  :href="selected.site_web"
                  target="_blank"
                  rel="noopener"
                  class="flex items-center gap-1.5 rounded-lg bg-[var(--primary)] px-3 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-[var(--primary)]/90"
                >
                  <Link :size="14" />
                  Site web
                </a>
                <a
                  v-if="selected.telephone"
                  :href="`tel:${selected.telephone.replace(/\s/g, '')}`"
                  class="flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm font-medium text-[var(--foreground)] transition hover:bg-[var(--accent)]"
                >
                  <Phone :size="14" />
                  {{ selected.telephone }}
                </a>
                <a
                  v-if="selected.email"
                  :href="`mailto:${selected.email}`"
                  class="flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm font-medium text-[var(--foreground)] transition hover:bg-[var(--accent)]"
                >
                  <Mail :size="14" />
                  {{ selected.email }}
                </a>
              </div>
            </div>

            <!-- Panel body -->
            <div class="grid grid-cols-1 gap-6 p-6 md:grid-cols-2">

              <!-- Présentation -->
              <div v-if="selected.presentation || selected.approches?.length" class="space-y-3">
                <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  <UserRound :size="13" class="text-[var(--primary)]" />
                  Présentation
                </h3>
                <p v-if="selected.presentation" class="text-sm leading-relaxed text-[var(--foreground)]">
                  {{ selected.presentation }}
                </p>
                <div v-if="selected.approches?.length" class="flex flex-wrap gap-1.5">
                  <span
                    v-for="a in selected.approches"
                    :key="a"
                    class="rounded-full bg-[var(--secondary)] px-2.5 py-1 text-xs font-medium text-[var(--secondary-foreground)]"
                  >
                    {{ a }}
                  </span>
                </div>
              </div>

              <!-- Tarifs -->
              <div v-if="selected.tarifs?.length" class="space-y-3">
                <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  <CreditCard :size="13" class="text-[var(--primary)]" />
                  Tarifs
                </h3>
                <div class="divide-y divide-[var(--border)] overflow-hidden rounded-xl border border-[var(--border)]">
                  <div
                    v-for="t in selected.tarifs"
                    :key="t.label"
                    class="flex items-center justify-between bg-[var(--card)] px-4 py-2.5"
                  >
                    <span class="text-sm text-[var(--foreground)]">{{ t.label }}</span>
                    <span class="font-semibold text-[var(--primary)]">{{ t.valeur }}</span>
                  </div>
                </div>
                <div class="space-y-1 text-xs text-[var(--muted-foreground)]">
                  <p v-if="selected.convention" class="flex items-center gap-1.5">
                    <span class="inline-block h-1.5 w-1.5 rounded-full bg-[var(--primary)]" />
                    {{ selected.convention }}
                  </p>
                  <p v-if="selected.tiers_payant" class="flex items-center gap-1.5">
                    <span class="inline-block h-1.5 w-1.5 rounded-full bg-[var(--primary)]" />
                    Tiers payant : {{ selected.tiers_payant }}
                  </p>
                  <p v-if="selected.carte_vitale" class="flex items-center gap-1.5">
                    <span class="inline-block h-1.5 w-1.5 rounded-full bg-[var(--primary)]" />
                    Carte Vitale acceptée
                  </p>
                  <p v-if="selected.paiements?.length" class="flex items-center gap-1.5">
                    <span class="inline-block h-1.5 w-1.5 rounded-full bg-[var(--primary)]" />
                    {{ selected.paiements.join(', ') }}
                  </p>
                </div>
              </div>

              <!-- Formations -->
              <div v-if="selected.formations?.length" class="space-y-3">
                <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  <BookOpen :size="13" class="text-[var(--primary)]" />
                  Formations
                </h3>
                <div class="space-y-2">
                  <div
                    v-for="f in selected.formations"
                    :key="f.label"
                    class="flex gap-3"
                  >
                    <span v-if="f.annee" class="mt-0.5 shrink-0 text-xs font-bold text-[var(--primary)]">{{ f.annee }}</span>
                    <span class="text-sm text-[var(--foreground)]">{{ f.label }}</span>
                  </div>
                </div>
              </div>

              <!-- Expériences -->
              <div v-if="selected.experiences?.length" class="space-y-3">
                <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  <Briefcase :size="13" class="text-[var(--primary)]" />
                  Expérience
                </h3>
                <div class="space-y-2">
                  <div
                    v-for="e in selected.experiences"
                    :key="e.label"
                    class="flex gap-3"
                  >
                    <span v-if="e.depuis" class="mt-0.5 shrink-0 text-xs font-bold text-[var(--primary)]">{{ e.depuis }}→</span>
                    <span class="text-sm text-[var(--foreground)]">{{ e.label }}</span>
                  </div>
                </div>
              </div>

              <!-- Langues -->
              <div v-if="selected.langues?.length" class="space-y-3">
                <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  <Languages :size="13" class="text-[var(--primary)]" />
                  Langues
                </h3>
                <div class="flex flex-col gap-1.5">
                  <div
                    v-for="l in selected.langues"
                    :key="typeof l === 'string' ? l : l.langue"
                    class="flex items-center justify-between rounded-lg bg-[var(--accent)]/50 px-3 py-1.5"
                  >
                    <span class="flex items-center gap-1.5 text-sm font-medium text-[var(--foreground)]">
                      <Globe :size="11" class="text-[var(--primary)]" />
                      {{ typeof l === 'string' ? l : l.langue }}
                    </span>
                    <span
                      v-if="typeof l !== 'string' && l.niveau"
                      class="text-xs text-[var(--muted-foreground)]"
                    >
                      {{ l.niveau }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Modalités de consultation -->
              <div v-if="selected.modalites?.length" class="space-y-3">
                <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  <Briefcase :size="13" class="text-[var(--primary)]" />
                  Modalités
                </h3>
                <div class="flex flex-wrap gap-1.5">
                  <span
                    v-for="m in selected.modalites"
                    :key="m"
                    class="rounded-full bg-[var(--secondary)] px-2.5 py-1 text-xs font-medium text-[var(--secondary-foreground)]"
                  >
                    {{ m }}
                  </span>
                </div>
              </div>

              <!-- Affiliations -->
              <div v-if="selected.affiliations?.length" class="space-y-3">
                <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  <Globe :size="13" class="text-[var(--primary)]" />
                  Affiliations
                </h3>
                <ul class="space-y-1">
                  <li
                    v-for="a in selected.affiliations"
                    :key="a"
                    class="flex items-start gap-1.5 text-sm text-[var(--foreground)]"
                  >
                    <span class="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--primary)]" />
                    {{ a }}
                  </li>
                </ul>
              </div>

              <!-- Infos légales -->
              <div v-if="selected.infos_legales && Object.values(selected.infos_legales).some(Boolean)" class="space-y-3">
                <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  <Building2 :size="13" class="text-[var(--primary)]" />
                  Informations légales
                </h3>
                <div class="space-y-1 text-xs">
                  <p v-if="selected.infos_legales.rpps" class="text-[var(--muted-foreground)]">
                    RPPS : <span class="font-mono text-[var(--foreground)]">{{ selected.infos_legales.rpps }}</span>
                  </p>
                  <p v-if="selected.infos_legales.adeli" class="text-[var(--muted-foreground)]">
                    ADELI : <span class="font-mono text-[var(--foreground)]">{{ selected.infos_legales.adeli }}</span>
                  </p>
                  <p v-if="selected.infos_legales.siren" class="text-[var(--muted-foreground)]">
                    SIREN : <span class="font-mono text-[var(--foreground)]">{{ selected.infos_legales.siren }}</span>
                  </p>
                  <p v-if="selected.infos_legales.siret" class="text-[var(--muted-foreground)]">
                    SIRET : <span class="font-mono text-[var(--foreground)]">{{ selected.infos_legales.siret }}</span>
                  </p>
                </div>
              </div>

              <!-- Notes personnelles -->
              <div v-if="selected.notes" class="md:col-span-2 space-y-2">
                <h3 class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  Notes personnelles
                </h3>
                <p class="rounded-xl border border-[var(--border)] bg-[var(--accent)]/30 p-4 text-sm leading-relaxed text-[var(--foreground)]">
                  {{ selected.notes }}
                </p>
              </div>

            </div>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>
