<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useOrdonnances } from '@/composables/useOrdonnances'
import PageShell from '@/components/PageShell.vue'
import {
  Calendar,
  ChevronRight,
  FlaskConical,
  Loader,
  Pill,
  ScrollText,
  Search,
  Tag,
  Upload,
  X,
} from '@lucide/vue'

const router = useRouter()
const { items, loading, error, load } = useOrdonnances()

const searchQuery = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const showTerminal = ref(false)
const syncLines = ref<string[]>([])
const syncDone = ref(false)
const syncError = ref<string | null>(null)
const uploadedId = ref<string | null>(null)

onMounted(() => {
  void load()
})

const filtered = computed(() => {
  const list = items.value
  if (!searchQuery.value.trim()) return list
  const q = searchQuery.value.toLowerCase()
  return list.filter(
    (i) =>
      (i.title || '').toLowerCase().includes(q) ||
      (i.prescriber || '').toLowerCase().includes(q) ||
      (i.filename || '').toLowerCase().includes(q) ||
      (i.kind || '').toLowerCase().includes(q) ||
      (i.date || '').includes(q) ||
      i.id.toLowerCase().includes(q),
  )
})

const grouped = computed(() => {
  const groups: Record<string, typeof items.value> = {}
  filtered.value.forEach((item) => {
    const key = item.date ? item.date.slice(0, 7) : 'Sans date'
    if (!groups[key]) groups[key] = []
    groups[key].push(item)
  })
  return Object.entries(groups).sort(([a], [b]) => b.localeCompare(a))
})

function formatDate(dateStr: string | null) {
  if (!dateStr) return ''
  const [year, month, day] = dateStr.split('-')
  const months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
  return `${parseInt(day)} ${months[parseInt(month) - 1]} ${year}`
}

function formatGroupLabel(key: string) {
  if (key === 'Sans date') return key
  const [year, month] = key.split('-')
  const months = [
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
  ]
  return `${months[parseInt(month) - 1]} ${year}`
}

function cardTitle(item: (typeof items.value)[number]) {
  if (item.kind === 'biologie') {
    return item.date ? `Biologie du ${formatDate(item.date)}` : item.title
  }
  return item.date ? `Ordonnance du ${formatDate(item.date)}` : item.title
}

function open(id: string) {
  void router.push(`/ordonnances/${encodeURIComponent(id)}`)
}

function pickFile() {
  if (uploading.value) return
  fileInput.value?.click()
}

async function onFileSelected(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    syncError.value = 'Seuls les fichiers PDF sont acceptés'
    showTerminal.value = true
    return
  }

  uploading.value = true
  showTerminal.value = true
  syncLines.value = []
  syncDone.value = false
  syncError.value = null
  uploadedId.value = null

  try {
    const form = new FormData()
    form.append('file', file, file.name)
    const res = await fetch('/api/ordonnances/pdfs/upload', { method: 'POST', body: form })
    if (!res.ok) {
      let detail = `HTTP ${res.status}`
      try {
        const body = await res.json()
        if (body?.detail) detail = String(body.detail)
      } catch {
        /* ignore */
      }
      throw new Error(detail)
    }

    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() ?? ''
      for (const block of blocks) {
        const line = block.replace(/^data: /, '').trim()
        if (!line) continue
        if (line === '[DONE]') {
          syncDone.value = true
          continue
        }
        if (line === '[ERROR]') {
          syncError.value = syncError.value || 'Échec'
          continue
        }
        if (line.startsWith('ID:')) {
          uploadedId.value = line.slice(3)
          continue
        }
        syncLines.value.push(line)
      }
    }
    await load()
  } catch (e) {
    syncError.value = e instanceof Error ? e.message : 'Upload impossible'
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <PageShell title="Ordonnances" max-width="lg">
    <template #description>
      <p class="mt-0.5 text-sm text-[var(--muted-foreground)]">
        {{ items.length }} ordonnance{{ items.length > 1 ? 's' : '' }} au total
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
          placeholder="Rechercher une ordonnance…"
          class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] py-2.5 pl-9 pr-4 text-sm placeholder:text-[var(--muted-foreground)] focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20 transition"
        />
      </div>
      <input
        ref="fileInput"
        type="file"
        accept="application/pdf,.pdf"
        class="hidden"
        @change="onFileSelected"
      />
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-lg bg-[var(--primary)] px-3 py-2.5 text-sm font-medium text-[var(--primary-foreground)] transition hover:opacity-90 disabled:opacity-50"
        :disabled="uploading"
        @click="pickFile"
      >
        <Loader v-if="uploading" :size="15" class="animate-spin" />
        <Upload v-else :size="15" />
        {{ uploading ? 'Envoi…' : 'Ajouter un PDF' }}
      </button>
      <button
        v-if="uploadedId && syncDone && !syncError"
        type="button"
        class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-2.5 text-sm text-[var(--foreground)] transition hover:bg-[var(--accent)]"
        @click="open(uploadedId)"
      >
        Ouvrir
        <ChevronRight :size="14" />
      </button>
    </template>

    <div
      v-if="showTerminal"
      class="relative mb-6 overflow-hidden rounded-xl border border-[var(--border)] bg-[oklch(0.12_0.02_165)] p-4 font-mono text-[11.5px] leading-5 text-slate-200"
    >
      <button
        type="button"
        class="absolute right-2 top-2 text-slate-400 hover:text-white"
        :disabled="uploading"
        @click="showTerminal = false"
      >
        <X :size="14" />
      </button>
      <p class="mb-2 text-xs font-semibold text-slate-300">Ajout + synchronisation OVH</p>
      <div class="max-h-40 overflow-y-auto">
        <p v-if="!syncLines.length && uploading" class="text-slate-500">Envoi du PDF…</p>
        <p
          v-for="(line, i) in syncLines"
          :key="i"
          :class="[
            line.startsWith('✗') ? 'text-red-400' :
            line.startsWith('✓') ? 'text-emerald-400' :
            line.startsWith('▶') ? 'text-[var(--primary)] font-semibold' :
            'text-slate-300',
          ]"
        >{{ line }}</p>
        <p v-if="syncDone && !syncError" class="mt-1 font-semibold text-emerald-400">✓ Terminé</p>
        <p v-if="syncError" class="mt-1 font-semibold text-red-400">✗ {{ syncError }}</p>
      </div>
    </div>

    <div v-if="loading && !items.length" class="flex flex-col items-center justify-center py-24 text-center">
      <p class="text-sm text-[var(--muted-foreground)]">Chargement des ordonnances…</p>
    </div>

    <div v-else-if="filtered.length === 0" class="flex flex-col items-center justify-center py-16 text-center">
      <div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--accent)]">
        <ScrollText :size="22" class="text-[var(--primary)]" />
      </div>
      <p class="text-base font-medium text-[var(--foreground)]">Aucune ordonnance trouvée</p>
      <p class="mt-1 text-sm text-[var(--muted-foreground)]">
        {{ items.length ? 'Modifiez votre recherche.' : 'Ajoutez un PDF via le bouton ci-dessus.' }}
      </p>
    </div>

    <div v-else class="space-y-8">
      <div v-for="([groupKey, groupItems]) in grouped" :key="groupKey">
        <div class="mb-4 flex items-center gap-3">
          <span class="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
            {{ formatGroupLabel(groupKey) }}
          </span>
          <div class="h-px flex-1 bg-[var(--border)]" />
          <span class="text-xs text-[var(--muted-foreground)]">{{ groupItems.length }}</span>
        </div>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <button
            v-for="item in groupItems"
            :key="item.id"
            type="button"
            class="group relative flex flex-col overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-[var(--primary)]/40 hover:shadow-md cursor-pointer"
            @click="open(item.id)"
          >
            <div class="absolute inset-x-0 top-0 h-0.5 bg-[var(--primary)] opacity-0 transition-opacity group-hover:opacity-100" />

            <div class="mb-3 flex items-center justify-between">
              <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)]">
                <FlaskConical
                  v-if="item.kind === 'biologie'"
                  :size="16"
                  class="text-[var(--primary)]"
                />
                <Pill v-else :size="16" class="text-[var(--primary)]" />
              </div>
              <div v-if="item.date" class="flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
                <Calendar :size="12" />
                <span>{{ formatDate(item.date) }}</span>
              </div>
            </div>

            <h3 class="mb-1 line-clamp-2 text-sm font-semibold leading-snug text-[var(--foreground)] transition-colors group-hover:text-[var(--primary)]">
              {{ cardTitle(item) }}
            </h3>
            <p class="mb-3 line-clamp-1 text-xs text-[var(--muted-foreground)]">
              {{ item.prescriber }}
            </p>

            <div class="mt-auto flex flex-wrap gap-1.5">
              <span
                class="flex items-center gap-1 rounded-full bg-[var(--secondary)] px-2 py-0.5 text-[10px] font-medium text-[var(--secondary-foreground)]"
              >
                <Tag :size="9" />
                {{ item.kind === 'biologie' ? 'Biologie' : 'Médicaments' }}
              </span>
              <span
                v-if="item.kind === 'biologie' && item.exams_count != null"
                class="rounded-full bg-[var(--accent)] px-2 py-0.5 text-[10px] font-medium text-[var(--accent-foreground)]"
              >
                {{ item.exams_count }} analyse{{ item.exams_count > 1 ? 's' : '' }}
              </span>
              <span
                v-else-if="item.medications_count != null"
                class="rounded-full bg-[var(--accent)] px-2 py-0.5 text-[10px] font-medium text-[var(--accent-foreground)]"
              >
                {{ item.medications_count }} médicament{{ item.medications_count > 1 ? 's' : '' }}
              </span>
            </div>
          </button>
        </div>
      </div>
    </div>
  </PageShell>
</template>
