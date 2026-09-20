<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Dialog from '@/components/ui/Dialog.vue'
import MoodScale from '@/components/MoodScale.vue'
import OwlEmotionIcon from '@/components/OwlEmotionIcon.vue'
import { useMood } from '@/composables/useMood'
import { usePushSubscription } from '@/composables/usePushSubscription'
import { formatMoodDate, moodOwl, todayIso } from '@/lib/mood'

const route = useRoute()
const { today, saveMood } = useMood()
const { dialogOpen: pushDialogOpen } = usePushSubscription()

const open = ref(false)
const dismissedToday = ref('')
const score = ref<number | null>(null)
const saving = ref(false)
const error = ref<string | null>(null)

const day = computed(() => todayIso())
const canAsk = computed(
  () =>
    !today.value &&
    !pushDialogOpen.value &&
    route.path !== '/humeur' &&
    dismissedToday.value !== day.value,
)

function maybeAsk() {
  if (canAsk.value) {
    score.value = null
    error.value = null
    open.value = true
  }
}

watch(canAsk, (value) => {
  if (value) maybeAsk()
  else if (today.value) open.value = false
})

onMounted(() => {
  window.setTimeout(() => maybeAsk(), 1400)
})

function later() {
  dismissedToday.value = day.value
  open.value = false
}

function onOpenChange(next: boolean) {
  if (next) open.value = true
  else later()
}

async function save() {
  if (score.value == null || saving.value) return
  saving.value = true
  error.value = null
  try {
    await saveMood(day.value, score.value)
    open.value = false
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Enregistrement impossible'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    :open="open"
    title="Comment tu te sens aujourd’hui ?"
    description="Une note de 0 (au plus bas) à 10 (super bien). Tu pourras la modifier plus tard."
    class="sm:max-w-lg"
    @update:open="onOpenChange"
  >
    <div class="space-y-4 px-4 py-5 sm:px-6">
      <div class="flex items-center gap-3 rounded-xl bg-[var(--accent)]/40 px-3 py-2.5">
        <OwlEmotionIcon
          :emotion="moodOwl(score ?? 5)"
          :active="score != null"
          :size="40"
        />
        <p class="text-sm font-medium capitalize text-[var(--foreground)]">
          {{ formatMoodDate(day) }}
        </p>
      </div>
      <MoodScale v-model:score="score" :disabled="saving" />
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
        :disabled="score == null || saving"
        @click="save"
      >
        {{ saving ? 'Enregistrement…' : 'Enregistrer' }}
      </button>
    </div>
  </Dialog>
</template>
