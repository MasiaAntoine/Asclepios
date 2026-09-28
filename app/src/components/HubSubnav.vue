<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { HUB_TABS, type HubId } from '@/lib/hubs'

const props = defineProps<{
  hub: HubId
}>()

const route = useRoute()
const router = useRouter()
const scroller = ref<HTMLElement | null>(null)

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

function scrollActiveIntoView() {
  const parent = scroller.value
  const el = parent?.querySelector<HTMLElement>('[data-active="true"]')
  if (!parent || !el) return
  const parentRect = parent.getBoundingClientRect()
  const elRect = el.getBoundingClientRect()
  const delta = elRect.left - parentRect.left - (parent.clientWidth - el.offsetWidth) / 2
  const next = Math.max(0, parent.scrollLeft + delta)
  parent.scrollTo({ left: next, behavior: 'auto' })
}

async function revealActive() {
  await nextTick()
  requestAnimationFrame(scrollActiveIntoView)
}

watch(
  () => [props.hub, route.fullPath] as const,
  () => {
    void revealActive()
  },
  { immediate: true },
)

onMounted(() => {
  window.addEventListener('resize', scrollActiveIntoView)
})

onUnmounted(() => {
  window.removeEventListener('resize', scrollActiveIntoView)
})
</script>

<template>
  <div
    ref="scroller"
    class="flex min-w-0 gap-1 overflow-x-auto rounded-xl bg-[var(--muted)] p-1 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden"
    role="navigation"
    aria-label="Sous-menu"
  >
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
      :data-active="isActive(tab.match) ? 'true' : undefined"
      :aria-current="isActive(tab.match) ? 'page' : undefined"
      @click="go(tab.to)"
    >
      {{ tab.label }}
    </button>
  </div>
</template>
