<script setup lang="ts">
import OwlEmotionIcon from '@/components/OwlEmotionIcon.vue'
import { moodColor, moodLabel, moodOwl } from '@/lib/mood'

const score = defineModel<number | null>('score', { default: null })

withDefaults(
  defineProps<{
    disabled?: boolean
  }>(),
  { disabled: false },
)

const ticks = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
</script>

<template>
  <div>
    <div class="-mx-1 overflow-x-auto px-1">
      <div class="flex min-w-[300px] items-end justify-between gap-1">
        <button
        v-for="n in ticks"
        :key="n"
        type="button"
        class="flex min-w-0 flex-1 flex-col items-center gap-1 rounded-xl py-1.5 transition duration-200 disabled:opacity-50"
        :class="score === n ? 'bg-[var(--card)] shadow-sm' : 'hover:bg-[var(--muted)]/70'"
        :style="score === n ? { outline: `2px solid ${moodColor(n)}` } : undefined"
        :disabled="disabled"
        :aria-pressed="score === n"
        :aria-label="`${n} — ${moodLabel(n)}`"
        @click="score = n"
      >
        <OwlEmotionIcon
          :emotion="moodOwl(n)"
          :active="score === n"
          :size="score === n ? 36 : 28"
        />
        <span
          class="text-[11px] font-semibold tabular-nums"
          :style="{ color: score === n ? moodColor(n) : 'var(--muted-foreground)' }"
        >
          {{ n }}
        </span>
        </button>
      </div>
    </div>
    <div class="mt-2 flex items-center justify-between text-[11px] text-[var(--muted-foreground)]">
      <span>0 · au plus bas</span>
      <span
        v-if="score != null"
        class="font-medium"
        :style="{ color: moodColor(score) }"
      >
        {{ score }} · {{ moodLabel(score) }}
      </span>
      <span>10 · super bien</span>
    </div>
  </div>
</template>
