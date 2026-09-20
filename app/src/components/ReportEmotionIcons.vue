<script setup lang="ts">
import OwlEmotionIcon from '@/components/OwlEmotionIcon.vue'
import { promptReportEmotions } from '@/composables/useEmotionPrompt'
import { useReportEmotions } from '@/composables/useReportEmotions'
import { EMOTIONS, type EmotionId } from '@/lib/emotions'

const props = withDefaults(
  defineProps<{
    reportId: string
    size?: number
  }>(),
  {
    size: 28,
  },
)

const { emotionsOf } = useReportEmotions()

function isOn(id: EmotionId) {
  return emotionsOf(props.reportId).includes(id)
}

function openPicker(event?: Event) {
  event?.stopPropagation()
  event?.preventDefault()
  promptReportEmotions(props.reportId)
}
</script>

<template>
  <button
    type="button"
    class="flex cursor-pointer flex-wrap items-center gap-1 text-left"
    :aria-label="'Émotions du rapport'"
    @click="openPicker"
  >
    <OwlEmotionIcon
      v-for="emotion in EMOTIONS"
      :key="emotion.id"
      :emotion="emotion.id"
      :active="isOn(emotion.id)"
      :size="size"
      :title="emotion.label"
    />
  </button>
</template>
