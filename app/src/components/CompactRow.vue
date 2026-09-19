<script setup lang="ts">
import { ChevronRight } from '@lucide/vue'

withDefaults(
  defineProps<{
    title: string
    /** Affiché à côté du titre, ex. « 24 oct. » */
    meta?: string
    subtitle?: string
    /** flush = liste dense groupée ; card = pastille arrondie */
    variant?: 'flush' | 'card'
  }>(),
  {
    meta: '',
    subtitle: '',
    variant: 'flush',
  },
)
</script>

<template>
  <button
    type="button"
    :class="[
      'flex w-full min-h-11 items-center gap-3 text-left',
      variant === 'card'
        ? 'rounded-2xl border border-[var(--border)] bg-[var(--card)] px-3 py-2.5'
        : 'py-2.5',
    ]"
  >
    <div
      :class="[
        'flex shrink-0 items-center justify-center text-[var(--muted-foreground)]',
        variant === 'card' ? 'h-9 w-9' : 'h-8 w-8',
      ]"
    >
      <slot name="icon" />
    </div>
    <div class="min-w-0 flex-1">
      <p class="truncate text-[15px] font-medium leading-snug text-[var(--foreground)]">
        {{ title }}
        <span v-if="meta" class="font-medium"> · {{ meta }}</span>
      </p>
      <p
        v-if="subtitle"
        class="mt-0.5 truncate text-[13px] leading-snug text-[var(--muted-foreground)]"
      >
        {{ subtitle }}
      </p>
    </div>
    <div v-if="$slots.trailing" class="shrink-0">
      <slot name="trailing" />
    </div>
    <ChevronRight
      :size="16"
      class="shrink-0 text-[var(--muted-foreground)]/45"
    />
  </button>
</template>
