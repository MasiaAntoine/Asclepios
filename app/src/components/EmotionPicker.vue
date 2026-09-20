<script setup lang="ts">
import OwlEmotionIcon from '@/components/OwlEmotionIcon.vue'
import { EMOTIONS, type EmotionId } from '@/lib/emotions'

const selected = defineModel<EmotionId[]>('selected', { default: () => [] })

withDefaults(
  defineProps<{
    size?: number
  }>(),
  { size: 56 },
)

function isOn(id: EmotionId) {
  return selected.value.includes(id)
}

function toggle(id: EmotionId) {
  if (isOn(id)) {
    selected.value = selected.value.filter((x) => x !== id)
  } else {
    selected.value = [...selected.value, id]
  }
}
</script>

<template>
  <div class="grid grid-cols-4 gap-2 sm:gap-3">
    <button
      v-for="emotion in EMOTIONS"
      :key="emotion.id"
      type="button"
      class="flex cursor-pointer flex-col items-center gap-1.5 rounded-2xl px-1 py-2 outline-offset-2 transition duration-200"
      :class="isOn(emotion.id) ? 'bg-[var(--card)] shadow-sm' : 'hover:bg-[var(--muted)]/70'"
      :style="isOn(emotion.id) ? { outline: `2px solid ${emotion.color}` } : undefined"
      :aria-pressed="isOn(emotion.id)"
      @click="toggle(emotion.id)"
    >
      <span
        class="rounded-[22%] transition duration-200"
        :class="isOn(emotion.id) ? 'scale-105' : 'scale-100'"
        :style="
          isOn(emotion.id)
            ? { boxShadow: `0 0 0 3px ${emotion.color}33` }
            : undefined
        "
      >
        <OwlEmotionIcon :emotion="emotion.id" :active="isOn(emotion.id)" :size="size" />
      </span>
      <span
        class="text-[11px] font-medium leading-none"
        :style="{ color: isOn(emotion.id) ? emotion.color : 'var(--muted-foreground)' }"
      >
        {{ emotion.label }}
      </span>
    </button>
  </div>
</template>
