<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import logoIconUrl from '@/assets/logo-icon.png'
import {
  Activity,
  BookOpen,
  Droplets,
  FileText,
  LayoutDashboard,
  MessageSquare,
  Scale,
  ScrollText,
  Settings,
  Stethoscope,
  UserRound,
  type LucideIcon,
} from '@lucide/vue'

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

const isActive = (to: string) =>
  to === '/' ? route.path === '/' : route.path.startsWith(to)

function navigate(item: NavItem) {
  void router.push(item.to)
}
</script>

<template>
  <aside class="flex h-screen w-64 flex-col border-r border-[var(--border)] bg-[var(--card)]">
    <!-- Logo / Brand -->
    <div class="flex items-center gap-3 border-b border-[var(--border)] px-5 py-5">
      <img
        :src="logoIconUrl"
        alt="Asclepios"
        class="h-10 w-10 rounded-xl object-cover shadow-sm"
      />
      <div>
        <p class="text-[15px] font-bold tracking-tight text-[var(--foreground)]">Asclepios</p>
        <p class="text-[11px] text-[var(--muted-foreground)]">Suivi médical</p>
      </div>
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
            'group flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all',
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
    <div class="border-t border-[var(--border)] px-5 py-4">
      <p class="text-[11px] text-[var(--muted-foreground)]">Asclepios v0.1.0</p>
    </div>
  </aside>
</template>
