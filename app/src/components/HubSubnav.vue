<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { HUB_TABS, type HubId } from '@/lib/hubs'

const props = defineProps<{
  hub: HubId
}>()

const route = useRoute()
const router = useRouter()

const tabs = computed(() => HUB_TABS[props.hub])
const queryTab = computed(() =>
  typeof route.query.tab === 'string' ? route.query.tab : undefined,
)

function isActive(match: (path: string, tab?: string) => boolean) {
  return match(route.path, queryTab.value)
}

function go(to: string) {
  void router.push(to)
}
</script>

<template>
  <div class="flex gap-1 overflow-x-auto rounded-xl bg-[var(--muted)] p-1">
    <button
      v-for="tab in tabs"
      :key="tab.to"
      type="button"
      class="shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition sm:px-4 sm:text-sm"
      :class="
        isActive(tab.match)
          ? 'bg-[var(--card)] text-[var(--foreground)] shadow-sm'
          : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'
      "
      @click="go(tab.to)"
    >
      {{ tab.label }}
    </button>
  </div>
</template>
