<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { Bell, Home, Loader2, Smartphone } from '@lucide/vue'
import Dialog from '@/components/ui/Dialog.vue'
import logoIconUrl from '@/assets/logo-icon.png'
import { usePushSubscription } from '@/composables/usePushSubscription'

const {
  kind,
  error,
  loading,
  dialogOpen,
  dismissedThisVisit,
  syncPushSubscription,
  enablePush,
  dismissPushDialog,
  maybeOpenPushDialog,
} = usePushSubscription()

const title = computed(() => {
  if (kind.value === 'needs-home') return 'Ajouter Asclepios à l’écran d’accueil'
  if (kind.value === 'denied') return 'Notifications bloquées'
  return 'Activer les notifications'
})

const description = computed(() => {
  if (kind.value === 'needs-home') {
    return 'Sur iPhone, le Web Push ne fonctionne que si Asclepios est ouvert depuis l’icône d’accueil (PWA).'
  }
  if (kind.value === 'denied') {
    return 'Le navigateur a refusé les notifications. Réactive-les dans les réglages du site, puis reviens ici.'
  }
  return 'Reçois une alerte système pour tes rendez-vous, même si l’app est fermée.'
})

async function onEnable() {
  const ok = await enablePush()
  if (ok) dialogOpen.value = false
}

function onOpenChange(open: boolean) {
  if (open) {
    dialogOpen.value = true
    return
  }
  if (kind.value === 'subscribed') {
    dialogOpen.value = false
    return
  }
  dismissPushDialog()
}

async function refreshAndMaybeAsk() {
  await syncPushSubscription()
  maybeOpenPushDialog()
}

function onVisibility() {
  if (document.visibilityState !== 'visible') return
  void (async () => {
    await syncPushSubscription()
    if (kind.value !== 'subscribed') maybeOpenPushDialog()
  })()
}

watch(kind, (value) => {
  if (value === 'subscribed') dialogOpen.value = false
})

onMounted(() => {
  dismissedThisVisit.value = false
  window.setTimeout(() => {
    void refreshAndMaybeAsk()
  }, 700)
  document.addEventListener('visibilitychange', onVisibility)
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', onVisibility)
})
</script>

<template>
  <Dialog
    :open="dialogOpen"
    :title="title"
    :description="description"
    class="sm:max-w-md"
    @update:open="onOpenChange"
  >
    <div class="space-y-4 px-4 py-5 sm:px-6">
      <div class="flex items-center gap-3 rounded-xl bg-[var(--accent)]/45 px-3 py-2.5">
        <img :src="logoIconUrl" alt="" class="h-12 w-12 rounded-2xl object-cover shadow-sm" />
        <p class="text-sm text-[var(--foreground)]">
          <template v-if="kind === 'needs-home'">
            Safari en onglet refuse le push. Installe l’app, puis ouvre-la depuis l’icône.
          </template>
          <template v-else>
            Chrome / Android et Safari iOS (PWA, iOS 16.4+) reçoivent une notif système.
          </template>
        </p>
      </div>

      <ol
        v-if="kind === 'needs-home'"
        class="space-y-2 text-sm text-[var(--foreground)]"
      >
        <li class="flex gap-2">
          <Home :size="16" class="mt-0.5 shrink-0 text-[var(--primary)]" />
          Touche Partager, puis <strong>Sur l’écran d’accueil</strong>.
        </li>
        <li class="flex gap-2">
          <Smartphone :size="16" class="mt-0.5 shrink-0 text-[var(--primary)]" />
          Ouvre Asclepios depuis cette icône, puis accepte les notifications.
        </li>
      </ol>

      <p v-if="error" class="text-xs text-red-600">{{ error }}</p>
    </div>

    <div class="flex items-center justify-between gap-3 border-t border-[var(--border)] px-4 py-4 sm:px-6">
      <button
        type="button"
        class="rounded-lg px-3 py-2 text-sm text-[var(--muted-foreground)] transition hover:text-[var(--foreground)]"
        @click="dismissPushDialog"
      >
        Plus tard
      </button>
      <button
        v-if="kind !== 'needs-home' && kind !== 'denied' && kind !== 'unsupported'"
        type="button"
        class="inline-flex items-center gap-2 rounded-lg bg-[var(--primary)] px-5 py-2.5 text-sm font-medium text-[var(--primary-foreground)] shadow-sm transition hover:opacity-90 disabled:opacity-40"
        :disabled="loading"
        @click="onEnable"
      >
        <Loader2 v-if="loading" :size="15" class="animate-spin" />
        <Bell v-else :size="15" />
        Activer
      </button>
    </div>
  </Dialog>
</template>
