<script setup lang="ts">
import { computed, ref } from 'vue'
import { useProfile } from '@/composables/useProfile'
import {
  Cigarette,
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
  <div class="flex h-full flex-col overflow-hidden">
    <!-- Header -->
    <div class="border-b border-[var(--border)] bg-[var(--card)] px-8 py-6">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold text-[var(--foreground)]">Profil patient</h1>
          <p class="mt-0.5 text-sm text-[var(--muted-foreground)]">
            Identité, constantes et traitements en cours
          </p>
        </div>
        <EditProfileDialog v-if="profil" :profil="profil" @saved="onProfileSaved" />
      </div>
    </div>

    <div class="flex-1 overflow-y-auto px-8 py-8">
      <div v-if="error" class="mx-auto max-w-5xl rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {{ error }}
      </div>
      <div v-else-if="loading && !profil" class="py-24 text-center text-sm text-[var(--muted-foreground)]">
        Chargement du profil…
      </div>
      <div v-else-if="profil" class="mx-auto max-w-5xl space-y-8">
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
            </div>
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
                    <template v-if="profil.parents.pere.date_naissance">
                      · né le {{ profil.parents.pere.date_naissance }}
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
                  <p class="text-xs text-[var(--muted-foreground)]">Mère</p>
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
                  <p class="text-xs capitalize text-[var(--muted-foreground)]">{{ s.lien }}</p>
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
                      <template v-if="p.date_naissance"> · né le {{ p.date_naissance }}</template>
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
                      <template v-if="a.date_naissance"> · né le {{ a.date_naissance }}</template>
                    </p>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
