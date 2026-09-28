<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'
import { LogOut, Settings, UserRound } from '@lucide/vue'
import { useAuth } from '@/composables/useAuth'
import { useProfile } from '@/composables/useProfile'

const router = useRouter()
const { logout } = useAuth()
const { profil, photoUrl } = useProfile()

const open = ref(false)
const root = ref<HTMLElement | null>(null)
const photoFailed = ref(false)

onClickOutside(root, () => {
  open.value = false
})

const initials = computed(() => {
  if (!profil.value) return ''
  return `${profil.value.prenom?.[0] ?? ''}${profil.value.nom?.[0] ?? ''}`.toUpperCase()
})

const label = computed(() => {
  if (!profil.value) return 'Compte'
  return `${profil.value.prenom} ${profil.value.nom}`.trim()
})

function toggle() {
  open.value = !open.value
}

function goSettings() {
  open.value = false
  void router.push({ name: 'settings' })
}

async function onLogout() {
  open.value = false
  await logout()
  await router.push({ name: 'login' })
}
</script>

<template>
  <div ref="root" class="relative shrink-0">
    <button
      type="button"
      class="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full ring-1 ring-[var(--border)] transition hover:ring-[var(--primary)]/50"
      :aria-expanded="open"
      aria-haspopup="menu"
      :aria-label="label"
      @click="toggle"
    >
      <img
        v-if="!photoFailed"
        :src="photoUrl"
        :alt="label"
        class="h-full w-full object-cover"
        @error="photoFailed = true"
      />
      <span
        v-else-if="initials"
        class="flex h-full w-full items-center justify-center bg-[var(--secondary)] text-xs font-semibold text-[var(--secondary-foreground)]"
      >
        {{ initials }}
      </span>
      <UserRound v-else :size="16" class="text-[var(--muted-foreground)]" />
    </button>

    <div
      v-if="open"
      class="absolute right-0 top-full z-50 mt-2 w-56 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--card)] py-1 shadow-lg"
      role="menu"
    >
      <p class="truncate px-3 py-2 text-xs font-medium text-[var(--muted-foreground)]">
        {{ label }}
      </p>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm text-[var(--foreground)] transition hover:bg-[var(--accent)]"
        role="menuitem"
        @click="goSettings"
      >
        <Settings :size="16" class="text-[var(--muted-foreground)]" />
        Réglages
      </button>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm text-[var(--foreground)] transition hover:bg-[var(--accent)]"
        role="menuitem"
        @click="onLogout"
      >
        <LogOut :size="16" class="text-[var(--muted-foreground)]" />
        Déconnexion
      </button>
    </div>
  </div>
</template>
