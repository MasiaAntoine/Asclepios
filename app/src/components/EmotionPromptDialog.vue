<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Dialog from '@/components/ui/Dialog.vue'
import EmotionPicker from '@/components/EmotionPicker.vue'
import OwlEmotionIcon from '@/components/OwlEmotionIcon.vue'
import { useEmotionPrompt } from '@/composables/useEmotionPrompt'
import { useReportEmotions } from '@/composables/useReportEmotions'
import { useReports } from '@/composables/useReports'
import type { EmotionId } from '@/lib/emotions'

const { promptOpen, promptReportId } = useEmotionPrompt()
const { emotionsOf, saveEmotions, isEvaluated } = useReportEmotions()
const { getReportSync, reports } = useReports()

const selected = ref<EmotionId[]>([])
const saving = ref(false)
const error = ref<string | null>(null)

const reportTitle = computed(() => {
  const id = promptReportId.value
  if (!id) return ''
  return getReportSync(id)?.title || reports.value.find((r) => r.id === id)?.title || id
})

watch(
  [promptOpen, promptReportId],
  ([open, id]) => {
    error.value = null
    if (open && id) selected.value = [...emotionsOf(id)]
  },
)

async function save() {
  if (!promptReportId.value || selected.value.length === 0 || saving.value) return
  saving.value = true
  error.value = null
  try {
    await saveEmotions(promptReportId.value, selected.value)
    promptOpen.value = false
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Enregistrement impossible'
  } finally {
    saving.value = false
  }
}

function later() {
  promptOpen.value = false
}
</script>

<template>
  <Dialog
    :open="promptOpen"
    title="Comment te sentais-tu ?"
    description="Associe une ou plusieurs émotions au moment de ce rapport. Tu pourras les modifier plus tard."
    class="sm:max-w-lg"
    @update:open="promptOpen = $event"
  >
    <div class="space-y-5 px-4 py-5 sm:px-6">
      <div class="flex items-center gap-3 rounded-xl bg-[var(--accent)]/40 px-3 py-2.5">
        <OwlEmotionIcon
          emotion="calme"
          :active="isEvaluated(promptReportId ?? '')"
          :size="40"
        />
        <p class="min-w-0 truncate text-sm font-medium text-[var(--foreground)]">
          {{ reportTitle }}
        </p>
      </div>

      <EmotionPicker v-model:selected="selected" :size="52" />

      <p v-if="error" class="text-xs text-red-600">{{ error }}</p>
    </div>

    <div class="flex items-center justify-between gap-3 border-t border-[var(--border)] px-4 py-4 sm:px-6">
      <button
        type="button"
        class="rounded-lg px-3 py-2 text-sm text-[var(--muted-foreground)] transition hover:text-[var(--foreground)]"
        @click="later"
      >
        Plus tard
      </button>
      <button
        type="button"
        class="rounded-lg bg-[var(--primary)] px-5 py-2.5 text-sm font-medium text-[var(--primary-foreground)] shadow-sm transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        :disabled="selected.length === 0 || saving"
        @click="save"
      >
        {{ saving ? 'Enregistrement…' : 'Enregistrer' }}
      </button>
    </div>
  </Dialog>
</template>
