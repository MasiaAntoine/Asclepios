<script setup lang="ts">
import { computed, ref } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import {
  CreditCard,
  FileText,
  MapPin,
  Stethoscope,
} from '@lucide/vue'
import { useDoctors, doctorFullName, doctorPhotoUrl, type Doctor } from '@/composables/useDoctors'
import DoctorEditDialog from '@/components/DoctorEditDialog.vue'
import DoctorDetail from '@/components/DoctorDetail.vue'
import GenerateDoctorReportStepper from '@/components/GenerateDoctorReportStepper.vue'
import BottomSheet from '@/components/ui/BottomSheet.vue'
import PageShell from '@/components/PageShell.vue'
import ReportDetailView from '@/views/ReportDetailView.vue'
import CompactRow from '@/components/CompactRow.vue'
import { useMobileSheet } from '@/composables/useMobileSheet'

const { doctors, loading, error, reload } = useDoctors()
const isMobile = useMediaQuery('(max-width: 767px)')
const { itemId: reportSheetId, sheetOpen: reportSheetOpen, openItem: openReportSheet } = useMobileSheet()

const selected = ref<Doctor | null>(null)
const photoFailed = ref<Record<string, boolean>>({})
const reportOpen = ref(false)
const reportDoctorId = ref<string | null>(null)

const sheetOpen = computed({
  get: () => Boolean(selected.value) && isMobile.value,
  set: (value) => {
    if (!value) selected.value = null
  },
})

function openReportStepper(doctorId?: string) {
  reportDoctorId.value = doctorId ?? selected.value?.id ?? null
  reportOpen.value = true
}

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
  selected.value = doctor
}
</script>

<template>
  <PageShell title="Équipe médicale" max-width="lg">
    <template #description>
      <p class="mt-0.5 text-sm text-[var(--muted-foreground)]">
        {{ doctors.length }} praticien{{ doctors.length > 1 ? 's' : '' }} dans votre suivi
      </p>
      <p v-if="error" class="mt-1 text-xs text-red-600">{{ error }}</p>
    </template>
    <template #actions>
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-lg bg-[var(--primary)] px-3 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-[var(--primary)]/90"
        @click="openReportStepper()"
      >
        <FileText :size="15" />
        Rapport médecin
      </button>
      <DoctorEditDialog mode="create" @saved="onDoctorsChanged" />
    </template>

    <div v-if="loading && !doctors.length" class="py-24 text-center text-sm text-[var(--muted-foreground)]">
      Chargement…
    </div>

    <div v-else class="space-y-6">
      <div class="space-y-2 md:hidden">
        <CompactRow
          v-for="doctor in doctors"
          :key="doctor.id"
          variant="card"
          :title="doctorFullName(doctor)"
          :subtitle="[doctor.specialite, doctor.adresse?.ville].filter(Boolean).join(' · ')"
          @click="selectDoctor(doctor)"
        >
          <template #icon>
            <img
              v-if="doctorPhotoUrl(doctor) && !photoFailed[doctor.id]"
              :src="doctorPhotoUrl(doctor)!"
              :alt="doctorFullName(doctor)"
              class="h-9 w-9 rounded-full object-cover"
              @error="photoFailed[doctor.id] = true"
            />
            <span
              v-else
              class="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--primary)] text-[11px] font-bold text-white"
            >
              {{ initials(doctor) }}
            </span>
          </template>
        </CompactRow>
      </div>

      <div class="hidden grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 md:grid">
        <button
          v-for="doctor in doctors"
          :key="doctor.id"
          type="button"
          :class="[
            'group relative flex flex-col gap-4 overflow-hidden rounded-2xl border bg-[var(--card)] p-5 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md',
            selected?.id === doctor.id
              ? 'border-[var(--primary)] ring-2 ring-[var(--primary)]/20'
              : 'border-[var(--border)] hover:border-[var(--primary)]/40',
          ]"
          @click="selectDoctor(doctor)"
        >
          <div class="absolute inset-x-0 top-0 h-0.5 bg-[var(--primary)] opacity-0 transition-opacity group-hover:opacity-100" />
          <div class="flex items-center gap-4">
            <div class="relative shrink-0">
              <img
                v-if="doctorPhotoUrl(doctor) && !photoFailed[doctor.id]"
                :src="doctorPhotoUrl(doctor)!"
                :alt="doctorFullName(doctor)"
                class="h-14 w-14 rounded-full object-cover ring-2 ring-[var(--primary)]/20"
                @error="photoFailed[doctor.id] = true"
              />
              <div
                v-else
                class="flex h-14 w-14 items-center justify-center rounded-full bg-[var(--primary)] text-white"
              >
                <span class="text-lg font-bold leading-none">{{ initials(doctor) }}</span>
              </div>
              <div class="absolute -bottom-0.5 -right-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-[var(--card)] shadow-sm ring-1 ring-[var(--border)]">
                <Stethoscope :size="11" class="text-[var(--primary)]" />
              </div>
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2">
                <p class="truncate font-semibold text-[var(--foreground)]">
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
          <div
            v-if="doctor.convention"
            class="flex items-center gap-1.5 rounded-lg bg-[var(--accent)] px-3 py-1.5 text-xs text-[var(--muted-foreground)]"
          >
            <CreditCard :size="11" class="text-[var(--primary)]" />
            {{ doctor.convention }}
          </div>
        </button>
      </div>

      <div
        v-if="selected && !isMobile"
        class="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-sm"
      >
        <DoctorDetail
          :doctor="selected"
          @report="openReportStepper"
          @saved="onDoctorsChanged"
          @deleted="() => { selected = null; onDoctorsChanged() }"
        />
      </div>
    </div>
  </PageShell>

  <BottomSheet v-model:open="sheetOpen">
    <DoctorDetail
      v-if="selected"
      compact
      :doctor="selected"
      @report="openReportStepper"
      @saved="onDoctorsChanged"
      @deleted="() => { selected = null; onDoctorsChanged() }"
    />
  </BottomSheet>

  <GenerateDoctorReportStepper
    v-model:open="reportOpen"
    :initial-doctor-id="reportDoctorId"
    @view="(id) => openReportSheet(id, `/rapports/${id}`)"
  />

  <BottomSheet v-model:open="reportSheetOpen">
    <ReportDetailView v-if="reportSheetId" embedded :item-id="reportSheetId" />
  </BottomSheet>
</template>
