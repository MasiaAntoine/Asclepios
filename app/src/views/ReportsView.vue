<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useReports } from '@/composables/useReports'
import GenerateReportDialog from '@/components/GenerateReportDialog.vue'
import PageShell from '@/components/PageShell.vue'
import { Calendar, FileText, Search, Tag } from '@lucide/vue'

const router = useRouter()
const { reports, loading, error, reload } = useReports()

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

function openReport(id: string) {
  router.push(`/rapports/${id}`)
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
      <div class="relative min-w-[12rem] flex-1 sm:min-w-[16rem]">
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
      <GenerateReportDialog @generated="onReportGenerated" />
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
    <div v-else class="space-y-8">
      <div v-for="([groupKey, groupReports]) in groupedReports" :key="groupKey">
        <!-- Month label -->
        <div class="mb-4 flex items-center gap-3">
          <span class="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
            {{ formatGroupLabel(groupKey) }}
          </span>
          <div class="h-px flex-1 bg-[var(--border)]" />
          <span class="text-xs text-[var(--muted-foreground)]">{{ groupReports.length }}</span>
        </div>

        <!-- Cards grid -->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <button
            v-for="report in groupReports"
            :key="report.id"
            @click="openReport(report.id)"
            class="group relative flex flex-col overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 text-left shadow-sm transition-all hover:border-[var(--primary)]/40 hover:shadow-md hover:-translate-y-0.5 cursor-pointer"
          >
            <!-- Top accent line on hover -->
            <div class="absolute inset-x-0 top-0 h-0.5 bg-[var(--primary)] opacity-0 transition-opacity group-hover:opacity-100" />

            <!-- Icon + date -->
            <div class="mb-3 flex items-center justify-between">
              <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)]">
                <FileText :size="16" class="text-[var(--primary)]" />
              </div>
              <div class="flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
                <Calendar :size="12" />
                <span>{{ formatDate(report.date) }}</span>
              </div>
            </div>

            <!-- Title -->
            <h3 class="mb-3 line-clamp-3 text-sm font-semibold leading-snug text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors">
              {{ report.title }}
            </h3>

            <!-- Tags -->
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
          </button>
        </div>
      </div>
    </div>
  </PageShell>
</template>
