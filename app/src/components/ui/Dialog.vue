<script setup lang="ts">
import {
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
  DialogTrigger,
} from 'reka-ui'
import { X } from '@lucide/vue'
import { cn } from '@/lib/utils'

interface Props {
  open?: boolean
  title?: string
  description?: string
  class?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:open': [value: boolean]
}>()
</script>

<template>
  <DialogRoot :open="props.open" @update:open="emit('update:open', $event)">
    <DialogTrigger as-child>
      <slot name="trigger" />
    </DialogTrigger>

    <DialogPortal>
      <DialogOverlay
        class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0"
      />
      <DialogContent
        :class="
          cn(
            'fixed z-50 flex w-full flex-col overflow-hidden border border-[var(--border)] bg-[var(--card)] shadow-2xl',
            'inset-x-0 bottom-0 max-h-[100dvh] rounded-t-2xl pb-[env(safe-area-inset-bottom)]',
            'sm:inset-auto sm:bottom-auto sm:left-1/2 sm:top-1/2 sm:max-h-[90vh] sm:max-w-2xl sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-2xl sm:pb-0',
            'data-[state=open]:animate-in data-[state=closed]:animate-out',
            'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
            'data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
            props.class,
          )
        "
      >
        <div class="flex shrink-0 items-start justify-between border-b border-[var(--border)] px-4 py-3 sm:px-6 sm:py-4">
          <div>
            <DialogTitle
              v-if="props.title"
              class="text-lg font-semibold text-[var(--foreground)]"
            >
              {{ props.title }}
            </DialogTitle>
            <DialogDescription
              v-if="props.description"
              class="mt-0.5 text-sm text-[var(--muted-foreground)]"
            >
              {{ props.description }}
            </DialogDescription>
            <slot name="header" />
          </div>
          <DialogClose
            class="ml-4 mt-0.5 rounded-lg p-1.5 text-[var(--muted-foreground)] transition hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
            aria-label="Fermer"
          >
            <X :size="18" />
          </DialogClose>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain">
          <slot />
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
