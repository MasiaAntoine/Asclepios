<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from '@/components/AppSidebar.vue'
import { useAuth } from '@/composables/useAuth'

const route = useRoute()
const { checked, authenticated } = useAuth()

const isLogin = computed(() => route.name === 'login')
const showLogin = computed(() => checked.value && isLogin.value)
const showApp = computed(() => checked.value && authenticated.value && !isLogin.value)
</script>

<template>
  <!-- Rien tant que la session n'est pas connue — évite le flash de l'app avant redirect login -->
  <div
    v-if="!checked || (!showLogin && !showApp)"
    class="min-h-dvh bg-[var(--background)]"
    aria-busy="true"
  />
  <div
    v-else-if="showLogin"
    class="min-h-dvh bg-[var(--background)]"
  >
    <RouterView />
  </div>
  <div
    v-else
    class="flex h-dvh overflow-hidden bg-[var(--background)]"
  >
    <AppSidebar />
    <main
      class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden pt-[calc(3.5rem+env(safe-area-inset-top))] md:pt-0"
    >
      <RouterView />
    </main>
  </div>
</template>
