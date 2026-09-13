<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import logoIconUrl from '@/assets/logo-icon.png'
import { useAuth } from '@/composables/useAuth'
import {
  Activity,
  BookOpen,
  CalendarDays,
  Droplets,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  Scale,
  ScrollText,
  Settings,
  Stethoscope,
  UserRound,
  X,
  type LucideIcon,
} from '@lucide/vue'

const { logout } = useAuth()

interface NavItem {
  label: string
  icon: LucideIcon
  to: string
  name: string
  badge?: string
}

interface NavSection {
  label: string | null
  items: NavItem[]
}

const route = useRoute()
const router = useRouter()
const mobileOpen = ref(false)

const navSections: NavSection[] = [
  {
    label: null,
    items: [
      { label: 'Tableau de bord', icon: LayoutDashboard, to: '/', name: 'dashboard' },
    ],
  },
  {
    label: 'Asclepios',
    items: [
      {
        label: 'Discuter',
        icon: MessageSquare,
        to: '/assistant',
        name: 'chat',
        badge: 'IA',
      },
    ],
  },
  {
    label: 'Dossier',
    items: [
      { label: 'Profil', icon: UserRound, to: '/profil', name: 'profile' },
      { label: 'Médecins', icon: Stethoscope, to: '/medecins', name: 'doctors' },
      { label: 'Médicaments', icon: BookOpen, to: '/meds', name: 'meds' },
    ],
  },
  {
    label: 'Documents',
    items: [
      { label: 'Rapports', icon: FileText, to: '/rapports', name: 'reports' },
      { label: 'Ordonnances', icon: ScrollText, to: '/ordonnances', name: 'ordonnances' },
      { label: 'Prise de sang', icon: Droplets, to: '/prise-de-sang', name: 'prise-de-sang' },
    ],
  },
  {
    label: 'Suivi',
    items: [
      { label: 'Agenda', icon: CalendarDays, to: '/agenda', name: 'agenda' },
      { label: 'Poids', icon: Scale, to: '/poids', name: 'weight' },
      { label: 'Suivi', icon: Activity, to: '/suivi', name: 'suivi' },
    ],
  },
  {
    label: 'Système',
    items: [
      { label: 'Paramètres', icon: Settings, to: '/settings', name: 'settings' },
    ],
  },
]

watch(
  () => route.fullPath,
  () => {
    mobileOpen.value = false
  },
)

const isActive = (to: string) =>
  to === '/' ? route.path === '/' : route.path.startsWith(to)

function navigate(item: NavItem) {
  mobileOpen.value = false
  void router.push(item.to)
}

async function onLogout() {
  mobileOpen.value = false
  await logout()
  await router.push({ name: 'login' })
}
</script>

<template>
  <!-- Barre mobile (PWA / téléphone) -->
  <header
    class="fixed inset-x-0 top-0 z-40 flex h-14 items-center gap-3 border-b border-[var(--border)] bg-[var(--card)] px-3 pt-[env(safe-area-inset-top)] md:hidden"
  >
    <button
      type="button"
      class="rounded-lg p-2 text-[var(--foreground)] transition hover:bg-[var(--accent)]"
      :aria-expanded="mobileOpen"
      aria-controls="app-sidebar"
      aria-label="Ouvrir le menu"
      @click="mobileOpen = true"
    >
      <Menu :size="20" />
    </button>
    <img :src="logoIconUrl" alt="" class="h-8 w-8 rounded-lg object-cover" />
    <div class="min-w-0">
      <p class="truncate text-sm font-bold text-[var(--foreground)]">Asclepios</p>
    </div>
  </header>

  <!-- Overlay mobile -->
  <Transition
    enter-active-class="transition-opacity duration-200"
    leave-active-class="transition-opacity duration-150"
    enter-from-class="opacity-0"
    leave-to-class="opacity-0"
  >
    <div
      v-if="mobileOpen"
      class="fixed inset-0 z-40 bg-black/40 backdrop-blur-[1px] md:hidden"
      @click="mobileOpen = false"
    />
  </Transition>

  <aside
    id="app-sidebar"
    class="fixed inset-y-0 left-0 z-50 flex h-dvh w-72 max-w-[85vw] flex-col border-r border-[var(--border)] bg-[var(--card)] pt-[env(safe-area-inset-top)] transition-transform duration-200 md:static md:z-auto md:h-screen md:w-64 md:max-w-none md:translate-x-0 md:pt-0"
    :class="mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'"
  >
    <!-- Logo / Brand -->
    <div class="flex items-center gap-3 border-b border-[var(--border)] px-5 py-5">
      <img
        :src="logoIconUrl"
        alt="Asclepios"
        class="h-10 w-10 rounded-xl object-cover shadow-sm"
      />
      <div class="min-w-0 flex-1">
        <p class="text-[15px] font-bold tracking-tight text-[var(--foreground)]">Asclepios</p>
        <p class="text-[11px] text-[var(--muted-foreground)]">Suivi médical</p>
      </div>
      <button
        type="button"
        class="rounded-lg p-2 text-[var(--muted-foreground)] transition hover:bg-[var(--muted)] md:hidden"
        aria-label="Fermer le menu"
        @click="mobileOpen = false"
      >
        <X :size="18" />
      </button>
    </div>

    <!-- Navigation -->
    <nav class="flex flex-1 flex-col gap-5 overflow-y-auto p-3">
      <div
        v-for="(section, sIdx) in navSections"
        :key="section.label ?? `section-${sIdx}`"
        class="flex flex-col gap-1"
      >
        <p
          v-if="section.label"
          class="px-3 pb-1 pt-0.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)]"
        >
          {{ section.label }}
        </p>
        <button
          v-for="item in section.items"
          :key="item.name"
          type="button"
          :class="[
            'group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all',
            isActive(item.to)
              ? 'bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm'
              : 'text-[var(--foreground)] hover:bg-[var(--accent)] hover:text-[var(--accent-foreground)]',
          ]"
          @click="navigate(item)"
        >
          <component
            :is="item.icon"
            :size="17"
            :class="[
              'shrink-0 transition-transform group-hover:scale-105',
              isActive(item.to) ? 'text-[var(--primary-foreground)]' : '',
            ]"
          />
          <span class="flex-1 text-left">{{ item.label }}</span>
          <span
            v-if="item.badge"
            :class="[
              'rounded-md px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide',
              isActive(item.to)
                ? 'bg-white/20 text-[var(--primary-foreground)]'
                : 'bg-[var(--primary)]/12 text-[var(--primary)]',
            ]"
          >
            {{ item.badge }}
          </span>
        </button>
      </div>
    </nav>

    <!-- Footer -->
    <div class="space-y-3 border-t border-[var(--border)] px-5 py-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
      <button
        type="button"
        class="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm font-medium text-[var(--muted-foreground)] transition hover:bg-[var(--accent)] hover:text-[var(--foreground)]"
        @click="onLogout"
      >
        <LogOut :size="16" />
        Déconnexion
      </button>
      <p class="text-[11px] text-[var(--muted-foreground)]">Asclepios v0.1.0</p>
    </div>
  </aside>
</template>
