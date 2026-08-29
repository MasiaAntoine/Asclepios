<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import logoIconUrl from '@/assets/logo-icon.png'
import { Activity, BookOpen, FileText, LayoutDashboard, Scale, Settings, Stethoscope, UserRound } from '@lucide/vue'

const route = useRoute()
const router = useRouter()

const navItems = [
  {
    label: 'Tableau de bord',
    icon: LayoutDashboard,
    to: '/',
    name: 'dashboard',
  },
  {
    label: 'Profil',
    icon: UserRound,
    to: '/profil',
    name: 'profile',
  },
  {
    label: 'Rapports',
    icon: FileText,
    to: '/rapports',
    name: 'reports',
  },
  {
    label: 'Poids',
    icon: Scale,
    to: '/poids',
    name: 'weight',
  },
  {
    label: 'Suivi',
    icon: Activity,
    to: '/suivi',
    name: 'suivi',
  },
  {
    label: 'Médicaments',
    icon: BookOpen,
    to: '/meds',
    name: 'meds',
  },
  {
    label: 'Médecins',
    icon: Stethoscope,
    to: '/medecins',
    name: 'doctors',
  },
  {
    label: 'Paramètres',
    icon: Settings,
    to: '/settings',
    name: 'settings',
    disabled: true,
  },
]

const isActive = (to: string) =>
  to === '/' ? route.path === '/' : route.path.startsWith(to)

function navigate(item: typeof navItems[0]) {
  if (!item.disabled) router.push(item.to)
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
    <nav class="flex flex-1 flex-col gap-1 p-3 overflow-y-auto">
      <button
        v-for="item in navItems"
        :key="item.name"
        @click="navigate(item)"
        :class="[
          'group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all',
          isActive(item.to) && !item.disabled
            ? 'bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm'
            : item.disabled
              ? 'cursor-not-allowed opacity-40 text-[var(--muted-foreground)]'
              : 'text-[var(--foreground)] hover:bg-[var(--accent)] hover:text-[var(--accent-foreground)]',
        ]"
      >
        <component
          :is="item.icon"
          :size="18"
          :class="[
            'shrink-0 transition-transform group-hover:scale-105',
            isActive(item.to) && !item.disabled ? 'text-[var(--primary-foreground)]' : '',
          ]"
        />
        <span>{{ item.label }}</span>
        <span
          v-if="item.disabled"
          class="ml-auto rounded-full bg-[var(--muted)] px-1.5 py-0.5 text-[10px] text-[var(--muted-foreground)]"
        >
          Bientôt
        </span>
      </button>
    </nav>

    <!-- Footer -->
    <div class="border-t border-[var(--border)] px-5 py-4">
      <p class="text-[11px] text-[var(--muted-foreground)]">Asclepios v0.1.0</p>
    </div>
  </aside>
</template>
