<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import logoIconUrl from '@/assets/logo-icon.jpg'
import UserMenu from '@/components/UserMenu.vue'
import { hubForPath } from '@/lib/hubs'
import {
  Activity,
  FileText,
  LayoutDashboard,
  UserRound,
  type LucideIcon,
} from '@lucide/vue'

interface NavItem {
  label: string
  icon: LucideIcon
  to: string
  name: string
}

const route = useRoute()
const router = useRouter()
const keyboardOpen = ref(false)
let dockRaf = 0

const primaryTabs: NavItem[] = [
  { label: 'Accueil', icon: LayoutDashboard, to: '/', name: 'dashboard' },
  { label: 'Suivi', icon: Activity, to: '/suivi', name: 'suivi' },
  { label: 'Documents', icon: FileText, to: '/rapports', name: 'documents' },
  { label: 'Dossier', icon: UserRound, to: '/profil', name: 'dossier' },
]

function isTabActive(item: NavItem) {
  if (item.to === '/') return route.path === '/'
  const hub = hubForPath(route.path)
  if (item.name === 'suivi') return hub === 'suivi'
  if (item.name === 'documents') return hub === 'documents'
  if (item.name === 'dossier') return hub === 'dossier'
  return route.path.startsWith(item.to)
}

const chatActive = computed(() => route.path.startsWith('/assistant'))

const pageTitle = computed(() => {
  if (route.path === '/') return 'Accueil'
  if (chatActive.value) return 'Discuter'
  if (route.path.startsWith('/settings')) return 'Réglages'
  const hub = hubForPath(route.path)
  if (hub === 'suivi') return 'Suivi'
  if (hub === 'documents') return 'Documents'
  if (hub === 'dossier') return 'Dossier'
  return 'Asclepios'
})

function navigate(item: NavItem) {
  void router.push(item.to)
}

function goChat() {
  void router.push('/assistant')
}

function syncDockOffset() {
  cancelAnimationFrame(dockRaf)
  dockRaf = requestAnimationFrame(() => {
    const vv = window.visualViewport
    const isCompact = window.matchMedia('(max-width: 767px)').matches
    const inset = vv ? Math.max(0, window.innerHeight - vv.height - vv.offsetTop) : 0
    keyboardOpen.value = isCompact && inset > 60
    const offset = !isCompact || keyboardOpen.value ? '0px' : '5.75rem'
    document.documentElement.style.setProperty('--mobile-dock', offset)
  })
}

onMounted(() => {
  syncDockOffset()
  const vv = window.visualViewport
  vv?.addEventListener('resize', syncDockOffset)
  vv?.addEventListener('scroll', syncDockOffset)
  window.addEventListener('resize', syncDockOffset)
})

onUnmounted(() => {
  cancelAnimationFrame(dockRaf)
  const vv = window.visualViewport
  vv?.removeEventListener('resize', syncDockOffset)
  vv?.removeEventListener('scroll', syncDockOffset)
  window.removeEventListener('resize', syncDockOffset)
  document.documentElement.style.removeProperty('--mobile-dock')
})

watch(
  () => route.fullPath,
  () => {
    syncDockOffset()
  },
)
</script>

<template>
  <header
    class="fixed inset-x-0 top-0 z-40 flex h-[calc(3.5rem+env(safe-area-inset-top))] items-center gap-3 border-b border-[var(--border)] bg-[var(--card)] px-4 pt-[env(safe-area-inset-top)] md:left-64"
  >
    <p class="min-w-0 flex-1 truncate text-sm font-bold text-[var(--foreground)] md:hidden">
      {{ pageTitle }}
    </p>
    <div class="ml-auto">
      <UserMenu />
    </div>
  </header>

  <aside
    class="hidden h-screen w-64 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--card)] md:flex"
  >
    <button
      type="button"
      class="flex items-center gap-3 border-b border-[var(--border)] px-5 py-5 text-left transition hover:bg-[var(--accent)]"
      :class="chatActive ? 'bg-[var(--primary)]/8' : ''"
      @click="goChat"
    >
      <img
        :src="logoIconUrl"
        alt="Asclepios"
        class="h-10 w-10 rounded-xl object-cover shadow-sm ring-2"
        :class="chatActive ? 'ring-[var(--primary)]' : 'ring-transparent'"
      />
      <div class="min-w-0 flex-1">
        <p class="text-[15px] font-bold tracking-tight text-[var(--foreground)]">Asclepios</p>
        <p class="text-[11px] text-[var(--muted-foreground)]">Discuter avec l’IA</p>
      </div>
    </button>

    <nav class="flex flex-1 flex-col gap-1 overflow-y-auto p-3" aria-label="Navigation">
      <button
        v-for="item in primaryTabs"
        :key="item.name"
        type="button"
        :class="[
          'group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all',
          isTabActive(item)
            ? 'bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm'
            : 'text-[var(--foreground)] hover:bg-[var(--accent)] hover:text-[var(--accent-foreground)]',
        ]"
        @click="navigate(item)"
      >
        <component
          :is="item.icon"
          :size="17"
          :class="isTabActive(item) ? 'text-[var(--primary-foreground)]' : ''"
        />
        <span class="flex-1 text-left">{{ item.label }}</span>
      </button>
    </nav>

    <div class="border-t border-[var(--border)] px-5 py-4">
      <p class="text-[11px] text-[var(--muted-foreground)]">Asclepios v0.1.0</p>
    </div>
  </aside>

  <nav
    class="pointer-events-none fixed inset-x-0 bottom-0 z-40 flex items-end justify-center gap-2 px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] transition-transform duration-200 md:hidden"
    :class="keyboardOpen ? 'translate-y-[120%]' : 'translate-y-0'"
    aria-label="Navigation"
  >
    <div
      class="pointer-events-auto flex min-w-0 flex-1 items-stretch rounded-full border border-[var(--border)] bg-[var(--card)]/90 p-1.5 shadow-[0_8px_32px_rgba(15,40,30,0.16)] backdrop-blur-xl"
    >
      <button
        v-for="item in primaryTabs"
        :key="item.name"
        type="button"
        class="flex min-w-0 flex-1 flex-col items-center justify-center gap-0.5 rounded-full px-1 py-2 transition"
        :class="
          isTabActive(item)
            ? 'bg-[var(--primary)]/12 text-[var(--primary)]'
            : 'text-[var(--muted-foreground)]'
        "
        @click="navigate(item)"
      >
        <component :is="item.icon" :size="20" />
        <span class="max-w-full truncate text-[10px] font-semibold leading-tight">
          {{ item.label }}
        </span>
      </button>
    </div>

    <button
      type="button"
      class="pointer-events-auto relative shrink-0 rounded-full shadow-[0_8px_24px_rgba(15,40,30,0.2)] ring-2 ring-[var(--card)] transition active:scale-95"
      :class="chatActive ? 'ring-[var(--primary)]' : ''"
      aria-label="Discuter avec l’IA"
      @click="goChat"
    >
      <img :src="logoIconUrl" alt="" class="h-14 w-14 rounded-full object-cover" />
      <span
        v-if="chatActive"
        class="absolute right-0.5 top-0.5 h-2.5 w-2.5 rounded-full bg-[var(--primary)] ring-2 ring-[var(--card)]"
      />
    </button>
  </nav>
</template>
