<script setup lang="ts">
import AppSidebar from '@/components/AppSidebar.vue'
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-[var(--background)]">
    <AppSidebar />
    <main class="flex flex-1 flex-col overflow-hidden">
      <RouterView />
    </main>
  </div>
</template>
