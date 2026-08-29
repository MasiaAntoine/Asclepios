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
            'fixed left-1/2 top-1/2 z-50 w-full max-w-2xl -translate-x-1/2 -translate-y-1/2',
            'rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-2xl',
            'data-[state=open]:animate-in data-[state=closed]:animate-out',
            'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
            'data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
            'data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%]',
            'data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]',
            props.class,
          )
        "
      >
        <!-- Header -->
        <div class="flex items-start justify-between border-b border-[var(--border)] px-6 py-4">
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

        <!-- Body -->
        <slot />
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
