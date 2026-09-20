<script setup lang="ts">
import { computed, ref } from 'vue'
import { useReports } from '@/composables/useReports'
import { useMobileSheet } from '@/composables/useMobileSheet'
import GenerateReportDialog from '@/components/GenerateReportDialog.vue'
import PageShell from '@/components/PageShell.vue'
import BottomSheet from '@/components/ui/BottomSheet.vue'
import ReportDetailView from '@/views/ReportDetailView.vue'
import CompactRow from '@/components/CompactRow.vue'
import ReportEmotionIcons from '@/components/ReportEmotionIcons.vue'
import { Calendar, FileText, Search, Tag } from '@lucide/vue'

const { reports, loading, error, reload } = useReports()
const { itemId, sheetOpen, openItem } = useMobileSheet()

function onReportGenerated() {
  void reload()
}

const searchQuery = ref('')

const filteredReports = computed(() => {
  const list = reports.value
  if (!searchQuery.value.trim()) return list
  const q = searchQuery.value.toLowerCase()
  return list.filter(
    (r) =>
      r.title.toLowerCase().includes(q) ||
      r.id.toLowerCase().includes(q) ||
      r.tags.some((t) => t.toLowerCase().includes(q)),
  )
})

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  const [year, month, day] = dateStr.split('-')
  const months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
  return `${parseInt(day)} ${months[parseInt(month) - 1]} ${year}`
}

function formatShortDate(dateStr: string) {
  if (!dateStr) return ''
  const [, month, day] = dateStr.split('-')
  const months = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']
  return `${parseInt(day)} ${months[parseInt(month) - 1]}`
}

function openReport(id: string) {
  openItem(id, `/rapports/${id}`)
}

// Group by month/year
const groupedReports = computed(() => {
  const groups: Record<string, typeof reports.value> = {}
  filteredReports.value.forEach((r) => {
    const key = r.date ? r.date.slice(0, 7) : 'Sans date'
    if (!groups[key]) groups[key] = []
    groups[key].push(r)
  })
  return Object.entries(groups).sort(([a], [b]) => b.localeCompare(a))
})

function formatGroupLabel(key: string) {
  if (key === 'Sans date') return key
  const [year, month] = key.split('-')
  const months = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
  return `${months[parseInt(month) - 1]} ${year}`
}
</script>

<template>
  <PageShell title="Rapports" max-width="lg">
    <template #description>
      <p class="mt-0.5 text-sm text-[var(--muted-foreground)]">
        {{ reports.length }} rapport{{ reports.length > 1 ? 's' : '' }} au total
      </p>
      <p v-if="error" class="mt-1 text-xs text-red-600">{{ error }}</p>
    </template>
    <template #actions>
      <div class="relative w-full min-w-0 flex-1">
        <Search
          :size="16"
          class="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]"
        />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Rechercher un rapport..."
          class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] py-2.5 pl-9 pr-4 text-sm placeholder:text-[var(--muted-foreground)] focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20 transition"
        />
      </div>
      <GenerateReportDialog
        @generated="onReportGenerated"
        @view="(id) => openItem(id, `/rapports/${id}`)"
      />
    </template>

    <!-- Loading -->
    <div v-if="loading && !reports.length" class="flex flex-col items-center justify-center py-24 text-center">
      <p class="text-sm text-[var(--muted-foreground)]">Chargement des rapports…</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="filteredReports.length === 0" class="flex flex-col items-center justify-center py-16 text-center">
      <p class="text-base font-medium text-[var(--foreground)]">Aucun rapport trouvé</p>
      <p class="mt-1 text-sm text-[var(--muted-foreground)]">Essayez de modifier votre recherche ou générez-en un avec l'IA.</p>
    </div>

    <!-- Groups -->
    <div v-else class="space-y-5 md:space-y-8">
      <div v-for="([groupKey, groupReports]) in groupedReports" :key="groupKey">
        <p class="mb-1 text-[15px] text-[var(--muted-foreground)] md:hidden">
          {{ formatGroupLabel(groupKey) }}
        </p>
        <div class="mb-4 hidden items-center gap-3 md:flex">
          <span class="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
            {{ formatGroupLabel(groupKey) }}
          </span>
          <div class="h-px flex-1 bg-[var(--border)]" />
          <span class="text-xs text-[var(--muted-foreground)]">{{ groupReports.length }}</span>
        </div>

        <div class="md:hidden">
          <div
            v-for="report in groupReports"
            :key="report.id"
            class="border-b border-[var(--border)]/60 last:border-0"
          >
            <CompactRow
              :title="report.title"
              :meta="formatShortDate(report.date)"
              :subtitle="report.tags.slice(0, 2).join(' · ')"
              @click="openReport(report.id)"
            >
              <template #icon>
                <FileText :size="20" />
              </template>
            </CompactRow>
            <div class="pb-2.5 pl-11">
              <ReportEmotionIcons :report-id="report.id" :size="26" />
            </div>
          </div>
        </div>

        <div class="hidden grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 md:grid">
          <button
            v-for="report in groupReports"
            :key="report.id"
            @click="openReport(report.id)"
            class="group relative flex flex-col overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 text-left shadow-sm transition-all hover:border-[var(--primary)]/40 hover:shadow-md hover:-translate-y-0.5 cursor-pointer"
          >
            <div class="absolute inset-x-0 top-0 h-0.5 bg-[var(--primary)] opacity-0 transition-opacity group-hover:opacity-100" />
            <div class="mb-3 flex items-center justify-between">
              <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)]">
                <FileText :size="16" class="text-[var(--primary)]" />
              </div>
              <div class="flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
                <Calendar :size="12" />
                <span>{{ formatDate(report.date) }}</span>
              </div>
            </div>
            <h3 class="mb-3 line-clamp-3 text-sm font-semibold leading-snug text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors">
              {{ report.title }}
            </h3>
            <div v-if="report.tags.length" class="mt-auto flex flex-wrap gap-1.5">
              <span
                v-for="tag in report.tags"
                :key="tag"
                class="flex items-center gap-1 rounded-full bg-[var(--secondary)] px-2 py-0.5 text-[10px] font-medium text-[var(--secondary-foreground)]"
              >
                <Tag :size="9" />
                {{ tag }}
              </span>
            </div>
            <div class="mt-3" @click.stop>
              <ReportEmotionIcons :report-id="report.id" :size="28" />
            </div>
          </button>
        </div>
      </div>
    </div>
  </PageShell>

  <BottomSheet v-model:open="sheetOpen">
    <ReportDetailView
      v-if="itemId"
      embedded
      :item-id="itemId"
    />
  </BottomSheet>
</template>
