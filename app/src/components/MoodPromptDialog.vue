<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Dialog from '@/components/ui/Dialog.vue'
import MoodScale from '@/components/MoodScale.vue'
import OwlEmotionIcon from '@/components/OwlEmotionIcon.vue'
import { useMood } from '@/composables/useMood'
import { usePushSubscription } from '@/composables/usePushSubscription'
import { formatMoodDateTime, moodOwl, todayIso } from '@/lib/mood'

const route = useRoute()
const { slotDue, currentSlot, currentSlotMeta, saveMood, loading } = useMood()
const { dialogOpen: pushDialogOpen } = usePushSubscription()

const open = ref(false)
const dismissedSlot = ref('')
const score = ref<number | null>(null)
const saving = ref(false)
const error = ref<string | null>(null)

const slotKey = computed(() => {
  const slot = currentSlot.value
  return slot ? `${todayIso()}|${slot}` : ''
})

const canAsk = computed(
  () =>
    !loading.value &&
    slotDue.value &&
    !pushDialogOpen.value &&
    route.path !== '/humeur' &&
    dismissedSlot.value !== slotKey.value &&
    Boolean(slotKey.value),
)

const title = computed(() => {
  const prompt = currentSlotMeta.value?.prompt ?? 'en ce moment'
  return `Comment tu te sens ${prompt} ?`
})

function maybeAsk() {
  if (canAsk.value) {
    score.value = null
    error.value = null
    open.value = true
  }
}

watch(canAsk, (value) => {
  if (value) maybeAsk()
  else if (!slotDue.value) open.value = false
})

onMounted(() => {
  window.setTimeout(() => maybeAsk(), 1400)
})

function later() {
  dismissedSlot.value = slotKey.value
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
    await saveMood(score.value)
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
    :title="title"
    description="Une note de 0 (au plus bas) à 10 (super bien), avec l’heure. Tu pourras la modifier plus tard."
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
        <div class="min-w-0">
          <p class="text-sm font-medium capitalize text-[var(--foreground)]">
            {{ formatMoodDateTime(new Date()) }}
          </p>
          <p v-if="currentSlotMeta" class="text-xs text-[var(--muted-foreground)]">
            Créneau {{ currentSlotMeta.label.toLowerCase() }}
          </p>
        </div>
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
