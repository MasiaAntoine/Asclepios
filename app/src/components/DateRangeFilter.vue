<script setup lang="ts">
import { DATE_RANGE_PRESETS, type DateRangePreset } from '@/composables/useDateRange'
import { CalendarRange } from '@lucide/vue'

defineProps<{
  preset: DateRangePreset
  customFrom: string
  customTo: string
}>()

const emit = defineEmits<{
  'update:preset': [value: DateRangePreset]
  'update:customFrom': [value: string]
  'update:customTo': [value: string]
  select: [value: DateRangePreset]
}>()

function onPreset(id: DateRangePreset) {
  emit('update:preset', id)
  emit('select', id)
}
</script>

<template>
  <div class="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
    <div class="flex items-center gap-2 text-xs font-medium text-[var(--muted-foreground)]">
      <CalendarRange :size="14" />
      Période
    </div>

    <div class="flex flex-wrap items-center gap-1.5">
      <button
        v-for="p in DATE_RANGE_PRESETS"
        :key="p.id"
        type="button"
        @click="onPreset(p.id)"
        :class="[
          'rounded-lg px-3 py-1.5 text-xs font-medium transition',
          preset === p.id
            ? 'bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm'
            : 'bg-[var(--muted)] text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--accent-foreground)]',
        ]"
      >
        {{ p.label }}
      </button>
    </div>

    <div
      v-if="preset === 'custom'"
      class="flex flex-wrap items-center gap-2 text-xs"
    >
      <label class="flex items-center gap-1.5 text-[var(--muted-foreground)]">
        Du
        <input
          type="date"
          :value="customFrom"
          @input="emit('update:customFrom', ($event.target as HTMLInputElement).value)"
          class="rounded-lg border border-[var(--border)] bg-[var(--background)] px-2 py-1.5 text-[var(--foreground)] focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
        />
      </label>
      <label class="flex items-center gap-1.5 text-[var(--muted-foreground)]">
        Au
        <input
          type="date"
          :value="customTo"
          @input="emit('update:customTo', ($event.target as HTMLInputElement).value)"
          class="rounded-lg border border-[var(--border)] bg-[var(--background)] px-2 py-1.5 text-[var(--foreground)] focus:border-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/20"
        />
      </label>
    </div>
  </div>
</template>
