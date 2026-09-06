<script setup lang="ts">
import { computed, onUnmounted, watch } from 'vue'
import { ArrowLeft, ArrowRight, Check, X } from '@lucide/vue'

export interface StepperStep {
  id: string
  label: string
}

const open = defineModel<boolean>('open', { default: false })
const index = defineModel<number>('index', { default: 0 })

const props = withDefaults(
  defineProps<{
    title: string
    description?: string
    steps: StepperStep[]
    /** Largeur du panneau (défaut ~ 32rem). */
    wide?: boolean
    canNext?: boolean
    nextLabel?: string
    backLabel?: string
    submitLabel?: string
    submitting?: boolean
    hideFooter?: boolean
  }>(),
  {
    canNext: true,
    nextLabel: 'Continuer',
    backLabel: 'Retour',
    submitLabel: 'Valider',
    submitting: false,
    hideFooter: false,
    wide: false,
  },
)

const emit = defineEmits<{
  next: []
  back: []
  submit: []
  close: []
}>()

const isFirst = computed(() => index.value <= 0)
const isLast = computed(() => index.value >= props.steps.length - 1)
const current = computed(() => props.steps[index.value])

watch(open, (value) => {
  document.body.style.overflow = value ? 'hidden' : ''
  if (!value) emit('close')
})

onUnmounted(() => {
  document.body.style.overflow = ''
})

function close() {
  if (props.submitting) return
  open.value = false
}

function next() {
  if (!props.canNext || props.submitting) return
  if (isLast.value) {
    emit('submit')
    return
  }
  emit('next')
  index.value = Math.min(index.value + 1, props.steps.length - 1)
}

function back() {
  if (isFirst.value || props.submitting) return
  emit('back')
  index.value = Math.max(index.value - 1, 0)
}

function goTo(i: number) {
  if (props.submitting) return
  if (i < 0 || i > index.value) return
  index.value = i
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="duration-300 ease-out"
      leave-active-class="duration-200 ease-in"
    >
      <div v-if="open" class="fixed inset-0 z-50">
        <div
          class="absolute inset-0 bg-black/40 backdrop-blur-[2px] transition-opacity"
          @click="close"
        />

          <aside
            class="absolute inset-y-0 right-0 flex h-full w-full flex-col border-l border-[var(--border)] bg-[var(--card)] shadow-2xl animate-in slide-in-from-right duration-300"
            :class="wide ? 'max-w-xl' : 'max-w-lg'"
            role="dialog"
            aria-modal="true"
            :aria-labelledby="'stepper-title'"
            @click.stop
          >
            <header class="shrink-0 border-b border-[var(--border)] px-6 py-4">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <h2 id="stepper-title" class="text-lg font-semibold text-[var(--foreground)]">
                    {{ title }}
                  </h2>
                  <p
                    v-if="description"
                    class="mt-0.5 text-sm text-[var(--muted-foreground)]"
                  >
                    {{ description }}
                  </p>
                </div>
                <button
                  type="button"
                  class="rounded-lg p-1.5 text-[var(--muted-foreground)] transition hover:bg-[var(--muted)] hover:text-[var(--foreground)] disabled:opacity-40"
                  :disabled="submitting"
                  aria-label="Fermer"
                  @click="close"
                >
                  <X :size="18" />
                </button>
              </div>

              <ol class="mt-5 flex items-center gap-1">
                <li
                  v-for="(step, i) in steps"
                  :key="step.id"
                  class="flex min-w-0 flex-1 items-center gap-1"
                >
                  <button
                    type="button"
                    class="flex min-w-0 flex-1 flex-col items-center gap-1.5"
                    :disabled="submitting || i > index"
                    @click="goTo(i)"
                  >
                    <span
                      class="flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold transition"
                      :class="
                        i < index
                          ? 'bg-[var(--primary)] text-white'
                          : i === index
                            ? 'bg-[var(--primary)] text-white ring-4 ring-[var(--primary)]/20'
                            : 'bg-[var(--muted)] text-[var(--muted-foreground)]'
                      "
                    >
                      <Check v-if="i < index" :size="13" />
                      <span v-else>{{ i + 1 }}</span>
                    </span>
                    <span
                      class="w-full truncate text-center text-[10px] font-medium uppercase tracking-wide"
                      :class="
                        i === index
                          ? 'text-[var(--primary)]'
                          : 'text-[var(--muted-foreground)]'
                      "
                    >
                      {{ step.label }}
                    </span>
                  </button>
                  <span
                    v-if="i < steps.length - 1"
                    class="mb-4 h-px flex-1 bg-[var(--border)]"
                    aria-hidden="true"
                  />
                </li>
              </ol>
            </header>

            <div class="min-h-0 flex-1 overflow-y-auto px-6 py-5">
              <slot :step="current" :index="index" />
            </div>

            <footer
              v-if="!hideFooter"
              class="shrink-0 flex items-center justify-between gap-3 border-t border-[var(--border)] bg-[var(--card)] px-6 py-4"
            >
              <button
                type="button"
                class="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-[var(--muted-foreground)] transition hover:bg-[var(--muted)] disabled:invisible"
                :disabled="isFirst || submitting"
                @click="back"
              >
                <ArrowLeft :size="15" />
                {{ backLabel }}
              </button>
              <button
                type="button"
                class="inline-flex items-center gap-2 rounded-lg bg-[var(--primary)] px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-[var(--primary)]/90 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="!canNext || submitting"
                @click="next"
              >
                {{ isLast ? submitLabel : nextLabel }}
                <ArrowRight v-if="!isLast" :size="15" />
              </button>
            </footer>
          </aside>
      </div>
    </Transition>
  </Teleport>
</template>
