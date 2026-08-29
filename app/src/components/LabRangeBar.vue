<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  value: number | null
  refLow: number | null
  refHigh: number | null
  outOfRange?: boolean
}>()

/** Position du curseur sur une échelle élargie autour de [low, high]. */
const markerPct = computed(() => {
  const v = props.value
  if (v == null) return null
  let low = props.refLow
  let high = props.refHigh
  if (low == null && high == null) return null
  if (low == null && high != null) {
    low = high * 0.2
  }
  if (high == null && low != null) {
    high = low * 1.8 || low + 1
  }
  if (low == null || high == null || high <= low) return 50

  const span = high - low
  const pad = span * 0.35
  const scaleMin = low - pad
  const scaleMax = high + pad
  const pct = ((v - scaleMin) / (scaleMax - scaleMin)) * 100
  return Math.min(98, Math.max(2, pct))
})

const greenStart = computed(() => {
  const low = props.refLow
  const high = props.refHigh
  if (low == null || high == null || high <= low) return 20
  const span = high - low
  const pad = span * 0.35
  const scaleMin = low - pad
  const scaleMax = high + pad
  return ((low - scaleMin) / (scaleMax - scaleMin)) * 100
})

const greenEnd = computed(() => {
  const low = props.refLow
  const high = props.refHigh
  if (low == null || high == null || high <= low) return 80
  const span = high - low
  const pad = span * 0.35
  const scaleMin = low - pad
  const scaleMax = high + pad
  return ((high - scaleMin) / (scaleMax - scaleMin)) * 100
})

function fmt(n: number | null): string {
  if (n == null) return ''
  return Number.isInteger(n) ? String(n) : String(n)
}
</script>

<template>
  <div v-if="markerPct != null" class="mt-2">
    <div class="relative mb-1 flex h-3.5 items-end text-[10px] text-[var(--muted-foreground)]">
      <span
        v-if="refLow != null"
        class="absolute -translate-x-1/2"
        :style="{ left: `${greenStart}%` }"
      >{{ fmt(refLow) }}</span>
      <span
        v-if="refHigh != null"
        class="absolute -translate-x-1/2"
        :style="{ left: `${greenEnd}%` }"
      >{{ fmt(refHigh) }}</span>
    </div>
    <div class="relative h-2 w-full overflow-visible rounded-full">
      <div
        class="absolute inset-0 rounded-full"
        :style="{
          background: `linear-gradient(90deg,
            #e07a5f 0%,
            #f2cc8f ${Math.max(0, greenStart - 8)}%,
            #81b29a ${greenStart}%,
            #81b29a ${greenEnd}%,
            #f2cc8f ${Math.min(100, greenEnd + 8)}%,
            #e07a5f 100%)`,
        }"
      />
      <div
        class="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 bg-white shadow-sm"
        :class="outOfRange ? 'border-[#e07a5f]' : 'border-[#81b29a]'"
        :style="{ left: `${markerPct}%` }"
      />
    </div>
  </div>
</template>
