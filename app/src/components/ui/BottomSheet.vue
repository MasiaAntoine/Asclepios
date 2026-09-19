<script setup lang="ts">
import { onUnmounted, watch } from 'vue'
import { X } from '@lucide/vue'

const open = defineModel<boolean>('open', { default: false })

withDefaults(
  defineProps<{
    title?: string
  }>(),
  {
    title: '',
  },
)

watch(open, (value) => {
  document.body.style.overflow = value ? 'hidden' : ''
})

onUnmounted(() => {
  document.body.style.overflow = ''
})

function close() {
  open.value = false
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-opacity duration-300 ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition-opacity duration-300 ease-in"
      leave-to-class="opacity-0"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-50 bg-black/45 backdrop-blur-[2px]"
        @click="close"
      />
    </Transition>

    <Transition
      enter-active-class="transition-transform duration-300 ease-out"
      enter-from-class="translate-y-full"
      leave-active-class="transition-transform duration-300 ease-in"
      leave-to-class="translate-y-full"
    >
      <div
        v-if="open"
        class="fixed inset-x-0 bottom-0 z-50 flex max-h-[92dvh] flex-col rounded-t-3xl border border-[var(--border)] bg-[var(--card)] shadow-2xl"
        role="dialog"
        aria-modal="true"
      >
        <div class="flex shrink-0 flex-col items-center pt-2">
          <div class="h-1 w-10 rounded-full bg-[var(--muted-foreground)]/30" />
        </div>

        <header class="flex shrink-0 items-start justify-between gap-3 px-4 pb-3 pt-2">
          <div class="min-w-0 flex-1 pt-1">
            <slot name="header">
              <h2
                v-if="title"
                class="text-base font-semibold text-[var(--foreground)]"
              >
                {{ title }}
              </h2>
            </slot>
          </div>
          <button
            type="button"
            class="rounded-lg p-2 text-[var(--muted-foreground)] transition hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
            aria-label="Fermer"
            @click="close"
          >
            <X :size="18" />
          </button>
        </header>

        <div
          class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 pb-[max(1rem,env(safe-area-inset-bottom))]"
        >
          <slot />
        </div>

        <footer
          v-if="$slots.footer"
          class="shrink-0 border-t border-[var(--border)] px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]"
        >
          <slot name="footer" />
        </footer>
      </div>
    </Transition>
  </Teleport>
</template>
