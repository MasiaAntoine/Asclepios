<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMedications } from '@/composables/useMedications'
import { BookOpen, Pill, Search, Sunrise, Sunset } from '@lucide/vue'

const router = useRouter()
const { list, actifs, arretes, misAJour, loading, error } = useMedications()

const searchQuery = ref('')

const filtered = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  const items = list.value
  if (!q) return items
  return items.filter(
    (t) =>
      t.nom.toLowerCase().includes(q) ||
      t.forme.toLowerCase().includes(q) ||
      t.moment.toLowerCase().includes(q) ||
      t.actuel?.dose.toLowerCase().includes(q),
  )
})

const filteredActifs = computed(() => filtered.value.filter((t) => t.actif))
const filteredArretes = computed(() => filtered.value.filter((t) => !t.actif))

function openMed(id: string) {
  router.push(`/meds/${id}`)
}

function momentIcon(moment: string) {
  return moment === 'soir' ? Sunset : Sunrise
}
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <div class="border-b border-[var(--border)] bg-[var(--card)] px-8 py-6">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 class="text-2xl font-bold text-[var(--foreground)]">Médicaments</h1>
          <p class="mt-0.5 text-sm text-[var(--muted-foreground)]">
            {{ list.length }} fiche{{ list.length > 1 ? 's' : '' }}
            <template v-if="misAJour"> · mis à jour le {{ misAJour }}</template>
          </p>
          <p v-if="error" class="mt-1 text-xs text-red-600">{{ error }}</p>
        </div>
        <div class="relative w-full max-w-sm">
          <Search
            :size="16"
            class="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]"
          />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Rechercher…"
            class="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] py-2.5 pl-9 pr-4 text-sm placeholder:text-[var(--muted-foreground)] focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20 transition"
          />
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto px-8 py-8">
      <div class="mx-auto max-w-5xl space-y-8">
        <div v-if="loading && !list.length" class="py-16 text-center text-sm text-[var(--muted-foreground)]">
          Chargement…
        </div>

        <template v-else>
          <!-- Stats -->
          <div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
              <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Total</p>
              <p class="mt-1 text-2xl font-bold">{{ list.length }}</p>
            </div>
            <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
              <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">En cours</p>
              <p class="mt-1 text-2xl font-bold text-emerald-700">{{ actifs.length }}</p>
            </div>
            <div class="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
              <p class="text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]">Arrêtés</p>
              <p class="mt-1 text-2xl font-bold text-[var(--muted-foreground)]">{{ arretes.length }}</p>
            </div>
          </div>

          <div v-if="!filtered.length" class="py-16 text-center text-sm text-[var(--muted-foreground)]">
            Aucun médicament trouvé
          </div>

          <!-- Active -->
          <section v-if="filteredActifs.length">
            <h2 class="mb-4 text-sm font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
              En cours
            </h2>
            <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
              <button
                v-for="t in filteredActifs"
                :key="t.id"
                type="button"
                @click="openMed(t.id)"
                class="group relative flex flex-col overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 text-left shadow-sm transition-all hover:border-[var(--primary)]/40 hover:shadow-md hover:-translate-y-0.5 cursor-pointer"
              >
                <div class="absolute inset-x-0 top-0 h-0.5 bg-[var(--primary)] opacity-0 transition-opacity group-hover:opacity-100" />
                <div class="mb-3 flex items-start justify-between gap-3">
                  <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--accent)]">
                    <Pill :size="18" class="text-[var(--primary)]" />
                  </div>
                  <div class="flex flex-wrap items-center gap-1.5">
                    <span
                      v-if="t.si_besoin"
                      class="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-800"
                    >
                      Si besoin
                    </span>
                    <span class="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-800">
                      Actif
                    </span>
                  </div>
                </div>
                <h3 class="text-sm font-semibold text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors">
                  {{ t.nom }}
                </h3>
                <p class="mt-1 text-xs capitalize text-[var(--muted-foreground)]">
                  {{ t.forme }}
                </p>
                <div class="mt-4 rounded-lg bg-[var(--muted)] px-3 py-2.5">
                  <p class="text-sm font-semibold">{{ t.actuel?.dose ?? '—' }}</p>
                  <p class="text-xs text-[var(--muted-foreground)]">{{ t.actuel?.posologie }}</p>
                </div>
                <div class="mt-3 flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
                  <component :is="momentIcon(t.moment)" :size="12" />
                  <span class="capitalize">{{ t.moment }}</span>
                  <span v-if="t.doc" class="ml-auto flex items-center gap-1 text-[var(--primary)]">
                    <BookOpen :size="12" />
                    Fiche
                  </span>
                </div>
              </button>
            </div>
          </section>

          <!-- Stopped -->
          <section v-if="filteredArretes.length">
            <h2 class="mb-4 text-sm font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
              Arrêtés
            </h2>
            <div class="space-y-2">
              <button
                v-for="t in filteredArretes"
                :key="t.id"
                type="button"
                @click="openMed(t.id)"
                class="flex w-full items-center justify-between gap-4 rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3 text-left opacity-75 transition hover:opacity-100 hover:border-[var(--primary)]/30 cursor-pointer"
              >
                <div class="min-w-0">
                  <p class="text-sm font-medium truncate">{{ t.nom }}</p>
                  <p class="text-xs text-[var(--muted-foreground)]">
                    Arrêté le {{ t.actuel?.date }}
                    <template v-if="t.actuel?.note"> — {{ t.actuel.note }}</template>
                  </p>
                </div>
                <span class="shrink-0 rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-700">
                  Arrêt
                </span>
              </button>
            </div>
          </section>
        </template>
      </div>
    </div>
  </div>
</template>
