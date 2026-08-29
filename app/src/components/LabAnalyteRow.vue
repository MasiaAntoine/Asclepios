<script setup lang="ts">
import type { LabAnalyte } from '@/composables/useLabPdfs'
import LabRangeBar from '@/components/LabRangeBar.vue'
import { ChevronRight } from '@lucide/vue'

defineProps<{
  item: LabAnalyte
}>()

function displayValue(item: LabAnalyte): string {
  if (item.value_display) return item.value_display.replace(',', '.')
  if (item.value != null) return String(item.value)
  return '—'
}
</script>

<template>
  <div class="border-b border-[var(--border)]/60 px-4 py-3 last:border-0">
    <div class="flex items-start justify-between gap-2">
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2">
          <span
            class="mt-0.5 h-2 w-2 shrink-0 rounded-full"
            :class="item.out_of_range ? 'bg-[#e07a5f]' : item.has_range ? 'bg-[#81b29a]' : 'bg-[var(--muted-foreground)]/40'"
          />
          <p class="truncate text-sm font-medium text-[var(--foreground)]">{{ item.name }}</p>
        </div>
        <div class="mt-1 pl-4">
          <p class="text-lg font-bold tracking-tight text-[var(--foreground)]">
            {{ displayValue(item) }}
            <span v-if="item.unit" class="ml-1 text-sm font-normal text-[var(--muted-foreground)]">{{ item.unit }}</span>
          </p>
          <p v-if="item.pct_display" class="text-xs text-[var(--muted-foreground)]">
            {{ item.pct_display }}
          </p>
          <LabRangeBar
            v-if="item.has_range && item.value != null"
            :value="item.value"
            :ref-low="item.ref_low"
            :ref-high="item.ref_high"
            :out-of-range="item.out_of_range"
          />
          <template v-if="item.alt && (item.alt.value != null || item.alt.value_display)">
            <p class="mt-2 text-[11px] text-[var(--muted-foreground)]">soit</p>
            <p class="text-base font-semibold text-[var(--foreground)]">
              {{ (item.alt.value_display || String(item.alt.value || '')).replace(',', '.') }}
              <span v-if="item.alt.unit" class="ml-1 text-sm font-normal text-[var(--muted-foreground)]">{{ item.alt.unit }}</span>
            </p>
            <LabRangeBar
              v-if="item.alt.value != null && (item.alt.ref_low != null || item.alt.ref_high != null)"
              :value="item.alt.value"
              :ref-low="item.alt.ref_low"
              :ref-high="item.alt.ref_high"
            />
          </template>
        </div>
      </div>
      <ChevronRight :size="16" class="mt-1 shrink-0 text-[var(--primary)]/50" />
    </div>
  </div>
</template>
